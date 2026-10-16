"""Resultado de un escaneo, antes de guardarlo. Es igual para archivos y bases de datos."""

from dataclasses import dataclass, field

from ksecure.core.models import Match


@dataclass
class Hallazgo:
    """Un dato sensible y dónde está.

    fuente:   el archivo o la tabla.
    columna:  la columna (solo en bases de datos).
    posicion: "línea 12" en un archivo, "fila id=5" en una tabla.
    numero:   la misma línea o fila como número.
    """

    match: Match
    fuente: str
    posicion: str
    columna: str | None = None
    numero: int = 0


@dataclass
class ResultadoEscaneo:
    origen_tipo: str            # "archivo" o "bd"
    origen_nombre: str          # "informe.docx" o "PostgreSQL · ventas@db.ejemplo.cl"
    hallazgos: list[Hallazgo] = field(default_factory=list)
    # Filas revisadas por tabla, para calcular qué % de una columna es sensible.
    filas_por_fuente: dict[str, int] = field(default_factory=dict)
    errores: list[str] = field(default_factory=list)
