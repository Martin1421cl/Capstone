"""Arma la expresión regular de una regla a partir de ejemplos del dato, para que nadie tenga que escribirla.

    ["F12345678"]             -> (?<![A-Za-z0-9])[A-Z]\\d{8}(?![A-Za-z0-9])    "1 letra + 8 números"
    ["FC-123456", "FC-9876543"] -> ...FC-\\d{6,7}...                            "«FC» + guion + 6 a 7 números"

Las letras que se repiten iguales en todos los ejemplos (con 2 o más) quedan fijas, como un prefijo.
"""

import re
from itertools import groupby

MAX_EJEMPLOS, MAX_LARGO = 10, 60
_BORDE_ANTES, _BORDE_DESPUES = r"(?<![A-Za-z0-9])", r"(?![A-Za-z0-9])"
_NOMBRES = {"-": "guion", ".": "punto", "/": "barra", "_": "guion bajo", ":": "dos puntos", "#": "#", "+": "+"}


def _clase(c: str) -> str:
    if c.isdigit():
        return "D"
    if c.isalpha():
        return "L"
    if c.isspace():
        return "S"
    return "O" + c  # un símbolo es parte de la forma: "FC-1" y "FC.1" no son el mismo formato


def _trozos(ejemplo: str) -> list[tuple[str, str]]:
    """'FC-123' -> [('L', 'FC'), ('O-', '-'), ('D', '123')]"""
    return [(k, "".join(g)) for k, g in groupby(ejemplo, key=_clase)]


def _cantidad(minimo: int, maximo: int) -> str:
    if minimo == maximo:
        return "" if minimo == 1 else f"{{{minimo}}}"
    return f"{{{minimo},{maximo}}}"


def _veces(minimo: int, maximo: int, singular: str, plural: str) -> str:
    if minimo == maximo:
        return f"{minimo} {singular if minimo == 1 else plural}"
    return f"{minimo} a {maximo} {plural}"


def _grupo(ejemplos: list[list[tuple[str, str]]]) -> tuple[str, str]:
    """Patrón y descripción para ejemplos que tienen la misma forma."""
    partes, texto = [], []
    for columna in zip(*ejemplos):
        clase = columna[0][0]
        valores = [v for _, v in columna]
        largos = [len(v) for v in valores]
        mn, mx = min(largos), max(largos)
        if clase == "D":
            partes.append(r"\d" + _cantidad(mn, mx))
            texto.append(_veces(mn, mx, "número", "números"))
        elif clase == "L":
            if len(ejemplos) >= 2 and len(set(valores)) == 1:
                partes.append(re.escape(valores[0]))
                texto.append(f"«{valores[0]}»")
            else:
                todas = "".join(valores)
                letras = "[A-Z]" if todas.isupper() else "[a-z]" if todas.islower() else "[A-Za-z]"
                partes.append(letras + _cantidad(mn, mx))
                texto.append(_veces(mn, mx, "letra", "letras"))
        elif clase == "S":
            partes.append(r"\s?")
            texto.append("espacio opcional")
        else:
            simbolo = clase[1]
            partes.append(re.escape(simbolo) + _cantidad(mn, mx))
            texto.append(_NOMBRES.get(simbolo, f"«{simbolo}»"))
    return "".join(partes), " + ".join(texto)


def generar_patron(ejemplos: list[str]) -> tuple[str, str]:
    """(expresión regular, descripción en palabras). Lanza ValueError si no hay ejemplos útiles."""
    limpios = [e.strip() for e in ejemplos if e and e.strip()][:MAX_EJEMPLOS]
    if not limpios:
        raise ValueError("Escribe al menos un ejemplo del dato")
    if any(len(e) > MAX_LARGO for e in limpios):
        raise ValueError(f"Cada ejemplo puede tener hasta {MAX_LARGO} caracteres")
    # Ejemplos con la misma forma (misma secuencia de letras/números/símbolos) se resumen juntos.
    formas: dict[tuple, list] = {}
    for e in limpios:
        trozos = _trozos(e)
        formas.setdefault(tuple(k for k, _ in trozos), []).append(trozos)
    grupos = [_grupo(g) for g in formas.values()]
    patron = grupos[0][0] if len(grupos) == 1 else "(?:" + "|".join(p for p, _ in grupos) + ")"
    return _BORDE_ANTES + patron + _BORDE_DESPUES, " o ".join(d for _, d in grupos)
