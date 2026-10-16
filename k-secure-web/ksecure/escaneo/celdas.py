"""Escaneo celda por celda, común a bases de datos y planillas."""

from collections.abc import Iterable, Mapping

from ksecure.escaneo.resultado import Hallazgo, ResultadoEscaneo
from ksecure.validators.base import Validator


def escanear_filas(resultado: ResultadoEscaneo, fuente: str, filas: Iterable[tuple[str, Mapping]],
                   validators: list[Validator]) -> int:
    """filas: pares (posición legible, {columna: valor}). Devuelve cuántas filas revisó.

    El nombre de la columna se usa como contexto: así "H14510" no dice nada,
    pero "rut_comprador" sube la confianza de lo que contiene.
    """
    n = 0
    for n, (posicion, fila) in enumerate(filas, start=1):
        for columna, valor in fila.items():
            if valor is None or isinstance(valor, (bytes, bytearray, memoryview)):
                continue
            texto = str(valor).strip()
            if not texto:
                continue
            for v in validators:
                for m in v.validate_content(texto, fuente, context_hint=columna):
                    resultado.hallazgos.append(Hallazgo(m, fuente, posicion, columna, n))
    resultado.filas_por_fuente[fuente] = n
    return n
