"""Endpoints para ver el historial y los resultados (siempre enmascarados)."""

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ksecure import exportar as formatos
from ksecure.almacenamiento import repositorio
from ksecure.almacenamiento.bitacora import describir_hallazgo
from ksecure.almacenamiento.modelos import Escaneo, Hallazgo
from ksecure.almacenamiento.usuarios import ahora
from ksecure.core.texto import slug
from ksecure.web.api.dependencias import AUDITOR_O_MAS, VISOR_O_MAS, get_db
from ksecure.web.sesion import anotar

router = APIRouter(prefix="/api/escaneos", tags=["resultados"])

# Filtro por revisión (RF-16): "" todos, o pendiente, confirmado, falso_positivo, sin_falsos (todo menos falsos positivos).
Revision = Literal["", "pendiente", "confirmado", "falso_positivo", "sin_falsos"]
ESTADO_TEXTO = {"pendiente": "Pendiente", "confirmado": "Confirmado", "falso_positivo": "Falso positivo"}


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
              revision: Revision = "", db: Session = Depends(get_db)):
    """Hallazgos enmascarados, filtrados y ordenados. Por defecto: primero los de mayor riesgo."""
    return repositorio.hallazgos(db, escaneo_id, riesgo, tipo, buscar, pagina, por_pagina, orden, invertir, revision)


@router.get("/{escaneo_id}/por-tipo", dependencies=[VISOR_O_MAS])
def por_tipo(escaneo_id: int, riesgo: str = "", tipo: str = "", buscar: str = "",
             pagina: int = Query(1, ge=1), por_pagina: int = Query(50, ge=1, le=200),
             revision: Revision = "", db: Session = Depends(get_db)):
    """Hallazgos como planilla: una columna por tipo de dato (RUT, correo, teléfono...), enmascarados.

    Usa los mismos filtros que /hallazgos. La página n trae los hallazgos n de cada columna.
    """
    return repositorio.por_tipo(db, escaneo_id, riesgo, tipo, buscar, pagina, por_pagina, revision)


TIPOS_ARCHIVO = {"csv": "text/csv; charset=utf-8", "json": "application/json", "pdf": "application/pdf"}


@router.get("/{escaneo_id}/exportar", dependencies=[VISOR_O_MAS])
def exportar(escaneo_id: int, request: Request, formato: Literal["csv", "json", "pdf"] = "csv",
             riesgo: str = "", tipo: str = "", buscar: str = Query("", max_length=100), revision: Revision = "",
             desfase: int = Query(0, ge=-840, le=840), db: Session = Depends(get_db)):
    """Descarga los hallazgos con los filtros de la pantalla, siempre enmascarados (RF-15).

    Lo puede hacer cualquiera que vea los resultados, y queda en la bitácora.
    desfase: minutos de la zona del navegador (getTimezoneOffset), para la hora del reporte.
    """
    datos = repositorio.para_exportar(db, escaneo_id, riesgo, tipo, buscar, revision)
    if datos is None:
        raise HTTPException(404, "Escaneo no encontrado")
    quien = request.state.usuario
    if formato == "csv":
        contenido = formatos.a_csv(datos)
    elif formato == "json":
        contenido = formatos.a_json(datos, quien, ahora())
    else:
        try:
            contenido = formatos.a_pdf(datos, quien, ahora() - timedelta(minutes=desfase))
        except ImportError:
            raise HTTPException(501, "Falta instalar reportlab para el PDF: pip install -r requirements.txt") from None
    e = datos["escaneo"]
    filtros = formatos.filtros_texto(datos["filtros"])
    anotar(request, db, "resultados_exportados",
           f"Escaneo #{e['id']}: {e['origen_nombre']} · {formato.upper()} · {formatos._miles(len(datos['hallazgos']))} hallazgos"
           + ("" if filtros.startswith("Sin filtros") else f" ({filtros})"), escaneo_id=e["id"])
    nombre = f"ksecure-escaneo-{e['id']}-{slug(e['origen_nombre'])}.{formato}"
    return Response(contenido, media_type=TIPOS_ARCHIVO[formato],
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


# --- Revisión de hallazgos (RF-16): solo Auditor y Admin; cada cambio queda en la bitácora ---------

class Marca(BaseModel):
    estado: Literal["pendiente", "confirmado", "falso_positivo"]
    nota: str | None = Field(None, max_length=repositorio.MAX_NOTA)


class MarcaVarios(Marca):
    riesgo: str = ""
    tipo: str = ""
    buscar: str = Field("", max_length=100)
    revision: Revision = ""


def _con_nota(texto: str, nota: str | None) -> str:
    nota = " ".join((nota or "").split())
    return f"{texto} · motivo: «{nota}»" if nota else texto


@router.put("/{escaneo_id}/hallazgos/{hallazgo_id}/revision", dependencies=[AUDITOR_O_MAS])
def revisar(escaneo_id: int, hallazgo_id: int, datos: Marca, request: Request, db: Session = Depends(get_db)):
    """Marca un hallazgo como confirmado (sí es un dato sensible), falso positivo o de nuevo pendiente."""
    h = repositorio.revisar(db, escaneo_id, hallazgo_id, datos.estado, request.state.usuario, datos.nota)
    if h is None:
        raise HTTPException(404, "Hallazgo no encontrado")
    anotar(request, db, "hallazgo_revisado",
           _con_nota(f"{ESTADO_TEXTO[datos.estado]}: {describir_hallazgo(h)}", h.nota_revision), escaneo_id=escaneo_id)
    return repositorio._item(h)


@router.post("/{escaneo_id}/revision", dependencies=[AUDITOR_O_MAS])
def revisar_varios(escaneo_id: int, datos: MarcaVarios, request: Request, db: Session = Depends(get_db)):
    """Marca de una vez todos los hallazgos que cumplen los filtros de la pantalla (ej. una columna completa)."""
    e = db.get(Escaneo, escaneo_id)
    if e is None:
        raise HTTPException(404, "Escaneo no encontrado")
    n = repositorio.revisar_filtrados(db, escaneo_id, datos.estado, request.state.usuario, datos.nota,
                                      datos.riesgo, datos.tipo, datos.buscar, datos.revision)
    filtros = formatos.filtros_texto(datos.model_dump())
    anotar(request, db, "hallazgos_revisados",
           _con_nota(f"{formatos._miles(n)} {'hallazgo' if n == 1 else 'hallazgos'} → {ESTADO_TEXTO[datos.estado]} "
                     f"(escaneo #{e.id}: {e.origen_nombre}; {filtros[:1].lower() + filtros[1:]})", datos.nota),
           escaneo_id=e.id)
    return {"marcados": n}


@router.delete("/{escaneo_id}", status_code=204, dependencies=[AUDITOR_O_MAS])
def borrar(escaneo_id: int, request: Request, db: Session = Depends(get_db)):
    if e := db.get(Escaneo, escaneo_id):
        total = db.scalar(select(func.count()).select_from(Hallazgo).where(Hallazgo.escaneo_id == escaneo_id))
        anotar(request, db, "escaneo_borrado", f"Escaneo #{e.id}: {e.origen_nombre} ({total} hallazgos y sus originales cifrados)",
               escaneo_id=e.id, guardar=False)  # queda junto con el borrado, en el mismo commit
    if not repositorio.borrar(db, escaneo_id):
        raise HTTPException(404, "Escaneo no encontrado")
