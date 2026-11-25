"""Endpoints para escanear: archivos subidos y bases de datos."""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ksecure.almacenamiento import reglas
from ksecure.almacenamiento.repositorio import Guardado
from ksecure.escaneo.archivos import escanear_archivos, titulo_de
from ksecure.escaneo.bases_datos import (MOTORES, PUERTOS, ConexionError, DatosConexion, conectar,
                                         escanear_bd, listar_tablas)
from ksecure.escaneo.resultado import ResultadoEscaneo
from ksecure.web.api.dependencias import AUDITOR_O_MAS, exigir_boveda, get_db
from ksecure.web.sesion import anotar

MAX_ARCHIVO = 100 * 1024 * 1024  # 100 MB, igual que ferret-scan

router = APIRouter(prefix="/api", tags=["escanear"])


def _hallazgos(n: int) -> str:
    return "1 hallazgo" if n == 1 else f"{n:,} hallazgos".replace(",", ".")


def _escanear_y_guardar(db: Session, origen_tipo: str, origen_nombre: str, escanear) -> ResultadoEscaneo:
    """Escanea guardando los hallazgos por lotes (HU-29). Si algo falla, no queda un escaneo a medias."""
    guardado = Guardado(db, origen_tipo, origen_nombre)
    resultado = ResultadoEscaneo(origen_tipo, origen_nombre, al_lote=guardado.agregar)
    try:
        escanear(resultado)
        guardado.terminar(resultado)
    except BaseException:
        try:
            guardado.cancelar()
        except Exception:  # noqa: S110 - que no tape el error original
            pass
        raise
    resultado.escaneo_id = guardado.escaneo.id
    return resultado


@router.post("/archivos", dependencies=[AUDITOR_O_MAS])
async def escanear_subidos(archivos: list[UploadFile], request: Request, db: Session = Depends(get_db)):
    """Escanea documentos (docx, pdf, xlsx, csv, txt...) y bases SQLite (.db) en un solo escaneo."""
    exigir_boveda(db)
    with tempfile.TemporaryDirectory() as carpeta:
        en_disco = []
        for i, archivo in enumerate(archivos):
            nombre = os.path.basename(archivo.filename or "archivo")
            # Del nombre del usuario solo se usa la extensión: nunca decide la ruta.
            ruta = Path(carpeta) / f"{i}{Path(nombre).suffix.lower()}"
            tamano = 0
            with open(ruta, "wb") as destino:  # de a 1 MB: el archivo nunca está entero en memoria (HU-29)
                while trozo := await archivo.read(1024 * 1024):
                    tamano += len(trozo)
                    if tamano > MAX_ARCHIVO:
                        raise HTTPException(413, f"{nombre} supera los 100 MB")
                    destino.write(trozo)
            en_disco.append((str(ruta), nombre))
        validadores = reglas.validadores_activos(db)
        # RNF-18: el escaneo corre en un hilo aparte; mientras tanto el servidor sigue atendiendo a los demás.
        resultado = await run_in_threadpool(
            _escanear_y_guardar, db, "archivo", titulo_de([n for _, n in en_disco]),
            lambda r: escanear_archivos(en_disco, validadores, r))
    nombres = ", ".join(n for _, n in en_disco)
    anotar(request, db, "escaneo_archivos",
           f"{nombres} · {_hallazgos(resultado.total)} (escaneo #{resultado.escaneo_id})",
           escaneo_id=resultado.escaneo_id)
    return {"escaneo_id": resultado.escaneo_id}


class Conexion(BaseModel):
    motor: str
    host: str = "localhost"
    puerto: int | None = None
    base: str = ""
    usuario: str = ""
    clave: str = ""


class PedidoEscaneoBD(BaseModel):
    conexion: Conexion
    tablas: list[str] | None = None  # siempre se revisan completas: todas sus filas


def _conectar(c: Conexion):
    if c.motor == "sqlite":
        # Un servidor web no debe abrir rutas arbitrarias de su disco: el .db se sube como archivo.
        raise HTTPException(400, "Para SQLite sube el archivo .db en Escanear archivos")
    try:
        return conectar(DatosConexion(**c.model_dump()))
    except ConexionError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/bd/motores", dependencies=[AUDITOR_O_MAS])
def motores():
    return [{"id": k, "nombre": v, "puerto": PUERTOS.get(k)} for k, v in MOTORES.items()]


@router.post("/bd/probar", dependencies=[AUDITOR_O_MAS])
def probar_conexion(conexion: Conexion):
    """Prueba la conexión y devuelve las tablas, para elegir cuáles escanear."""
    engine = _conectar(conexion)
    try:
        return {"tablas": listar_tablas(engine)}
    finally:
        engine.dispose()


@router.post("/bd/escanear", dependencies=[AUDITOR_O_MAS])
def escanear_base(pedido: PedidoEscaneoBD, request: Request, db: Session = Depends(get_db)):
    exigir_boveda(db)
    engine = _conectar(pedido.conexion)
    try:
        descripcion = DatosConexion(**pedido.conexion.model_dump()).descripcion()
        validadores = reglas.validadores_activos(db)
        resultado = _escanear_y_guardar(
            db, "bd", descripcion,
            lambda r: escanear_bd(engine, descripcion, None, pedido.tablas, validadores, r))
    finally:
        engine.dispose()
    tablas = len(resultado.filas_por_fuente)
    anotar(request, db, "escaneo_bd",  # la descripción no lleva la contraseña de la base
           f"{descripcion} · {tablas} {'tabla' if tablas == 1 else 'tablas'} · "
           f"{_hallazgos(resultado.total)} (escaneo #{resultado.escaneo_id})", escaneo_id=resultado.escaneo_id)
    return {"escaneo_id": resultado.escaneo_id}
