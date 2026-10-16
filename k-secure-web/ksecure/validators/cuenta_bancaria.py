"""Validador de cuentas bancarias chilenas (equivalente al validador bankaccount de ferret-scan).

En Chile cada banco usa su propio formato (7 a 14 dígitos, a veces con guiones)
y no hay dígito verificador común, así que solo se reporta un número si cerca
aparece una palabra bancaria ("cuenta corriente", "BancoEstado", ...).
La Cuenta RUT de BancoEstado es el RUT sin dígito verificador.
"""

import re

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import Candidate, Validator

_CUENTA_PATTERN = re.compile(r"(?<![\w.,$-])\d[\d-]{5,18}\d(?![\w.,]|-\w)")

_FORMA_DE_RUT = re.compile(r"\d{7,8}-\d")
_FORMA_DE_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4}")


class CuentaBancariaValidator(Validator):
    name = "CUENTA_BANCARIA"
    requires_context = True
    positive_keywords = (
        "cuenta", "cta", "cte", "corriente", "vista", "ahorro", "cuenta rut", "chequera electronica",
        "banco", "bancoestado", "santander", "bci", "scotiabank", "itau", "security", "falabella",
        "ripley", "bice", "consorcio", "internacional", "transferencia", "deposito", "abono",
    )
    negative_keywords = (
        "monto", "total", "pesos", "clp", "valor", "precio", "saldo", "folio", "factura",
        "boleta", "telefono", "celular",
    )

    def find_candidates(self, line):
        for m in _CUENTA_PATTERN.finditer(line):
            raw = m.group(0)
            digitos = raw.replace("-", "")
            if not 7 <= len(digitos) <= 14 or "--" in raw:
                continue
            if _FORMA_DE_RUT.fullmatch(raw) or _FORMA_DE_FECHA.fullmatch(raw):
                continue
            yield Candidate(m.start(), m.end(), 55, {"numero": digitos})

    def risk_level(self, confidence, metadata):
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW:
            return RiskLevel.INTERNO
        return RiskLevel.RESTRINGIDO
