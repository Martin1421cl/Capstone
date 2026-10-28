"""Clave de auditor: la crea un Admin una vez y se pide cada vez que alguien quiere ver un dato original."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ksecure.almacenamiento import boveda, repositorio
from ksecure.almacenamiento.modelos import Usuario
from ksecure.almacenamiento.usuarios import AUDITOR, ahora
from ksecure.web.api.dependencias import SOLO_ADMIN, VISOR_O_MAS, get_db
from ksecure.web.sesion import requiere

MAX_INTENTOS, BLOQUEO = 5, timedelta(seconds=60)

router = APIRouter(prefix="/api", tags=["auditor"])


class Clave(BaseModel):
    clave: str


@router.get("/auditor", dependencies=[VISOR_O_MAS])
def estado(db: Session = Depends(get_db)):
    return {"configurada": boveda.esta_configurada(db), "largo_minimo": boveda.MIN_LARGO_CLAVE}


@router.post("/auditor", status_code=201, dependencies=[SOLO_ADMIN])
def configurar(datos: Clave, db: Session = Depends(get_db)):
    try:
        boveda.configurar(db, datos.clave)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"configurada": True}


@router.post("/hallazgos/{hallazgo_id}/revelar")
def revelar(hallazgo_id: int, datos: Clave, db: Session = Depends(get_db), quien=Depends(requiere(AUDITOR))):
    """Devuelve el dato original. Requiere la clave de auditor.

    5 claves incorrectas seguidas bloquean el desenmascarado 1 minuto, para esa cuenta (contra fuerza bruta).
    """
    u = db.get(Usuario, quien.id)
    momento = ahora()
    if u.auditor_bloqueado_hasta and u.auditor_bloqueado_hasta > momento:
        segundos = int((u.auditor_bloqueado_hasta - momento).total_seconds()) + 1
        raise HTTPException(429, f"Demasiados intentos. Espera {segundos} s")
    try:
        valor = repositorio.revelar(db, hallazgo_id, datos.clave)
    except boveda.ClaveIncorrecta:
        u.fallos_auditor = (u.fallos_auditor or 0) + 1
        if u.fallos_auditor >= MAX_INTENTOS:
            u.fallos_auditor, u.auditor_bloqueado_hasta = 0, momento + BLOQUEO
        db.commit()
        raise HTTPException(403, "Clave incorrecta") from None
    if valor is None:
        raise HTTPException(404, "Hallazgo no encontrado")
    if u.fallos_auditor:
        u.fallos_auditor = 0
        db.commit()
    return {"valor": valor}
