from dataclasses import dataclass, field
from enum import Enum

class RiskLevel(str, Enum):
    PUBLICO = "Público"
    INTERNO = "Interno"
    CONFIDENCIAL = "Confidencial"
    RESTRINGIDO = "Restringido"

class DataType(str, Enum):
    RUT = "RUT"
    TELEFONO_MOVIL = "Teléfono móvil (+56 9)"
    CORREO_ELECTRONICO = "Correo Electrónico"
    AWS_ACCESS_KEY = "AWS Access Key"
    TARJETA_CREDITO = "Tarjeta de Crédito"

class Confidence(str, Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"

@dataclass
class Finding:
    data_type: DataType
    raw_value: str
    normalized_value: str
    is_valid: bool
    confidence: Confidence
    confidence_score: float
    risk_level: RiskLevel
    source: str
    masked_value: str = ""  # Agregado para compatibilidad con la base de datos
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tipo_dato": self.data_type.value,
            "valor_detectado": self.raw_value,
            "valor_normalizado": self.normalized_value,
            "valor_enmascarado": self.masked_value, # Agregado al diccionario
            "formato_valido": self.is_valid,
            "confianza": self.confidence.value,
            "score_confianza": round(self.confidence_score, 2),
            "nivel_riesgo": self.risk_level.value,
            "origen": self.source,
            "motivos": "; ".join(self.reasons),
        }