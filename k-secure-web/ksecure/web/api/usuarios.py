"""Administración de cuentas (solo rol Admin). No hay registro público."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ksecure.almacenamiento import usuarios
from ksecure.almacenamiento.usuarios import ADMIN, ErrorUsuario
from ksecure.web.api.dependencias import get_db
from ksecure.web.sesion import requiere

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])
solo_admin = requiere(ADMIN)


class CuentaNueva(BaseModel):
    usuario: str = Field(max_length=100)
    nombre: str = Field(max_length=100)
    correo: str = Field(max_length=200)
    rol: str


class CambiosCuenta(BaseModel):
    nombre: str = Field(max_length=100)
    correo: str = Field(max_length=200)
    rol: str
    activo: bool


@router.get("")
def listar(db: Session = Depends(get_db), _=Depends(solo_admin)):
    return [usuarios.publico(u) for u in usuarios.listar(db)]


@router.post("", status_code=201)
def crear(datos: CuentaNueva, db: Session = Depends(get_db), _=Depends(solo_admin)):
    """Crea la cuenta con una contraseña temporal, que se muestra solo esta vez."""
    try:
        cuenta, temporal = usuarios.crear_por_admin(db, datos.usuario, datos.nombre, datos.correo, datos.rol)
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    return {"usuario": usuarios.publico(cuenta), "clave_temporal": temporal}


@router.put("/{usuario_id}")
def actualizar(usuario_id: int, datos: CambiosCuenta, db: Session = Depends(get_db), admin=Depends(solo_admin)):
    try:
        cuenta = usuarios.actualizar(db, usuario_id, admin, datos.nombre, datos.correo, datos.rol, datos.activo)
    except LookupError:
        raise HTTPException(404, "Usuario no encontrado") from None
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    return usuarios.publico(cuenta)


@router.post("/{usuario_id}/restablecer")
def restablecer(usuario_id: int, db: Session = Depends(get_db), _=Depends(solo_admin)):
    """Nueva contraseña temporal (también desbloquea la cuenta y cierra sus sesiones)."""
    try:
        cuenta, temporal = usuarios.restablecer(db, usuario_id)
    except LookupError:
        raise HTTPException(404, "Usuario no encontrado") from None
    return {"usuario": usuarios.publico(cuenta), "clave_temporal": temporal}
