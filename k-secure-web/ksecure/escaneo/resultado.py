"""Resultado de un escaneo, antes de guardarlo. Es igual para archivos y bases de datos."""

from collections.abc import Callable
from dataclasses import dataclass, field

from ksecure.core.models import Match

LOTE = 2000  # HU-29: cada cuántos hallazgos se entregan a la base para no juntarlos todos en memoria


class ErrorAlGuardar(Exception):
    """Falló la base interna al guardar un lote: el escaneo se detiene (no es un error de una tabla del cliente)."""


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
    # HU-29: si se indica, recibe los hallazgos de a LOTE y la lista se vacía (se guardan en la base mientras
    # se escanea). Sin él, todos quedan en `hallazgos` (así lo usan las pruebas y el escaneo de un .db subido).
    al_lote: Callable[[list[Hallazgo]], None] | None = field(default=None, repr=False)
    total: int = 0              # hallazgos encontrados, incluidos los ya entregados a la base
    escaneo_id: int | None = None  # el id en la base interna, una vez guardado

    def agregar(self, hallazgo: Hallazgo):
        self.hallazgos.append(hallazgo)
        self.total += 1
        if self.al_lote is not None and len(self.hallazgos) >= LOTE:
            self.vaciar()

    def vaciar(self):
        """Entrega a la base lo que quede pendiente."""
        if self.al_lote is not None and self.hallazgos:
            self.al_lote(self.hallazgos)
            self.hallazgos = []
