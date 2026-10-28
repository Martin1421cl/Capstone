"""Bitácora (RF-17): solo lectura y solo para Admin. No hay endpoints para editar ni borrar eventos."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ksecure.almacenamiento import bitacora
from ksecure.almacenamiento.usuarios import ahora
from ksecure.web.api.dependencias import SOLO_ADMIN, get_db

router = APIRouter(prefix="/api/bitacora", tags=["bitácora"], dependencies=[SOLO_ADMIN])


@router.get("")
def listar(categoria: str = "", persona: int | None = None, buscar: str = Query("", max_length=100),
           dias: int | None = Query(None, ge=1, le=3650), pagina: int = Query(1, ge=1),
           por_pagina: int = Query(bitacora.POR_PAGINA, ge=1, le=100), db: Session = Depends(get_db)):
    """Eventos del más nuevo al más antiguo. categoria puede ser una categoría o "Alertas"."""
    return bitacora.listar(db, categoria, persona, buscar, dias, pagina, por_pagina)


@router.get("/csv")
def descargar(categoria: str = "", persona: int | None = None, buscar: str = Query("", max_length=100),
              dias: int | None = Query(None, ge=1, le=3650), desfase: int = Query(0, ge=-840, le=840),
              db: Session = Depends(get_db)):
    """La bitácora con los mismos filtros, en CSV para Excel. desfase: minutos de la zona del navegador."""
    contenido = bitacora.exportar_csv(db, categoria, persona, buscar, dias, desfase)
    nombre = f"bitacora-ksecure-{ahora():%Y-%m-%d}.csv"
    return Response(contenido.encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/resumen")
def resumen(db: Session = Depends(get_db)):
    """Cifras de los últimos 7 días y las categorías disponibles para filtrar."""
    return {**bitacora.resumen(db), "categorias": [bitacora.ALERTAS, *bitacora.CATEGORIAS]}
