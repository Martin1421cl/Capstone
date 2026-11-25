"""Escaneo celda por celda, común a bases de datos y planillas."""

from collections.abc import Iterable, Mapping
from datetime import date, datetime, time

from ksecure.core.models import Match
from ksecure.escaneo.resultado import Hallazgo, ResultadoEscaneo
from ksecure.validators.base import Validator

# Valores repetidos en una misma columna (estados, comunas, fechas, montos...) se validan una sola vez.
# Solo valores cortos y hasta un tope de entradas, para no gastar memoria en tablas enormes.
_CACHE_LARGO = 256
_CACHE_MAX = 50_000
_SIN_DIGITOS = str.maketrans("", "", "0123456789")
# Fechas, horas y sí/no que vienen como tipo propio de la base: ningún validador busca datos ahí.
_NO_SE_REVISAN = (bytes, bytearray, memoryview, date, datetime, time, bool)


def _validar(texto: str, fuente: str, columna: str, validators: list[Validator]) -> list[Match]:
    """Pasa el texto por los validadores, saltando los que no pueden encontrar nada ahí."""
    if texto.isascii():  # el filtro cuenta dígitos 0-9; con otros alfabetos se revisa todo
        digitos = len(texto) - len(texto.translate(_SIN_DIGITOS))
        validators = [v for v in validators if v.puede_estar_en(texto, digitos)]
    return [m for v in validators for m in v.validate_content(texto, fuente, context_hint=columna)]


def escanear_filas(resultado: ResultadoEscaneo, fuente: str, filas: Iterable[tuple[str, Mapping]],
                   validators: list[Validator]) -> int:
    """filas: pares (posición legible, {columna: valor}). Devuelve cuántas filas revisó.

    El nombre de la columna se usa como contexto: así "H14510" no dice nada,
    pero "rut_comprador" sube la confianza de lo que contiene.
    """
    vistos: dict[tuple[str, str], list[Match]] = {}
    n = 0
    for n, (posicion, fila) in enumerate(filas, start=1):
        for columna, valor in fila.items():
            if valor is None or isinstance(valor, _NO_SE_REVISAN):
                continue
            texto = str(valor).strip()
            if not texto:
                continue
            clave = (columna, texto)
            encontrados = vistos.get(clave)
            if encontrados is None:
                # El resultado depende solo del texto y de la columna: se puede reutilizar tal cual.
                encontrados = _validar(texto, fuente, columna, validators)
                if len(texto) <= _CACHE_LARGO:
                    if len(vistos) >= _CACHE_MAX:
                        vistos.clear()
                    vistos[clave] = encontrados
            for m in encontrados:
                resultado.agregar(Hallazgo(m, fuente, posicion, columna, n))
    resultado.filas_por_fuente[fuente] = n
    return n
