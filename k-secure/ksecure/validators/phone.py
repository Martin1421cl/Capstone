import re
from ksecure.validators.base import BaseValidator
from ksecure.models import DataType, RiskLevel, Confidence

class PhoneValidator(BaseValidator):
    def __init__(self, custom_whitelist=None):
        default_whitelist = ["+56900000000"]
        whitelist = custom_whitelist if custom_whitelist is not None else default_whitelist

        super().__init__(
            name=DataType.TELEFONO_MOVIL,
            pattern=r"\+?56\s?9\s?\d{4}\s?\d{4}\b|\b9\d{8}\b",
            risk_level=RiskLevel.CONFIDENCIAL,
            confidence=Confidence.MEDIA,
            score=0.75,
            whitelist=whitelist
        )

    def mask(self, value: str) -> str:
        """Oculta los números centrales del teléfono."""
        clean_val = value.replace(" ", "")
        if len(clean_val) > 8:
            return clean_val[:4] + "****" + clean_val[-4:]
        return "****"

    def normalize(self, value: str) -> str:
        """Limpia los espacios del teléfono para estandarizar el formato."""
        return value.replace(" ", "")