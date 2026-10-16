"""Validador de teléfonos chilenos (equivalente al validador phone de ferret-scan).

Desde 2016 todos los números chilenos tienen 9 dígitos:
- Móvil: 9 XXXX XXXX
- Fijo Santiago: 2 2XXX XXXX
- Fijo regiones: código de área de 2 dígitos + 7 dígitos (ej. 41 223 4567)
Prefijo de país opcional: +56, 56 o (+56).
"""

import re

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import Candidate, Validator

_S = r"[\s-]?"
_PREFIJO = r"(?:\(?\+?56\)?" + _S + ")?"
_MOVIL = rf"\(?9\)?{_S}\d{{4}}{_S}\d{{4}}|9\d{{2}}[\s-]\d{{3}}[\s-]\d{{3}}"
_AREAS = r"3[2-5]|4[1-5]|5[1-8]|6[1-7]|7[1-5]"
_FIJO = rf"\(?2\)?{_S}\d{{4}}{_S}\d{{4}}|22{_S}\d{{3}}{_S}\d{{4}}|\(?(?:{_AREAS})\)?{_S}\d{{3}}{_S}\d{{4}}"
_TELEFONO_PATTERN = re.compile(rf"(?<![\w+.-])({_PREFIJO})({_MOVIL}|{_FIJO})(?!\w|[.-]\d)")

_NUMEROS_DE_EJEMPLO = {"912345678", "987654321", "123456789", "223456789"}


def formatear(digitos: str) -> str:
    """Formato estándar: +56 9 1234 5678 / +56 2 2345 6789 / +56 41 223 4567."""
    if digitos[0] in "92":
        return f"+56 {digitos[0]} {digitos[1:5]} {digitos[5:]}"
    return f"+56 {digitos[:2]} {digitos[2:5]} {digitos[5:]}"


class TelefonoValidator(Validator):
    name = "TELEFONO"
    positive_keywords = (
        "telefono", "fono", "tel", "celular", "cel", "movil", "whatsapp", "contacto",
        "llamar", "numero de contacto",
    )
    negative_keywords = (
        "rut", "folio", "factura", "boleta", "monto", "total", "precio", "pedido",
        "orden", "codigo", "serie",
    )

    def find_candidates(self, line):
        for m in _TELEFONO_PATTERN.finditer(line):
            digitos = re.sub(r"\D", "", m.group(2))
            movil = digitos[0] == "9"
            confidence = 70 if movil else 60
            if m.group(1):
                confidence += 15
            if digitos in _NUMEROS_DE_EJEMPLO or len(set(digitos[1:])) == 1:
                confidence -= 40
            yield Candidate(m.start(), m.end(), confidence, {
                "tipo": "movil" if movil else "fijo",
                "numero_normalizado": formatear(digitos),
                "con_prefijo_pais": bool(m.group(1)),
            })

    def mask(self, text, metadata):
        """+56 9 **** 4870: se ve el tipo y los últimos 4 dígitos."""
        pais, area, *_, final = metadata["numero_normalizado"].split()
        return f"{pais} {area} **** {final}"

    def risk_level(self, confidence, metadata):
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW:
            return RiskLevel.INTERNO
        # Un celular es de una persona; un fijo suele ser de una empresa u oficina.
        return RiskLevel.CONFIDENCIAL if metadata["tipo"] == "movil" else RiskLevel.INTERNO
