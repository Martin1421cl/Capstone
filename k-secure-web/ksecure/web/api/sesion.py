"""Ingresar, salir, cambiar o recuperar la contraseña y configurar el primer administrador."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ksecure.almacenamiento import bitacora, usuarios
from ksecure.almacenamiento.usuarios import CuentaBloqueada, CuentaDesactivada, ErrorUsuario
from ksecure.correo import ErrorCorreo, mensaje_codigo
from ksecure.web.api.dependencias import get_db
from ksecure.web.sesion import COOKIE, anotar, borrar_cookie, ip_de, poner_cookie, usuario_actual

router = APIRouter(prefix="/api/sesion", tags=["sesión"])
log = logging.getLogger("ksecure.correo")


class Ingreso(BaseModel):
    usuario: str = Field(max_length=100)
    clave: str = Field(max_length=200)


class PrimerAdmin(BaseModel):
    usuario: str = Field(max_length=100)
    nombre: str = Field(max_length=100)
    correo: str = Field(max_length=200)
    clave: str = Field(max_length=200)


class CambioClave(BaseModel):
    actual: str | None = Field(None, max_length=200)
    nueva: str = Field(max_length=200)
    correo: str | None = Field(None, max_length=200)


class PedidoCodigo(BaseModel):
    cuenta: str = Field(max_length=200)  # usuario o correo


class Recuperacion(BaseModel):
    cuenta: str = Field(max_length=200)
    codigo: str = Field(max_length=20)
    clave: str = Field(max_length=200)


@router.get("")
def estado(request: Request, db: Session = Depends(get_db)):
    """Si K-Secure ya tiene cuentas y quién es el usuario de esta sesión (o null)."""
    usuario = getattr(request.state, "usuario", None)
    return {
        "configurado": usuarios.hay_usuarios(db),
        "usuario": usuarios.publico(usuario) if usuario else None,
        "largo_minimo": usuarios.MIN_LARGO_CLAVE,
        "correo": request.app.state.correo.configurado,  # si los códigos salen por correo o a la terminal
    }


@router.post("/ingresar")
def ingresar(datos: Ingreso, request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        usuario = usuarios.autenticar(db, datos.usuario, datos.clave)
    except CuentaBloqueada as e:
        if e.nueva:
            anotar(request, db, "cuenta_bloqueada",
                   f"{usuarios.MAX_INTENTOS} contraseñas incorrectas seguidas: bloqueada {e.minutos} min", e.cuenta)
        else:
            anotar(request, db, "ingreso_fallido", "Intento mientras la cuenta está bloqueada", e.cuenta)
        raise HTTPException(429, str(e)) from None
    except CuentaDesactivada as e:
        anotar(request, db, "ingreso_fallido", "Intento en una cuenta desactivada", e.cuenta)
        raise HTTPException(403, "Tu cuenta está desactivada. Habla con un administrador.") from None
    if usuario is None:
        if cuenta := usuarios.buscar(db, datos.usuario):
            anotar(request, db, "ingreso_fallido",
                   f"Contraseña incorrecta (intento {cuenta.intentos_fallidos} de {usuarios.MAX_INTENTOS})", cuenta)
        else:  # sin el nombre escrito: podría ser una contraseña puesta en el campo equivocado
            anotar(request, db, "ingreso_desconocido", "Alguien intentó entrar con un usuario que no existe", None)
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    anotar(request, db, "ingreso", "Con una contraseña temporal" if usuario.debe_cambiar_clave else "", usuario)
    poner_cookie(response, request, usuarios.abrir_sesion(db, usuario))
    return {"usuario": usuarios.publico(usuario)}


@router.post("/configurar", status_code=201)
def configurar(datos: PrimerAdmin, request: Request, response: Response, db: Session = Depends(get_db)):
    """Crea el primer administrador. Solo funciona mientras no exista ninguna cuenta."""
    try:
        usuario = usuarios.configurar_primer_admin(db, datos.usuario, datos.nombre, datos.correo, datos.clave)
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    anotar(request, db, "configuracion_inicial", f"Creó la cuenta de administrador @{usuario.usuario}", usuario)
    poner_cookie(response, request, usuarios.abrir_sesion(db, usuario))
    return {"usuario": usuarios.publico(usuario)}


@router.post("/salir", status_code=204)
def salir(request: Request, response: Response, db: Session = Depends(get_db)):
    if getattr(request.state, "usuario", None):
        anotar(request, db, "salida")
    usuarios.cerrar_sesion(db, request.cookies.get(COOKIE))
    borrar_cookie(response)


@router.post("/cambiar-clave")
def cambiar_clave(datos: CambioClave, request: Request, db: Session = Depends(get_db),
                  usuario=Depends(usuario_actual)):
    era_temporal, tenia_correo = usuario.debe_cambiar_clave, bool(usuario.correo)
    try:
        actualizado = usuarios.cambiar_clave(db, usuario.id, datos.actual, datos.nueva,
                                             request.cookies.get(COOKIE), datos.correo)
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    detalle = ["reemplazó la contraseña temporal" if era_temporal else "",
               f"registró su correo {actualizado.correo}" if not tenia_correo else ""]
    texto = "; ".join(d for d in detalle if d)
    anotar(request, db, "clave_cambiada", texto[:1].upper() + texto[1:], actualizado)
    return {"usuario": usuarios.publico(actualizado)}


# --- ¿Olvidaste tu contraseña? (RF-14) -----------------------------------------------------------

def _enviar_codigo(sesiones, correo, cuenta: str, ip: str | None):
    """Corre después de responder: así la respuesta tarda lo mismo exista o no la cuenta."""
    with sesiones() as db:
        pedido = usuarios.pedir_codigo(db, cuenta)
        if pedido is None:
            return
        u, codigo = pedido
        minutos = int(usuarios.CODIGO_VIGENCIA.total_seconds() // 60)
        asunto, texto, html = mensaje_codigo(u.nombre, u.usuario, codigo, minutos)
        try:
            correo.enviar(u.correo, asunto, texto, html)
            detalle = f"Código enviado a {u.correo}" if correo.configurado else "Código escrito en la terminal (correo sin configurar)"
        except ErrorCorreo as e:
            log.error("No se pudo enviar el código de @%s: %s", u.usuario, e)
            detalle = f"No se pudo enviar el correo: {e}"
        bitacora.registrar(db, "codigo_enviado", detalle, usuario=u, ip=ip)


@router.post("/recuperar", status_code=202)
def pedir_codigo(datos: PedidoCodigo, request: Request, tareas: BackgroundTasks):
    """Manda un código de 6 dígitos al correo de la cuenta. Responde igual aunque la cuenta no exista."""
    tareas.add_task(_enviar_codigo, request.app.state.sesiones, request.app.state.correo, datos.cuenta, ip_de(request))
    return {"detail": "Si la cuenta existe y tiene correo, te enviamos un código.",
            "minutos": int(usuarios.CODIGO_VIGENCIA.total_seconds() // 60)}


@router.post("/recuperar/confirmar")
def recuperar(datos: Recuperacion, request: Request, response: Response, db: Session = Depends(get_db)):
    """Con el código crea la contraseña nueva y deja la sesión iniciada."""
    try:
        usuario = usuarios.recuperar_clave(db, datos.cuenta, datos.codigo, datos.clave)
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    anotar(request, db, "clave_recuperada", "Con el código que llegó a su correo", usuario)
    poner_cookie(response, request, usuarios.abrir_sesion(db, usuario))
    return {"usuario": usuarios.publico(usuario)}
