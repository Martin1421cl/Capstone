"""Aplicación web de K-Secure.

Ejecutar:  uvicorn ksecure.web.app:app --reload
Páginas en http://localhost:8000 y documentación de la API en /docs (con sesión iniciada).

Primer administrador:
- En la nube, KSECURE_ACCESO="usuario:contraseña" lo crea al arrancar (si la base no tiene cuentas).
- En un PC sin esa variable, la primera visita muestra la pantalla para crearlo.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ksecure.almacenamiento import usuarios
from ksecure.almacenamiento.db import crear_sesiones
from ksecure.web.api import auditor, escanear, reglas, resultados
from ksecure.web.api import sesion as api_sesion
from ksecure.web.api import usuarios as api_usuarios
from ksecure.web.sesion import proteger

STATIC = Path(__file__).parent / "static"


def create_app(db_url: str | None = None, acceso: str | None = None) -> FastAPI:
    app = FastAPI(title="K-Secure", description="Detección de datos sensibles chilenos en archivos y bases de datos")
    app.state.sesiones = crear_sesiones(db_url)
    acceso = acceso if acceso is not None else os.environ.get("KSECURE_ACCESO", "")
    if acceso:
        with app.state.sesiones() as db:
            usuarios.crear_admin_inicial(db, acceso)
    proteger(app)

    @app.get("/api/health", tags=["sistema"])
    def health():
        return {"status": "ok"}

    app.include_router(api_sesion.router)
    app.include_router(api_usuarios.router)
    app.include_router(escanear.router)
    app.include_router(resultados.router)
    app.include_router(auditor.router)
    app.include_router(reglas.router)
    # Va al final: todo lo que no sea /api/... son las páginas (index.html, archivos.html, ...).
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="paginas")
    return app


app = create_app()
