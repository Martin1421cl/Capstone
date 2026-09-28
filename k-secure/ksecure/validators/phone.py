"""Validador de números de teléfono móvil chileno (+56 9)."""

import re

from ksecure.models import Confidence, DataType, Finding, RiskLevel
from ksecure.validators.base import BaseValidator

# Acepta variantes: +56912345678 | +56 9 1234 5678 | 56912345678 |
# 912345678 | 9 1234 5678
_PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?56\s?)?9\s?(\d{4})\s?(\d{4})(?!\d)"
)


class PhoneValidator(BaseValidator):
    """Detecta números de celular chileno con formato +56 9 XXXX XXXX."""

    POSITIVE_KEYWORDS = (
        "telefono",
        "teléfono",
        "celular",
        "movil",
        "móvil",
        "contacto",
        "whatsapp",
        "cliente",
        "paciente",
    )
    NEGATIVE_KEYWORDS = (
        "rut",
        "factura",
        "folio",
        "monto",
        "precio",
        "codigo postal",
        "código postal",
    )

    def find(self, content: str, source: str) -> list[Finding]:
        findings: list[Finding] = []

        for match in _PHONE_PATTERN.finditer(content):
            numero = "9" + match.group(1) + match.group(2)
            raw = match.group(0)

            score = 0.5
            reasons = ["formato coincide con celular chileno (+56 9)"]

            if raw.strip().startswith("+56") or raw.strip().startswith("56"):
                score += 0.25
                reasons.append("incluye prefijo de país +56")

            context = self._extract_context(content, match.start(), match.end())
            delta, kw_reasons = self._keyword_adjustment(context)
            score += delta
            reasons.extend(kw_reasons)

            score = max(0.0, min(1.0, score))

            if score >= 0.75:
                confidence = Confidence.ALTA
                risk = RiskLevel.CONFIDENCIAL
            elif score >= 0.5:
                confidence = Confidence.MEDIA
                risk = RiskLevel.CONFIDENCIAL
            else:
                confidence = Confidence.BAJA
                risk = RiskLevel.INTERNO

            findings.append(
                Finding(
                    data_type=DataType.TELEFONO_MOVIL,
                    raw_value=raw,
                    normalized_value=f"+56 9 {numero[1:5]} {numero[5:]}",
                    is_valid=True,  # no existe DV que validar en telefonía
                    confidence=confidence,
                    confidence_score=score,
                    risk_level=risk,
                    source=source,
                    reasons=reasons,
                )
            )

        return findings
