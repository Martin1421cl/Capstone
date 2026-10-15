"""Validador de patentes de vehículos chilenas (PPU). No existe en ferret-scan.

- Formato actual (desde 2007): 4 consonantes + 2 dígitos, ej. BB·CD·12 o BBCD12.
  Sin vocales ni M, N, Ñ, Q.
- Formato antiguo: 2 letras + 4 dígitos, ej. AB·12·34. Se confunde más con
  códigos, así que parte con menos confianza.
"""

import re

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import Candidate, Validator

_C = "[BCDFGHJKLPRSTVWXYZ]"
_S = r"[\s·.-]?"
_PATENTE_PATTERN = re.compile(
    rf"(?<![\w·.-])(?:(?P<nueva>{_C}{{2}}{_S}{_C}{{2}}{_S}\d{{2}})|(?P<antigua>[A-Z]{{2}}{_S}\d{{2}}{_S}\d{{2}}))(?!\w|[·.-]\w)"
)


class PatenteValidator(Validator):
    name = "PATENTE"
    positive_keywords = (
        "patente", "ppu", "placa", "vehiculo", "auto", "automovil", "camioneta", "moto",
        "permiso de circulacion", "revision tecnica", "multa", "tag", "estacionamiento",
    )
    negative_keywords = (
        "codigo", "sku", "modelo", "version", "iso", "ref", "norma", "articulo", "decreto",
    )

    def find_candidates(self, line):
        for m in _PATENTE_PATTERN.finditer(line):
            normalizada = re.sub(r"[\s·.-]", "", m.group(0))
            yield Candidate(m.start(), m.end(), 75 if m.group("nueva") else 45, {
                "formato": "nuevo" if m.group("nueva") else "antiguo",
                "patente_normalizada": f"{normalizada[:2]}·{normalizada[2:4]}·{normalizada[4:]}",
            })

    def mask(self, text, metadata):
        return "**·**·" + metadata["patente_normalizada"][-2:]

    def risk_level(self, confidence, metadata):
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW:
            return RiskLevel.INTERNO
        # Con la patente se obtiene el nombre y RUT del dueño en el Registro de Vehículos.
        return RiskLevel.CONFIDENCIAL
