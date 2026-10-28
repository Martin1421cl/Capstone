from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ksecure.almacenamiento import boveda
from ksecure.almacenamiento.usuarios import ADMIN, AUDITOR, VISOR
from ksecure.web.sesion import requiere

# Permisos por rol para los endpoints: cada rol puede todo lo del anterior (Visor < Auditor < Admin).
VISOR_O_MAS = Depends(requiere(VISOR))      # ver resultados enmascarados y reglas
AUDITOR_O_MAS = Depends(requiere(AUDITOR))  # escanear, borrar escaneos, revelar con la clave de auditor
SOLO_ADMIN = Depends(requiere(ADMIN))       # cuentas, reglas y crear la clave de auditor


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.sesiones() as db:
        yield db


def exigir_boveda(db: Session):
    """Sin clave de auditor no se puede cifrar el original, así que no se escanea."""
    if not boveda.esta_configurada(db):
        raise HTTPException(409, "Primero crea la clave de auditor")
