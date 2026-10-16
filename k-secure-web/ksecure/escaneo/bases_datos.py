"""Escaneo de bases de datos en SOLO LECTURA (adaptado de conexiones.py del K-Secure anterior).

K-Secure solo ejecuta SELECT. Además, en SQLite, PostgreSQL y MySQL la conexión
se abre en modo lectura, así que el propio motor rechazaría cualquier escritura.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, event, inspect, select
from sqlalchemy.engine import URL, Engine

from ksecure.escaneo.celdas import escanear_filas
from ksecure.escaneo.resultado import ResultadoEscaneo
from ksecure.validators import default_validators
from ksecure.validators.base import Validator

MOTORES = {
    "sqlite": "SQLite",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL / MariaDB",
    "sqlserver": "SQL Server",
    "oracle": "Oracle",
}
PUERTOS = {"postgresql": 5432, "mysql": 3306, "sqlserver": 1433, "oracle": 1521}
_DRIVERS = {
    "postgresql": "postgresql+psycopg",
    "mysql": "mysql+pymysql",
    "sqlserver": "mssql+pymssql",
    "oracle": "oracle+oracledb",
}
_TIMEOUT = 10  # segundos para conectarse


class ConexionError(Exception):
    """Error para mostrarle al usuario tal cual (credenciales malas, host caído...)."""


@dataclass
class DatosConexion:
    motor: str
    host: str = "localhost"
    puerto: int | None = None
    base: str = ""        # nombre de la base; en Oracle, el service name
    usuario: str = ""
    clave: str = ""
    ruta: str = ""        # solo SQLite

    def descripcion(self) -> str:
        nombre = MOTORES.get(self.motor, self.motor)
        if self.motor == "sqlite":
            return f"{nombre} · {Path(self.ruta).name}"
        return f"{nombre} · {self.base}@{self.host}"


def _engine_sqlite(ruta: str) -> Engine:
    path = Path(ruta)
    if not path.is_file():
        raise ConexionError(f"No existe el archivo {path.name}")
    uri = path.resolve().as_uri() + "?mode=ro"
    return create_engine("sqlite://", creator=lambda: sqlite3.connect(uri, uri=True, check_same_thread=False))


def _engine_servidor(datos: DatosConexion) -> Engine:
    oracle = datos.motor == "oracle"
    url = URL.create(
        _DRIVERS[datos.motor],
        username=datos.usuario or None,
        password=datos.clave or None,
        host=datos.host or "localhost",
        port=datos.puerto or PUERTOS[datos.motor],
        database=None if oracle else (datos.base or None),
        query={"service_name": datos.base} if oracle and datos.base else {},
    )
    connect_args = {
        "postgresql": {"options": "-c default_transaction_read_only=on", "connect_timeout": _TIMEOUT},
        "mysql": {"connect_timeout": _TIMEOUT},
        "sqlserver": {"login_timeout": _TIMEOUT},
        "oracle": {"tcp_connect_timeout": _TIMEOUT},
    }[datos.motor]
    engine = create_engine(url, connect_args=connect_args)
    if datos.motor == "mysql":
        @event.listens_for(engine, "connect")
        def _solo_lectura(conn, _):
            with conn.cursor() as cur:
                cur.execute("SET SESSION TRANSACTION READ ONLY")
    return engine


def conectar(datos: DatosConexion) -> Engine:
    """Abre la conexión y comprueba que funcione."""
    if datos.motor == "sqlite":
        engine = _engine_sqlite(datos.ruta)
    elif datos.motor in _DRIVERS:
        engine = _engine_servidor(datos)
    else:
        raise ConexionError(f"Motor no soportado: {datos.motor}")
    try:
        with engine.connect():
            pass
    except Exception as e:  # el mensaje del motor es lo más útil para el usuario
        engine.dispose()
        raise ConexionError(f"No se pudo conectar: {str(e).splitlines()[0][:200]}") from e
    return engine


def listar_tablas(engine: Engine) -> list[str]:
    return sorted(inspect(engine).get_table_names())


def _posicion(fila, clave: list[str], numero: int) -> str:
    """Cómo encontrar la fila: por su llave primaria si tiene, si no por su número."""
    if clave:
        return "fila " + ", ".join(f"{k}={fila[k]}" for k in clave)
    return f"fila {numero}"


def escanear_bd(engine: Engine, descripcion: str, max_filas: int = 1000,
                tablas: list[str] | None = None, validators: list[Validator] | None = None) -> ResultadoEscaneo:
    """Pasa cada celda por los validadores, usando el nombre de su columna como contexto."""
    resultado = ResultadoEscaneo("bd", descripcion)
    validators = validators if validators is not None else default_validators()
    disponibles = listar_tablas(engine)
    for nombre in tablas or disponibles:
        if nombre not in disponibles:
            resultado.errores.append(f"La tabla {nombre} no existe")
            continue
        try:
            tabla = Table(nombre, MetaData(), autoload_with=engine)
            clave = [c.name for c in tabla.primary_key.columns]
            with engine.connect() as conn:
                filas = conn.execute(select(tabla).limit(max_filas)).mappings()
                escanear_filas(resultado, nombre,
                               ((_posicion(f, clave, n), f) for n, f in enumerate(filas, start=1)), validators)
        except Exception as e:  # una tabla rara (permisos, tipos exóticos) no detiene el resto
            resultado.errores.append(f"{nombre}: {str(e).splitlines()[0][:200]}")
    return resultado
