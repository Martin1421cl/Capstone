"""Validador de correos electrónicos (equivalente al validador email de ferret-scan)."""

import re

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import Candidate, Validator

_EMAIL_PATTERN = re.compile(r"(?<![\w.+-])([\w.%+-]+)@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,24})(?![\w-])")

_DOMINIOS_DE_EJEMPLO = re.compile(r"(^|\.)(example|ejemplo|test|prueba|dominio|localhost)\.")

# Casillas de un área, no de una persona: contacto@empresa.cl se publica en la web.
_CUENTAS_DE_ROL = {
    "contacto", "info", "informaciones", "ventas", "soporte", "ayuda", "admin", "administracion",
    "noreply", "no-reply", "notificaciones", "rrhh", "hola", "atencion", "clientes", "prensa",
    "facturacion", "cobranza", "postulaciones",
}


class EmailValidator(Validator):
    name = "EMAIL"
    positive_keywords = ("correo", "email", "e-mail", "mail", "contacto", "escribir a")

    def find_candidates(self, line):
        for m in _EMAIL_PATTERN.finditer(line):
            usuario, dominio = m.group(1).lower(), m.group(2).lower()
            de_ejemplo = bool(_DOMINIOS_DE_EJEMPLO.search(dominio + "."))
            yield Candidate(m.start(), m.end(), 90 - (50 if de_ejemplo else 0), {
                "dominio": dominio,
                "cuenta_de_rol": usuario in _CUENTAS_DE_ROL,
                "dominio_de_ejemplo": de_ejemplo,
            })

    def risk_level(self, confidence, metadata):
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW:
            return RiskLevel.INTERNO
        return RiskLevel.PUBLICO if metadata["cuenta_de_rol"] else RiskLevel.CONFIDENCIAL
