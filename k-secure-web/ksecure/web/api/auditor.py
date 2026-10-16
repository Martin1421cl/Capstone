"""Clave de auditor: se crea una vez y se pide cada vez que alguien quiere ver un dato original."""

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ksecure.almacenamiento import boveda, repositorio
from ksecure.web.api.dependencias import get_db

MAX_INTENTOS, BLOQUEO_SEGUNDOS = 5, 60

router = APIRouter(prefix="/api", tags=["auditor"])


class Clave(BaseModel):
    clave: str


class _Bloqueo:
    """5 claves incorrectas seguidas bloquean el desenmascarado por 1 minuto (contra fuerza bruta).

    shortcut: vive en memoria y es global; con login (más adelante) debe ser por usuario y persistente.
    """

    def __init__(self):
        self.fallos, self.hasta = 0, 0.0

    def verificar(self):
        if time.monotonic() < self.hasta:
            raise HTTPException(429, f"Demasiados intentos. Espera {int(self.hasta - time.monotonic()) + 1} s")

    def fallo(self):
        self.fallos += 1
        if self.fallos >= MAX_INTENTOS:
            self.fallos, self.hasta = 0, time.monotonic() + BLOQUEO_SEGUNDOS

    def exito(self):
        self.fallos = 0


bloqueo = _Bloqueo()


@router.get("/auditor")
def estado(db: Session = Depends(get_db)):
    return {"configurada": boveda.esta_configurada(db), "largo_minimo": boveda.MIN_LARGO_CLAVE}


@router.post("/auditor", status_code=201)
def configurar(datos: Clave, db: Session = Depends(get_db)):
    try:
        boveda.configurar(db, datos.clave)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"configurada": True}


@router.post("/hallazgos/{hallazgo_id}/revelar")
def revelar(hallazgo_id: int, datos: Clave, db: Session = Depends(get_db)):
    """Devuelve el dato original. Requiere la clave de auditor."""
    bloqueo.verificar()
    try:
        valor = repositorio.revelar(db, hallazgo_id, datos.clave)
    except boveda.ClaveIncorrecta:
        bloqueo.fallo()
        raise HTTPException(403, "Clave incorrecta") from None
    if valor is None:
        raise HTTPException(404, "Hallazgo no encontrado")
    bloqueo.exito()
    return {"valor": valor}
