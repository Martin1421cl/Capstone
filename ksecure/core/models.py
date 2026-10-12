"""Modelos compartidos por todo K-Secure.

Equivalen a internal/detector de ferret-scan (Match, ContextInfo) y a sus
bandas de confianza (formatters/shared: HIGH >= 90, MEDIUM >= 60, LOW < 60).
RiskLevel es propio de K-Secure: la clasificación de la Política de Duoc UC
y el whitepaper OEA/AWS.
"""

from dataclasses import dataclass, field
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 90:
            return cls.HIGH
        if score >= 60:
            return cls.MEDIUM
        return cls.LOW


class RiskLevel(str, Enum):
    PUBLICO = "Público"
    INTERNO = "Interno"
    CONFIDENCIAL = "Confidencial"
    RESTRINGIDO = "Restringido"


@dataclass
class ContextInfo:
    """Texto alrededor de una coincidencia y su efecto en la confianza."""

    before_text: str = ""
    after_text: str = ""
    full_line: str = ""
    positive_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    confidence_impact: float = 0.0


@dataclass
class Match:
    """Un dato sensible encontrado por un validador."""

    text: str
    type: str
    confidence: float  # 0-100, como en ferret-scan
    risk_level: RiskLevel
    line_number: int
    filename: str
    validator: str
    context: ContextInfo
    # Columnas 1-based dentro de la línea, fin exclusivo; 0 = sin posición.
    start_column: int = 0
    end_column: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        return ConfidenceLevel.from_score(self.confidence)
