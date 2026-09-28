"""Validador de RUT (Rol Único Tributario) chileno.

Combina dos capas, tal como se definió en el Informe de Fase 1:

1. Expresión regular que reconoce los formatos habituales de escritura
   de un RUT (con o sin puntos de miles, con guion antes del dígito
   verificador).
2. Validación matemática del dígito verificador mediante el algoritmo
   Módulo 11, que reduce falsos positivos frente a un escaneo que solo
   usara el patrón (por ejemplo, un número de folio o de teléfono que
   "parece" un RUT pero cuyo dígito verificador no calza).

El scoring de confianza por contexto (palabras clave positivas/negativas
alrededor del match) sigue la misma idea que el validador de SSN de
FerretScan (AWS Labs), adaptada a vocabulario chileno.
"""

import itertools
import re

from ksecure.models import Confidence, DataType, Finding, RiskLevel
from ksecure.validators.base import BaseValidator

# Acepta: 12.345.678-9 | 12345678-9 | 1.234.567-K | 1234567-k
# El guion antes del DV es obligatorio para evitar capturar cualquier
# número de 7-8 dígitos como si fuera un RUT.
_RUT_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2}(?:\.\d{3}){2}|\d{7,8})\s?-\s?([0-9kK])(?!\d)"
)


def normalizar_rut(cuerpo: str, dv: str) -> str:
    """Quita puntos y arma el RUT normalizado "12345678-9"."""
    return f"{cuerpo.replace('.', '')}-{dv.upper()}"


def calcular_dv(cuerpo: int) -> str:
    """Calcula el dígito verificador de un RUT chileno (algoritmo Módulo 11)."""
    digitos_invertidos = [int(d) for d in reversed(str(cuerpo))]
    factores = itertools.cycle([2, 3, 4, 5, 6, 7])
    suma = sum(d * f for d, f in zip(digitos_invertidos, factores))
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


class RutValidator(BaseValidator):
    """Detecta RUTs chilenos y valida su dígito verificador."""

    POSITIVE_KEYWORDS = (
        "rut",
        "run",
        "cedula",
        "cédula",
        "identificacion",
        "identificación",
        "cliente",
        "paciente",
        "titular",
        "contribuyente",
        "empleado",
        "trabajador",
    )
    NEGATIVE_KEYWORDS = (
        "factura",
        "folio",
        "guia",
        "guía",
        "boleta",
        "telefono",
        "teléfono",
        "orden de compra",
        "ticket",
        "codigo postal",
        "código postal",
    )

    def find(self, content: str, source: str) -> list[Finding]:
        findings: list[Finding] = []

        for match in _RUT_PATTERN.finditer(content):
            cuerpo_str, dv_str = match.group(1), match.group(2)
            cuerpo_limpio = cuerpo_str.replace(".", "")
            cuerpo_num = int(cuerpo_limpio)

            # Descarta cuerpos fuera del rango plausible de RUT emitido en Chile.
            if not (1_000_000 <= cuerpo_num <= 99_999_999):
                continue

            dv_esperado = calcular_dv(cuerpo_num)
            dv_ingresado = dv_str.upper()
            es_valido = dv_esperado == dv_ingresado

            score = 0.55  # base: el formato calza con un RUT
            reasons = ["formato coincide con patrón de RUT"]

            if es_valido:
                score += 0.30
                reasons.append("dígito verificador válido (Módulo 11)")
            else:
                score -= 0.20
                reasons.append(
                    f"dígito verificador no coincide "
                    f"(esperado {dv_esperado}, encontrado {dv_ingresado})"
                )

            context = self._extract_context(content, match.start(), match.end())
            delta, kw_reasons = self._keyword_adjustment(context)
            score += delta
            reasons.extend(kw_reasons)

            score = max(0.0, min(1.0, score))
            confidence, risk = self._clasificar(score, es_valido)

            findings.append(
                Finding(
                    data_type=DataType.RUT,
                    raw_value=match.group(0),
                    normalized_value=normalizar_rut(cuerpo_str, dv_str),
                    is_valid=es_valido,
                    confidence=confidence,
                    confidence_score=score,
                    risk_level=risk,
                    source=source,
                    reasons=reasons,
                )
            )

        return findings

    @staticmethod
    def _clasificar(score: float, es_valido: bool) -> tuple[Confidence, RiskLevel]:
        if score >= 0.75:
            confidence = Confidence.ALTA
        elif score >= 0.5:
            confidence = Confidence.MEDIA
        else:
            confidence = Confidence.BAJA

        # El RUT identifica unívocamente a una persona natural en Chile:
        # con dígito verificador válido y confianza razonable, se clasifica
        # como Restringido (dato personal identificable). Si el DV no es
        # válido, se degrada porque probablemente no sea un RUT real.
        if es_valido and confidence in (Confidence.ALTA, Confidence.MEDIA):
            risk = RiskLevel.RESTRINGIDO
        elif es_valido:
            risk = RiskLevel.CONFIDENCIAL
        else:
            risk = RiskLevel.INTERNO

        return confidence, risk
