"""Candado de acceso para cuando K-Secure está publicado en internet.

Si existe la variable KSECURE_ACCESO="usuario:contraseña", toda la web pide ese
usuario y contraseña (el navegador muestra su ventana de inicio de sesión).
Sin la variable (en el PC de desarrollo) no pide nada.

shortcut: un solo usuario compartido; se reemplaza por el login con roles (Admin, Auditor, Visor).
"""

import base64
import os
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import Response

LIBRES = {"/api/health"}  # Render revisa esta ruta para saber si la app está viva


def _credenciales_validas(cabecera: str, esperado: str) -> bool:
    if not cabecera.startswith("Basic "):
        return False
    try:
        recibido = base64.b64decode(cabecera[6:]).decode()
    except (ValueError, UnicodeDecodeError):
        return False
    return secrets.compare_digest(recibido.encode(), esperado.encode())  # sin filtrar por tiempos


def proteger(app: FastAPI, acceso: str | None = None):
    acceso = acceso if acceso is not None else os.environ.get("KSECURE_ACCESO", "")
    if not acceso:
        return
    if ":" not in acceso:
        raise ValueError('KSECURE_ACCESO debe tener la forma "usuario:contraseña"')

    @app.middleware("http")
    async def pedir_credenciales(request: Request, siguiente):
        if request.url.path in LIBRES or _credenciales_validas(request.headers.get("authorization", ""), acceso):
            return await siguiente(request)
        return Response("Acceso restringido", status_code=401, headers={"WWW-Authenticate": 'Basic realm="K-Secure"'})
