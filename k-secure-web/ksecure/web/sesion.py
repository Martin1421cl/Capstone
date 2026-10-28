"""Inicio de sesión para toda la web (reemplaza al candado de usuario compartido).

Un middleware revisa la cookie en cada petición:
- Sin sesión, las páginas llevan a /login.html y la API responde 401.
- Con una contraseña temporal, solo se puede cambiar la contraseña (la API responde 428).
- Las páginas de escanear piden rol Auditor y la de usuarios rol Admin.
Los permisos de cada endpoint se piden con requiere(...) (ver api/*.py).
"""

from urllib.parse import quote, urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool

from ksecure.almacenamiento import usuarios
from ksecure.almacenamiento.modelos import Usuario
from ksecure.almacenamiento.usuarios import ADMIN, AUDITOR, NIVEL

COOKIE = "ksecure_sesion"
LOGIN = "/login.html"
RECURSOS = ("/css/", "/js/", "/img/")  # estilos, scripts e imágenes: no tienen datos
API_PUBLICA = {"/api/health", "/api/sesion", "/api/sesion/ingresar", "/api/sesion/configurar"}
API_CON_CLAVE_TEMPORAL = {"/api/sesion", "/api/sesion/salir", "/api/sesion/cambiar-clave"}
PAGINAS_POR_ROL = {"/archivos.html": AUDITOR, "/base-datos.html": AUDITOR, "/usuarios.html": ADMIN}
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}


def es_https(request: Request) -> bool:
    # Render atiende el HTTPS y le pasa la petición a la app por HTTP, avisando en este encabezado.
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def poner_cookie(respuesta, request: Request, token: str):
    respuesta.set_cookie(COOKIE, token, max_age=int(usuarios.DURACION_MAXIMA.total_seconds()), path="/",
                         httponly=True, samesite="lax", secure=es_https(request))


def borrar_cookie(respuesta):
    respuesta.delete_cookie(COOKIE, path="/")


def _cargar_usuario(request: Request) -> Usuario | None:
    with request.app.state.sesiones() as db:
        return usuarios.usuario_de_sesion(db, request.cookies.get(COOKIE))


def proteger(app: FastAPI):
    @app.middleware("http")
    async def exigir_sesion(request: Request, siguiente):
        ruta = request.url.path

        # Otra página no puede mandar formularios o peticiones a K-Secure con la cookie del usuario.
        origen = request.headers.get("origin")
        if request.method not in METODOS_SEGUROS and origen and urlsplit(origen).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Origen no permitido"}, status_code=403)

        if ruta.startswith(RECURSOS) or ruta == "/api/health":
            return await siguiente(request)

        usuario = await run_in_threadpool(_cargar_usuario, request)
        request.state.usuario = usuario
        es_api = ruta.startswith("/api/")

        if ruta in API_PUBLICA or ruta == LOGIN:
            return await siguiente(request)
        if usuario is None:
            if es_api:
                return JSONResponse({"detail": "Inicia sesión para continuar"}, status_code=401)
            volver = ruta + (f"?{request.url.query}" if request.url.query else "")
            destino = LOGIN if volver == "/" else f"{LOGIN}?volver={quote(volver, safe='')}"
            return RedirectResponse(destino, status_code=303)
        if usuario.debe_cambiar_clave and ruta not in API_CON_CLAVE_TEMPORAL:
            if es_api:
                return JSONResponse({"detail": "Debes cambiar tu contraseña antes de continuar"}, status_code=428)
            return RedirectResponse(LOGIN, status_code=303)
        if (minimo := PAGINAS_POR_ROL.get(ruta)) and NIVEL[usuario.rol] < NIVEL[minimo]:
            return RedirectResponse("/", status_code=303)
        return await siguiente(request)


def usuario_actual(request: Request) -> Usuario:
    usuario = getattr(request.state, "usuario", None)
    if usuario is None:
        raise HTTPException(401, "Inicia sesión para continuar")
    return usuario


def requiere(rol_minimo: str):
    """Dependencia de FastAPI: deja pasar al rol indicado y a los de más arriba (Visor < Auditor < Admin)."""
    def verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if NIVEL[usuario.rol] < NIVEL[rol_minimo]:
            raise HTTPException(403, f"Esta acción requiere el rol {rol_minimo}")
        return usuario
    return verificar
