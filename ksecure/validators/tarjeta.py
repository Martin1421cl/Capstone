"""Validador de tarjetas de pago (equivalente al validador creditcard de ferret-scan).

1. 13 a 19 dígitos, contiguos o en grupos estándar (4-4-4-4, 4-6-5, ...).
2. Algoritmo de Luhn.
3. Rango IIN y largo válidos para la marca.
4. Tarjetas de prueba conocidas (incluidas las de Transbank/Webpay) bajan la confianza.
"""

import re

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import Candidate, Validator, find_keywords

_TARJETA_PATTERN = re.compile(r"(?<![\d.-])\d(?:[ -]?\d){12,18}(?![\d-])")

_AGRUPACIONES_VALIDAS = {(4, 4, 4, 4), (4, 6, 5), (4, 6, 4), (4, 4, 4, 4, 3)}

# (marca, prefijos, largos). Las más específicas primero.
_MARCAS = [
    ("Visa Electron", ("4026", "417500", "4405", "4508", "4844", "4913", "4917"), (16,)),
    ("Visa", ("4",), (13, 16, 19)),
    ("Maestro", ("5018", "5020", "5038", "5893", "6304", "6759", "6761", "6762", "6763"), tuple(range(12, 20))),
    ("Mastercard", tuple(str(p) for p in range(51, 56)) + tuple(str(p) for p in range(2221, 2721)), (16,)),
    ("American Express", ("34", "37"), (15,)),
    ("Diners Club", ("300", "301", "302", "303", "304", "305", "36", "38", "39"), (14, 16)),
    ("Discover", ("6011", "65", "644", "645", "646", "647", "648", "649"), (16, 19)),
    ("JCB", tuple(str(p) for p in range(3528, 3590)), (16, 17, 18, 19)),
    ("UnionPay", ("62",), (16, 17, 18, 19)),
]

_TIPO_POR_MARCA = {"Visa Electron": "debito", "Maestro": "debito", "American Express": "credito", "Diners Club": "credito"}

_TIPO_POR_CONTEXTO = [
    ("prepago", ("prepago", "prepaid", "recargable")),
    ("debito", ("debito", "debit", "redcompra", "cuenta rut", "cuenta vista")),
    ("credito", ("credito", "credit", "cuotas")),
]

_TARJETAS_DE_PRUEBA = {
    # Transbank / Webpay (ambiente de integración)
    "4051885600446623", "5186059559590568", "4051884239937763", "370000000002032",
    # Stripe y otras pasarelas
    "4111111111111111", "4242424242424242", "4012888888881881", "4000056655665556",
    "5555555555554444", "5105105105105100", "378282246310005", "6011111111111117",
}


def luhn(numero: str) -> bool:
    total = 0
    for i, d in enumerate(int(c) for c in reversed(numero)):
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def detectar_marca(numero: str) -> str | None:
    for marca, prefijos, largos in _MARCAS:
        if len(numero) in largos and numero.startswith(prefijos):
            return marca
    return None


def _agrupacion_valida(raw: str) -> bool:
    grupos = re.split(r"[ -]", raw)
    if len(grupos) == 1:
        return True
    return len(set(re.findall(r"[ -]", raw))) == 1 and tuple(map(len, grupos)) in _AGRUPACIONES_VALIDAS


class TarjetaValidator(Validator):
    name = "TARJETA_PAGO"
    positive_keywords = (
        "tarjeta", "card", "visa", "mastercard", "amex", "redcompra", "webpay", "cvv", "cvc",
        "vencimiento", "venc", "pago", "titular", "cuotas",
    )
    negative_keywords = (
        "folio", "factura", "boleta", "pedido", "orden", "seguimiento", "tracking", "guia",
        "serie", "imei", "codigo de barras",
    )

    def find_candidates(self, line):
        for m in _TARJETA_PATTERN.finditer(line):
            raw = m.group(0)
            numero = re.sub(r"[ -]", "", raw)
            if not _agrupacion_valida(raw) or not luhn(numero):
                continue
            marca = detectar_marca(numero)
            if marca is None:
                continue
            de_prueba = numero in _TARJETAS_DE_PRUEBA
            yield Candidate(m.start(), m.end(), 80 - (40 if de_prueba else 0), {
                "marca": marca,
                "tipo": self._tipo(marca, line),
                "tarjeta_de_prueba": de_prueba,
                # Truncado PCI-DSS: solo BIN y últimos 4 dígitos.
                "numero_truncado": f"{numero[:6]}{'*' * (len(numero) - 10)}{numero[-4:]}",
            })

    @staticmethod
    def _tipo(marca: str, line: str) -> str:
        if marca in _TIPO_POR_MARCA:
            return _TIPO_POR_MARCA[marca]
        for tipo, palabras in _TIPO_POR_CONTEXTO:
            if find_keywords(line, palabras):
                return tipo
        return "no_determinado"

    def risk_level(self, confidence, metadata):
        # El número de tarjeta (PAN) es dato del titular según PCI-DSS.
        if ConfidenceLevel.from_score(confidence) == ConfidenceLevel.LOW:
            return RiskLevel.CONFIDENCIAL
        return RiskLevel.RESTRINGIDO
