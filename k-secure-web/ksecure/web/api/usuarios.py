"""Administración de cuentas (solo rol Admin). No hay registro público."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ksecure.almacenamiento import usuarios
from ksecure.almacenamiento.modelos import Usuario
from ksecure.almacenamiento.usuarios import ADMIN, ErrorUsuario
from ksecure.correo import ErrorCorreo, mensaje_prueba
from ksecure.web.api.dependencias import get_db
from ksecure.web.sesion import anotar, requiere

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
def crear(datos: CuentaNueva, request: Request, db: Session = Depends(get_db), _=Depends(solo_admin)):
    """Crea la cuenta con una contraseña temporal, que se muestra solo esta vez."""
    try:
        cuenta, temporal = usuarios.crear_por_admin(db, datos.usuario, datos.nombre, datos.correo, datos.rol)
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    anotar(request, db, "cuenta_creada", f"Cuenta @{cuenta.usuario} ({cuenta.nombre}) con rol {cuenta.rol}", afectado=cuenta)
    return {"usuario": usuarios.publico(cuenta), "clave_temporal": temporal}


CAMPOS = (("nombre", "nombre"), ("correo", "correo"), ("rol", "rol"))


@router.put("/{usuario_id}")
def actualizar(usuario_id: int, datos: CambiosCuenta, request: Request, db: Session = Depends(get_db),
               admin=Depends(solo_admin)):
    antes = db.get(Usuario, usuario_id)
    antes = {c: getattr(antes, c) for c in ("nombre", "correo", "rol", "activo")} if antes else {}
    try:
        cuenta = usuarios.actualizar(db, usuario_id, admin, datos.nombre, datos.correo, datos.rol, datos.activo)
    except LookupError:
        raise HTTPException(404, "Usuario no encontrado") from None
    except ErrorUsuario as e:
        raise HTTPException(400, str(e)) from None
    cambios = [f"{texto}: {antes[c] or '—'} → {getattr(cuenta, c) or '—'}"
               for c, texto in CAMPOS if antes[c] != getattr(cuenta, c)]
    if cambios:
        anotar(request, db, "cuenta_editada", f"Cuenta @{cuenta.usuario}: " + "; ".join(cambios), afectado=cuenta)
    if antes["activo"] != cuenta.activo:
        anotar(request, db, "cuenta_activada" if cuenta.activo else "cuenta_desactivada", f"Cuenta @{cuenta.usuario}",
               afectado=cuenta)
    return usuarios.publico(cuenta)


@router.post("/{usuario_id}/restablecer")
def restablecer(usuario_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(solo_admin)):
    """Nueva contraseña temporal (también desbloquea la cuenta y cierra sus sesiones)."""
    if usuario_id == admin.id:
        raise HTTPException(400, "Para tu propia cuenta usa «Cambiar contraseña» en el menú con tu nombre")
    try:
        cuenta, temporal = usuarios.restablecer(db, usuario_id)
    except LookupError:
        raise HTTPException(404, "Usuario no encontrado") from None
    anotar(request, db, "clave_restablecida", f"Contraseña temporal nueva para @{cuenta.usuario}", afectado=cuenta)
    return {"usuario": usuarios.publico(cuenta), "clave_temporal": temporal}


@router.post("/correo-prueba")
def correo_prueba(request: Request, admin=Depends(solo_admin)):
    """Manda un correo de prueba al administrador, para revisar que el envío esté bien configurado."""
    correo = request.app.state.correo
    if not admin.correo:
        raise HTTPException(400, "Tu cuenta no tiene correo")
    try:
        correo.enviar(admin.correo, *mensaje_prueba(admin.nombre))
    except ErrorCorreo as e:
        raise HTTPException(502, str(e)) from None
    return {"para": admin.correo, "configurado": correo.configurado}
