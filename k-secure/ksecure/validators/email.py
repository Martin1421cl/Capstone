import re
from ksecure.models import Confidence, DataType, Finding, RiskLevel
from ksecure.validators.base import BaseValidator

_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")

class EmailValidator(BaseValidator):
    """Detecta direcciones de correo electrónico."""

    def find(self, text: str, source: str) -> list[Finding]:
        findings = []
        for match in _EMAIL_PATTERN.finditer(text):
            raw_value = match.group(0)
            
            findings.append(Finding(
                data_type=DataType.CORREO_ELECTRONICO,
                raw_value=raw_value,
                normalized_value=raw_value.lower(),
                is_valid=True,
                confidence=Confidence.ALTA,
                confidence_score=0.95,
                risk_level=RiskLevel.CONFIDENCIAL, 
                source=source,
                reasons=["Coincidencia con patrón estándar de Email RFC"]
            ))
            
        return findings

        