"""Validador de RUT chileno, el equivalente chileno del validador SSN de ferret-scan.

1. Patrón: 12.345.678-5, 12345678-5, 1.234.567-K (guion obligatorio).
2. Dígito verificador con Módulo 11.
3. Confianza por formato, RUT de ejemplo y palabras clave cercanas.
"""

import itertools
import re

from ksecure.core.models import ConfidenceLevel, Match, RiskLevel
from ksecure.validators.base import Validator

# Word suele autocorregir "-" a "–", así que se aceptan ambos guiones.
_RUT_PATTERN = re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d{3}){2}|\d{7,8})\s?[-‐–]\s?([0-9kK])(?!\w)")

# Desde 50 millones se asignan a personas jurídicas (empresas).
_EMPRESA_DESDE = 50_000_000

# RUT que aparecen en ejemplos y formularios de prueba.
_RUT_DE_EJEMPLO = {"12345678", "1234567", "87654321", "7654321"}


def calcular_dv(cuerpo: int) -> str:
    """Dígito verificador del RUT (Módulo 11)."""
    factores = itertools.cycle([2, 3, 4, 5, 6, 7])
    suma = sum(int(d) * f for d, f in zip(reversed(str(cuerpo)), factores))
    resto = 11 - suma % 11
    return {11: "0", 10: "K"}.get(resto, str(resto))


def es_rut_de_ejemplo(cuerpo: str) -> bool:
    return cuerpo in _RUT_DE_EJEMPLO or len(set(cuerpo)) == 1


class RutValidator(Validator):
    name = "RUT"
    positive_keywords = (
        "rut", "run", "cedula", "identidad", "identificacion", "cliente", "paciente",
        "titular", "contribuyente", "empleado", "trabajador", "alumno", "beneficiario",
        "rol unico tributario",
    )
    negative_keywords = (
        "factura", "folio", "boleta", "guia", "ticket", "orden de compra", "pedido",
        "telefono", "codigo postal", "serie",
    )

    def validate_content(self, content: str, filename: str) -> list[Match]:
        matches = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            for m in _RUT_PATTERN.finditer(line):
                cuerpo = m.group(1).replace(".", "")
                if int(cuerpo) < 1_000_000:
                    continue
                matches.append(self._build_match(m, line, line_number, filename, cuerpo))
        return matches

    def calculate_confidence(self, rut_text: str, cuerpo: str, dv: str) -> tuple[float, dict[str, bool]]:
        """Confianza 0-100 sin contexto, y los chequeos que la explican."""
        checks = {
            "formato_con_puntos": "." in rut_text,
            "dv_valido": calcular_dv(int(cuerpo)) == dv.upper(),
            "rut_de_ejemplo": es_rut_de_ejemplo(cuerpo),
        }
        confidence = 90 if checks["formato_con_puntos"] else 75
        if not checks["dv_valido"]:
            confidence -= 40
        if checks["rut_de_ejemplo"]:
            confidence -= 40
        return confidence, checks

    def _build_match(self, m: re.Match, line: str, line_number: int, filename: str, cuerpo: str) -> Match:
        confidence, checks = self.calculate_confidence(m.group(0), cuerpo, m.group(2))

        context = self.extract_context(line, m.start(), m.end())
        context.confidence_impact = (
            min(10 * len(context.positive_keywords), 20)
            - min(20 * len(context.negative_keywords), 40)
        )
        confidence = max(0.0, min(100.0, confidence + context.confidence_impact))

        es_empresa = int(cuerpo) >= _EMPRESA_DESDE
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW or es_empresa:
            # El RUT de una empresa sale en cada factura: no identifica a una persona.
            risk = RiskLevel.INTERNO
        else:
            risk = RiskLevel.RESTRINGIDO

        return Match(
            text=m.group(0),
            type="RUT",
            confidence=confidence,
            risk_level=risk,
            line_number=line_number,
            filename=filename,
            validator=self.name,
            context=context,
            start_column=m.start() + 1,
            end_column=m.end() + 1,
            metadata={
                "rut_normalizado": f"{cuerpo}-{m.group(2).upper()}",
                "persona_juridica": es_empresa,
                "checks": checks,
            },
        )
