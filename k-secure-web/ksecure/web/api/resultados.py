"""Endpoints para ver el historial y los resultados (siempre enmascarados)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ksecure.almacenamiento import repositorio
from ksecure.web.api.dependencias import AUDITOR_O_MAS, VISOR_O_MAS, get_db

router = APIRouter(prefix="/api/escaneos", tags=["resultados"])


@router.get("", dependencies=[VISOR_O_MAS])
def listar(db: Session = Depends(get_db)):
    return repositorio.listar(db)


@router.get("/{escaneo_id}", dependencies=[VISOR_O_MAS])
def detalle(escaneo_id: int, db: Session = Depends(get_db)):
    if (d := repositorio.detalle(db, escaneo_id)) is None:
        raise HTTPException(404, "Escaneo no encontrado")
    return d


@router.get("/{escaneo_id}/hallazgos", dependencies=[VISOR_O_MAS])
def hallazgos(escaneo_id: int, riesgo: str = "", tipo: str = "", buscar: str = "",
              pagina: int = Query(1, ge=1), por_pagina: int = Query(50, ge=1, le=200),
              orden: Literal["riesgo", "tipo", "confianza", "ubicacion"] = "riesgo", invertir: bool = False,
              db: Session = Depends(get_db)):
    """Hallazgos enmascarados, filtrados y ordenados. Por defecto: primero los de mayor riesgo."""
    return repositorio.hallazgos(db, escaneo_id, riesgo, tipo, buscar, pagina, por_pagina, orden, invertir)


@router.get("/{escaneo_id}/por-tipo", dependencies=[VISOR_O_MAS])
def por_tipo(escaneo_id: int, riesgo: str = "", tipo: str = "", buscar: str = "",
             pagina: int = Query(1, ge=1), por_pagina: int = Query(50, ge=1, le=200),
             db: Session = Depends(get_db)):
    """Hallazgos como planilla: una columna por tipo de dato (RUT, correo, teléfono...), enmascarados.

    Usa los mismos filtros que /hallazgos. La página n trae los hallazgos n de cada columna.
    """
    return repositorio.por_tipo(db, escaneo_id, riesgo, tipo, buscar, pagina, por_pagina)


@router.delete("/{escaneo_id}", status_code=204, dependencies=[AUDITOR_O_MAS])
def borrar(escaneo_id: int, db: Session = Depends(get_db)):
    if not repositorio.borrar(db, escaneo_id):
        raise HTTPException(404, "Escaneo no encontrado")
