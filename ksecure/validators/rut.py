"""Validador de RUT chileno, el equivalente chileno del validador SSN de ferret-scan.

1. Patrón: 12.345.678-5, 12345678-5, 1.234.567-K (guion obligatorio).
2. Dígito verificador con Módulo 11.
3. Confianza por formato, RUT de ejemplo y palabras clave cercanas.
"""

import itertools
import re

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import Candidate, Validator

# Word suele autocorregir "-" a "–", así que se aceptan ambos guiones.
_RUT_PATTERN = re.compile(r"(?<![\d.\-‐–])(\d{1,2}(?:\.\d{3}){2}|\d{1,3}\.\d{3}|\d{1,8})\s?[-‐–]\s?([0-9kK])(?!\w)")

# Bajo 1 millón también hay RUT (antiguos o internos, ej. "2004-4"), pero "número-guion-dígito"
# es demasiado común: solo se reportan si alrededor se habla de RUT (o la columna se llama rut_...).
_RUT_LARGO_DESDE = 1_000_000

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
        "rol unico tributario", "comprador", "vendedor", "proveedor", "usuario", "socio",
    )
    negative_keywords = (
        "factura", "folio", "boleta", "guia", "ticket", "orden de compra", "pedido",
        "telefono", "codigo postal", "serie",
    )

    def find_candidates(self, line):
        for m in _RUT_PATTERN.finditer(line):
            cuerpo, dv = m.group(1).replace(".", ""), m.group(2).upper()
            if int(cuerpo) == 0:
                continue
            corto = int(cuerpo) < _RUT_LARGO_DESDE
            confidence, checks = self.calculate_confidence(m.group(0), cuerpo, dv)
            if corto:
                confidence = min(confidence, 35)  # +20 máx. de contexto: queda en LOW, puede ser cualquier código
            yield Candidate(m.start(), m.end(), confidence, {
                "rut_normalizado": f"{cuerpo}-{dv}",
                "persona_juridica": int(cuerpo) >= _EMPRESA_DESDE,
                "rut_corto": corto,
                "checks": checks,
            }, requires_context=corto)

    def calculate_confidence(self, rut_text: str, cuerpo: str, dv: str) -> tuple[float, dict[str, bool]]:
        """Confianza 0-100 sin contexto, y los chequeos que la explican."""
        checks = {
            "formato_con_puntos": "." in rut_text,
            "dv_valido": calcular_dv(int(cuerpo)) == dv,
            "rut_de_ejemplo": es_rut_de_ejemplo(cuerpo),
        }
        confidence = 90 if checks["formato_con_puntos"] else 75
        if not checks["dv_valido"]:
            confidence -= 40
        if checks["rut_de_ejemplo"]:
            confidence -= 40
        return confidence, checks

    def mask(self, text, metadata):
        """Solo los últimos 3 dígitos y el DV: **.***.678-5."""
        cuerpo, dv = metadata["rut_normalizado"].split("-")
        return f"**.***.{cuerpo[-3:]}-{dv}"

    def risk_level(self, confidence, metadata):
        # El RUT de una empresa sale en cada factura: no identifica a una persona.
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW or metadata["persona_juridica"]:
            return RiskLevel.INTERNO
        return RiskLevel.RESTRINGIDO
