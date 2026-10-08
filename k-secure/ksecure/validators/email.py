import re
from ksecure.validators.base import BaseValidator
from ksecure.models import DataType, RiskLevel, Confidence

class EmailValidator(BaseValidator):
    def __init__(self, custom_whitelist=None):
        # Ejemplos documentados que no representan un riesgo real
        default_whitelist = ["test@example.com", "usuario@prueba.cl", "ejemplo@duoc.cl"]
        whitelist = custom_whitelist if custom_whitelist is not None else default_whitelist

        super().__init__(
            name=DataType.CORREO_ELECTRONICO,
            pattern=r"\b[A-Za-z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", 
            risk_level=RiskLevel.INTERNO,
            confidence=Confidence.ALTA,
            score=0.90,
            whitelist=whitelist
        )
        # Re-compilamos la regex con el flag IGNORECASE para mayor robustez
        self.pattern = re.compile(self.pattern.pattern, re.IGNORECASE)

    def mask(self, value: str) -> str:
        """Oculta el nombre de usuario, dejando visible la primera letra y el dominio."""
        partes = value.split('@')
        usuario = partes[0]
        dominio = partes[1]
        
        if len(usuario) > 2:
            usuario_enmascarado = usuario[:2] + "****"
        else:
            usuario_enmascarado = "****"
            
        return f"{usuario_enmascarado}@{dominio}"

    def normalize(self, value: str) -> str:
        """Pasa todo a minúsculas para estandarizar."""
        return value.strip().lower()