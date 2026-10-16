"""Validador de secretos y credenciales (equivalente al validador secrets de ferret-scan)."""

import re

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import Candidate, Validator

# (tipo, patrón, confianza). Si el patrón tiene un grupo, el secreto es solo ese grupo.
_PATRONES = [
    ("AWS_ACCESS_KEY", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}(?![A-Z0-9])"), 95),
    ("AWS_SECRET_KEY", re.compile(
        r"(?i:aws_?secret_?access_?key|secret_?access_?key)\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{40})(?![A-Za-z0-9/+=])"), 95),
    ("GITHUB_TOKEN", re.compile(r"(?<!\w)gh[pousr]_[A-Za-z0-9]{36}(?!\w)"), 95),
    ("LLAVE_PRIVADA", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"), 100),
]


class SecretoValidator(Validator):
    name = "SECRETO"

    def find_candidates(self, line):
        for tipo, patron, confianza in _PATRONES:
            for m in patron.finditer(line):
                grupo = 1 if patron.groups else 0
                # La documentación de AWS usa claves que terminan en EXAMPLE.
                de_ejemplo = "EXAMPLE" in m.group(grupo)
                yield Candidate(m.start(grupo), m.end(grupo), confianza - (50 if de_ejemplo else 0), {
                    "tipo_secreto": tipo,
                    "secreto_de_ejemplo": de_ejemplo,
                })

    def mask(self, text, metadata):
        """Solo los primeros 4 caracteres, que dicen qué tipo de clave es (AKIA, ghp_...)."""
        return text[:4] + "*" * 8

    def risk_level(self, confidence, metadata):
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW:
            return RiskLevel.CONFIDENCIAL
        return RiskLevel.RESTRINGIDO
