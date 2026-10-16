"""Validador armado desde parámetros: las reglas que se crean en la pantalla "Reglas", sin programar.

Una regla es un patrón (expresión regular) + una validación opcional (Módulo 11 o
Luhn, las mismas de los validadores de RUT y tarjeta) + palabras de contexto +
riesgo y confianza. Así se puede detectar un dato nuevo (pasaporte, ficha
clínica, N° de socio...) sin tocar el código.
"""

import re
from dataclasses import dataclass

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import Candidate, Validator, mask_keep_last
from ksecure.validators.rut import calcular_dv
from ksecure.validators.tarjeta import luhn


def _modulo11(texto: str) -> bool:
    """El último carácter es el dígito verificador del resto, como en el RUT."""
    limpio = re.sub(r"[^0-9kK]", "", texto).upper()
    return len(limpio) >= 2 and limpio[:-1].isdigit() and calcular_dv(int(limpio[:-1])) == limpio[-1]


def _luhn(texto: str) -> bool:
    digitos = re.sub(r"\D", "", texto)
    return len(digitos) >= 2 and luhn(digitos)


VALIDACIONES = {"ninguna": None, "modulo11": _modulo11, "luhn": _luhn}
PENALIDAD_VALIDACION = 40  # si no pasa la validación se reporta igual, pero con menos confianza


@dataclass(frozen=True)
class ParametrosRegla:
    nombre: str
    patron: str
    validacion: str = "ninguna"
    palabras_positivas: tuple[str, ...] = ()
    palabras_negativas: tuple[str, ...] = ()
    requiere_contexto: bool = False
    confianza: int = 70
    riesgo: RiskLevel = RiskLevel.CONFIDENCIAL
    visibles: int = 4  # caracteres que quedan a la vista al enmascarar


class ReglaValidator(Validator):
    def __init__(self, p: ParametrosRegla):
        if p.validacion not in VALIDACIONES:
            raise ValueError(f"Validación desconocida: {p.validacion}")
        self.p = p
        self.name = p.nombre
        self.positive_keywords = p.palabras_positivas
        self.negative_keywords = p.palabras_negativas
        self.requires_context = p.requiere_contexto
        self._patron = re.compile(p.patron)  # lanza re.error si el patrón está mal escrito
        self._validar = VALIDACIONES[p.validacion]

    def find_candidates(self, line):
        for m in self._patron.finditer(line):
            if not m.group(0):
                continue  # un patrón que calza vacío ("a*") no es un hallazgo
            valido = self._validar is None or self._validar(m.group(0))
            yield Candidate(m.start(), m.end(), self.p.confianza - (0 if valido else PENALIDAD_VALIDACION),
                            {"regla_personalizada": True, "validacion_ok": valido})

    def mask(self, text, metadata):
        return mask_keep_last(text, self.p.visibles)

    def risk_level(self, confidence, metadata):
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW:
            return RiskLevel.INTERNO
        return self.p.riesgo
