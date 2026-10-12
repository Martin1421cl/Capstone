"""Clase base de los validadores, equivalente a detector.Validator de ferret-scan.

Cada validador implementa validate_content(). Esta base aporta el contexto
alrededor de cada coincidencia y la búsqueda de palabras clave.
"""

import re
import unicodedata
from abc import ABC, abstractmethod

from ksecure.core.models import ContextInfo, Match


def normalize(text: str) -> str:
    """Minúsculas y sin tildes, para que "cédula" y "cedula" sean lo mismo."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def find_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    """Palabras clave presentes en text como palabra completa ("rut" no calza en "Ruta")."""
    norm = normalize(text)
    return [kw for kw in keywords if re.search(rf"(?<!\w){re.escape(normalize(kw))}(?!\w)", norm)]


class Validator(ABC):
    name: str = ""
    positive_keywords: tuple[str, ...] = ()
    negative_keywords: tuple[str, ...] = ()
    # Caracteres a cada lado de la coincidencia que cuentan como contexto.
    context_window: int = 50

    @abstractmethod
    def validate_content(self, content: str, filename: str) -> list[Match]:
        """Busca datos sensibles en content y devuelve un Match por cada uno."""

    def extract_context(self, line: str, start: int, end: int) -> ContextInfo:
        before = line[max(0, start - self.context_window):start]
        after = line[end:end + self.context_window]
        nearby = before + " " + after
        return ContextInfo(
            before_text=before,
            after_text=after,
            full_line=line,
            positive_keywords=find_keywords(nearby, self.positive_keywords),
            negative_keywords=find_keywords(nearby, self.negative_keywords),
        )
