import re
from ksecure.validators.base import BaseValidator
from ksecure.models import DataType, RiskLevel, Confidence

class CreditCardValidator(BaseValidator):
    def __init__(self, custom_whitelist=None):
        # Tarjetas clásicas de prueba de pasarelas de pago (Stripe, Transbank, etc.)
        default_whitelist = ["4242424242424242", "4000000000000000"]
        whitelist = custom_whitelist if custom_whitelist is not None else default_whitelist

        super().__init__(
            name=DataType.TARJETA_CREDITO,
            # Regex que detecta formatos de 16 dígitos (Visa/Mastercard) permitiendo espacios o guiones
            pattern=r"\b(?:\d[ -]*?){13,16}\b",
            risk_level=RiskLevel.RESTRINGIDO,
            confidence=Confidence.ALTA,
            score=0.95,
            whitelist=whitelist
        )

    def mask(self, value: str) -> str:
        """Enmascara los últimos 12 dígitos, dejando visibles solo los primeros 4."""
        clean_val = self.normalize(value)
        if len(clean_val) >= 4:
            return clean_val[:4] + "-****-****-****"
        return "****-****-****-****"

    def normalize(self, value: str) -> str:
        """Limpia espacios y guiones para guardar el dato puro."""
        return value.replace(" ", "").replace("-", "").strip()