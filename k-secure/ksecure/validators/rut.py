"""Validador de RUT (Rol Único Tributario) chileno.

Combina dos capas, tal como se definió en el Informe de Fase 1:

1. Expresión regular que reconoce los formatos habituales de escritura
   de un RUT (con o sin puntos de miles, con guion antes del dígito
   verificador). Se ajustó para soportar RUTs atípicos y cortos (1 a 8 dígitos).
2. Validación matemática del dígito verificador mediante el algoritmo
   Módulo 11 (Pendiente de implementación en esta fase).
"""

import re
from ksecure.validators.base import BaseValidator
from ksecure.models import DataType, RiskLevel, Confidence

class RutValidator(BaseValidator):
    def __init__(self, custom_whitelist=None):
        default_whitelist = ["11.111.111-1", "12.345.678-5", "1-9"]
        whitelist = custom_whitelist if custom_whitelist is not None else default_whitelist

        super().__init__(
            name=DataType.RUT,
            pattern=r"\b\d{1,8}\.?\d{3}\.?\d{3}-[\dkK]\b|\b\d{1,8}-[\dkK]\b",
            risk_level=RiskLevel.RESTRINGIDO,
            confidence=Confidence.ALTA,
            score=0.85,
            whitelist=whitelist
        )

    def mask(self, value: str) -> str:
        """Enmascara el RUT tapando al menos 5 dígitos del cuerpo."""
        parts = value.split("-")
        if len(parts) == 2:
            cuerpo = parts[0].replace(".", "")
            dv = parts[1]
            # Si el cuerpo es largo, reemplazamos los primeros 5 dígitos por asteriscos
            if len(cuerpo) >= 5:
                cuerpo_mascara = "*****" + cuerpo[5:]
            else:
                cuerpo_mascara = "*****"
            return f"{cuerpo_mascara}-{dv}"
        return "*****"

    def normalize(self, value: str) -> str:
        """Limpia el RUT para facilitar comparaciones y almacenamiento."""
        return value.replace(".", "").replace("-", "").upper()