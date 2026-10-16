"""Endpoints para escanear: archivos subidos y bases de datos."""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ksecure.almacenamiento import reglas, repositorio
from ksecure.escaneo.archivos import escanear_archivos
from ksecure.escaneo.bases_datos import (MOTORES, PUERTOS, ConexionError, DatosConexion, conectar,
                                         escanear_bd, listar_tablas)
from ksecure.web.api.dependencias import exigir_boveda, get_db

MAX_ARCHIVO = 100 * 1024 * 1024  # 100 MB, igual que ferret-scan

router = APIRouter(prefix="/api", tags=["escanear"])


@router.post("/archivos")
async def escanear_subidos(archivos: list[UploadFile], db: Session = Depends(get_db)):
    """Escanea documentos (docx, pdf, xlsx, csv, txt...) y bases SQLite (.db) en un solo escaneo."""
    exigir_boveda(db)
    with tempfile.TemporaryDirectory() as carpeta:
        en_disco = []
        for i, archivo in enumerate(archivos):
            nombre = os.path.basename(archivo.filename or "archivo")
            datos = await archivo.read(MAX_ARCHIVO + 1)
            if len(datos) > MAX_ARCHIVO:
                raise HTTPException(413, f"{nombre} supera los 100 MB")
            # Del nombre del usuario solo se usa la extensión: nunca decide la ruta.
            ruta = Path(carpeta) / f"{i}{Path(nombre).suffix.lower()}"
            ruta.write_bytes(datos)
            en_disco.append((str(ruta), nombre))
        resultado = escanear_archivos(en_disco, reglas.validadores_activos(db))
    return {"escaneo_id": repositorio.guardar(db, resultado).id}


class Conexion(BaseModel):
    motor: str
    host: str = "localhost"
    puerto: int | None = None
    base: str = ""
    usuario: str = ""
    clave: str = ""


class PedidoEscaneoBD(BaseModel):
    conexion: Conexion
    tablas: list[str] | None = None
    max_filas: int = Field(1000, ge=1, le=100_000)


def _conectar(c: Conexion):
    if c.motor == "sqlite":
        # Un servidor web no debe abrir rutas arbitrarias de su disco: el .db se sube como archivo.
        raise HTTPException(400, "Para SQLite sube el archivo .db en Escanear archivos")
    try:
        return conectar(DatosConexion(**c.model_dump()))
    except ConexionError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/bd/motores")
def motores():
    return [{"id": k, "nombre": v, "puerto": PUERTOS.get(k)} for k, v in MOTORES.items()]


@router.post("/bd/probar")
def probar_conexion(conexion: Conexion):
    """Prueba la conexión y devuelve las tablas, para elegir cuáles escanear."""
    engine = _conectar(conexion)
    try:
        return {"tablas": listar_tablas(engine)}
    finally:
        engine.dispose()


@router.post("/bd/escanear")
def escanear_base(pedido: PedidoEscaneoBD, db: Session = Depends(get_db)):
    exigir_boveda(db)
    engine = _conectar(pedido.conexion)
    try:
        descripcion = DatosConexion(**pedido.conexion.model_dump()).descripcion()
        resultado = escanear_bd(engine, descripcion, pedido.max_filas, pedido.tablas, reglas.validadores_activos(db))
    finally:
        engine.dispose()
    return {"escaneo_id": repositorio.guardar(db, resultado).id}
