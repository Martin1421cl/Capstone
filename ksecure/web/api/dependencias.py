from collections.abc import Iterator

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from ksecure.almacenamiento import boveda


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.sesiones() as db:
        yield db


def exigir_boveda(db: Session):
    """Sin clave de auditor no se puede cifrar el original, así que no se escanea."""
    if not boveda.esta_configurada(db):
        raise HTTPException(409, "Primero crea la clave de auditor")
