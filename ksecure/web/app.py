"""Aplicación web de K-Secure.

Ejecutar:  uvicorn ksecure.web.app:app --reload
Páginas en http://localhost:8000 y documentación de la API en /docs.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ksecure.almacenamiento.db import crear_sesiones
from ksecure.web.api import auditor, escanear, reglas, resultados

STATIC = Path(__file__).parent / "static"


def create_app(db_url: str | None = None) -> FastAPI:
    app = FastAPI(title="K-Secure", description="Detección de datos sensibles chilenos en archivos y bases de datos")
    app.state.sesiones = crear_sesiones(db_url)

    @app.get("/api/health", tags=["sistema"])
    def health():
        return {"status": "ok"}

    app.include_router(escanear.router)
    app.include_router(resultados.router)
    app.include_router(auditor.router)
    app.include_router(reglas.router)
    # Va al final: todo lo que no sea /api/... son las páginas (index.html, archivos.html, ...).
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="paginas")
    return app


app = create_app()
