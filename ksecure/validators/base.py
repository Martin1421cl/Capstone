"""Clase base de los validadores, equivalente a detector.Validator de ferret-scan.

Cada validador dice qué busca en una línea (find_candidates) y qué riesgo
tiene (risk_level). La base recorre el texto, ajusta la confianza según las
palabras clave cercanas y arma cada Match.
"""

import re
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field

from ksecure.core.models import ContextInfo, Match, RiskLevel

# Ajuste por palabras clave: +10 por cada positiva (máx +20), -20 por cada negativa (máx -40).
_POSITIVO, _POSITIVO_MAX = 10, 20
_NEGATIVO, _NEGATIVO_MAX = 20, 40


def normalize(text: str) -> str:
    """Minúsculas y sin tildes, para que "cédula" y "cedula" sean lo mismo."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def find_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    """Palabras clave presentes en text como palabra completa ("rut" no calza en "Ruta")."""
    norm = normalize(text)
    return [kw for kw in keywords if re.search(rf"(?<!\w){re.escape(normalize(kw))}(?!\w)", norm)]


@dataclass
class Candidate:
    """Una coincidencia dentro de una línea, antes de aplicar el contexto."""

    start: int
    end: int
    confidence: float
    metadata: dict = field(default_factory=dict)


class Validator(ABC):
    name: str = ""
    positive_keywords: tuple[str, ...] = ()
    negative_keywords: tuple[str, ...] = ()
    # Caracteres a cada lado de la coincidencia que cuentan como contexto.
    context_window: int = 50
    # Para datos sin formato propio (ej. cuentas bancarias): sin palabra clave positiva no se reporta.
    requires_context: bool = False

    @abstractmethod
    def find_candidates(self, line: str) -> Iterable[Candidate]:
        """Coincidencias en una línea, con su confianza 0-100 sin contexto."""

    @abstractmethod
    def risk_level(self, confidence: float, metadata: dict) -> RiskLevel:
        """Clasificación de riesgo según la confianza final."""

    def validate_content(self, content: str, filename: str) -> list[Match]:
        matches = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            for c in self.find_candidates(line):
                context = self.extract_context(line, c.start, c.end)
                if self.requires_context and not context.positive_keywords:
                    continue
                context.confidence_impact = (
                    min(_POSITIVO * len(context.positive_keywords), _POSITIVO_MAX)
                    - min(_NEGATIVO * len(context.negative_keywords), _NEGATIVO_MAX)
                )
                confidence = max(0.0, min(100.0, c.confidence + context.confidence_impact))
                matches.append(Match(
                    text=line[c.start:c.end],
                    type=self.name,
                    confidence=confidence,
                    risk_level=self.risk_level(confidence, c.metadata),
                    line_number=line_number,
                    filename=filename,
                    validator=self.name,
                    context=context,
                    start_column=c.start + 1,
                    end_column=c.end + 1,
                    metadata=c.metadata,
                ))
        return matches

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
