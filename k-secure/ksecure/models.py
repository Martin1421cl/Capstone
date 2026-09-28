"""Modelos de datos compartidos por todo el motor K-Secure."""

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    """Niveles de clasificación de riesgo/criticidad.

    Basado en el whitepaper OEA/AWS de Clasificación de Datos y en la
    Política de Clasificación de Datos e Información de Duoc UC:
    Público, Interno, Confidencial, Restringido.
    """

    PUBLICO = "Público"
    INTERNO = "Interno"
    CONFIDENCIAL = "Confidencial"
    RESTRINGIDO = "Restringido"


class DataType(str, Enum):
    """Tipos de dato sensible que K-Secure es capaz de detectar."""

    RUT = "RUT"
    TELEFONO_MOVIL = "Teléfono móvil (+56 9)"
    CORREO_ELECTRONICO = "Correo Electrónico"
    AWS_ACCESS_KEY = "AWS Access Key"


class Confidence(str, Enum):
    """Nivel de confianza de una detección individual."""

    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"


@dataclass
class Finding:
    """Una coincidencia detectada por un validador dentro de una fuente
    de datos (columna de BD, archivo, celda, etc.)."""

    data_type: DataType
    raw_value: str
    normalized_value: str
    is_valid: bool
    confidence: Confidence
    confidence_score: float  # 0.0 - 1.0, para trazabilidad/depuración
    risk_level: RiskLevel
    source: str  # ej: "tabla.columna" o "archivo.csv:fila 12"
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tipo_dato": self.data_type.value,
            "valor_detectado": self.raw_value,
            "valor_normalizado": self.normalized_value,
            "formato_valido": self.is_valid,
            "confianza": self.confidence.value,
            "score_confianza": round(self.confidence_score, 2),
            "nivel_riesgo": self.risk_level.value,
            "origen": self.source,
            "motivos": "; ".join(self.reasons),
        }
