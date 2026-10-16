"""Conexión a la base interna. Por defecto un SQLite en data/; en la nube, KSECURE_DB_URL (ej. Neon)."""

import os
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ksecure.almacenamiento.modelos import Base

_DATA = Path(__file__).resolve().parents[2] / "data"


def url_por_defecto() -> str:
    if url := os.environ.get("KSECURE_DB_URL"):
        return url
    _DATA.mkdir(exist_ok=True)
    return f"sqlite:///{_DATA / 'ksecure.db'}"


def crear_sesiones(url: str | None = None) -> sessionmaker:
    url = url or url_por_defecto()
    if url.startswith("sqlite"):
        # StaticPool solo para ":memory:" (tests): todas las sesiones ven la misma base.
        extra = {"poolclass": StaticPool} if url == "sqlite://" else {}
        engine = create_engine(url, connect_args={"check_same_thread": False}, **extra)
        event.listen(engine, "connect", _sqlite_foreign_keys)
    else:
        engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    _agregar_columnas_nuevas(engine)
    return sessionmaker(engine, expire_on_commit=False)


def _agregar_columnas_nuevas(engine: Engine):
    """create_all crea tablas nuevas pero no agrega columnas a las que ya existen.

    Esto suma las columnas que falten (siempre como opcionales), así una base de una
    versión anterior se actualiza sola y no se pierden escaneos ni reglas.
    shortcut: solo agrega columnas; si algún día se renombra o borra una, usar Alembic.
    """
    existentes = inspect(engine)
    with engine.begin() as conn:
        for tabla in Base.metadata.sorted_tables:
            if not existentes.has_table(tabla.name):
                continue
            actuales = {c["name"] for c in existentes.get_columns(tabla.name)}
            for col in tabla.columns:
                if col.name not in actuales:
                    tipo = col.type.compile(engine.dialect)
                    conn.execute(text(f'ALTER TABLE {tabla.name} ADD COLUMN "{col.name}" {tipo}'))


def _sqlite_foreign_keys(conn, _):
    # Sin esto SQLite ignora ON DELETE CASCADE.
    conn.execute("PRAGMA foreign_keys=ON")
