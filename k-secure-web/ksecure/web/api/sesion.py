"""Ingresar, salir, cambiar la contraseña y configurar el primer administrador."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ksecure.almacenamiento import usuarios
from ksecure.almacenamiento.usuarios import CuentaBloqueada, CuentaDesactivada, ErrorUsuario
from ksecure.web.api.dependencias import get_db
from ksecure.web.sesion import COOKIE, borrar_cookie, poner_cookie, usuario_actual

router = APIRouter(prefix="/api/sesion", tags=["sesión"])


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


@router.get("")
def estado(request: Request, db: Session = Depends(get_db)):
    """Si K-Secure ya tiene cuentas y quién es el usuario de esta sesión (o null)."""
    usuario = getattr(request.state, "usuario", None)
    return {
        "configurado": usuarios.hay_usuarios(db),
        "usuario": usuarios.publico(usuario) if usuario else None,
        "largo_minimo": usuarios.MIN_LARGO_CLAVE,
    }


@router.post("/ingresar")
def ingresar(datos: Ingreso, request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        usuario = usuarios.autenticar(db, datos.usuario, datos.clave)
    except CuentaBloqueada as e:
        raise HTTPException(429, str(e)) from None
    except CuentaDesactivada:
        raise HTTPException(403, "Tu cuenta está desactivada. Habla con un administrador.") from None
    if usuario is None:
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    poner_cookie(response, request, usuarios.abrir_sesion(db, usuario))
    return {"usuario": usuarios.publico(usuario)}


@router.post("/configurar", status_code=201)
def configurar(datos: PrimerAdmin, request: Request, response: Response, db: Session = Depends(get_db)):
    """Crea el primer administrador. Solo funciona mientras no exista ninguna cuenta."""
    try:
        usuario = usuarios.configurar_primer_admin(db, datos.usuario, datos.nombre, datos.correo, datos.clave)
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    poner_cookie(response, request, usuarios.abrir_sesion(db, usuario))
    return {"usuario": usuarios.publico(usuario)}


@router.post("/salir", status_code=204)
def salir(request: Request, response: Response, db: Session = Depends(get_db)):
    usuarios.cerrar_sesion(db, request.cookies.get(COOKIE))
    borrar_cookie(response)


@router.post("/cambiar-clave")
def cambiar_clave(datos: CambioClave, request: Request, db: Session = Depends(get_db),
                  usuario=Depends(usuario_actual)):
    try:
        actualizado = usuarios.cambiar_clave(db, usuario.id, datos.actual, datos.nueva,
                                             request.cookies.get(COOKIE), datos.correo)
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    return {"usuario": usuarios.publico(actualizado)}
