import re
from ksecure.models import Confidence, DataType, Finding, RiskLevel
from ksecure.validators.base import BaseValidator

# Captura 13 a 16 dígitos, permitiendo espacios o guiones entre medio
_CC_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

def luhn_checksum(card_number: str) -> bool:
    """Aplica el algoritmo de Luhn para validar la tarjeta."""
    digits = [int(c) for c in card_number if c.isdigit()]
    if not digits:
        return False
    
    checksum = 0
    reverse_digits = digits[::-1]
    
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
        
    return checksum % 10 == 0

class CreditCardValidator(BaseValidator):
    """Detecta números de Tarjeta de Crédito usando Regex + Algoritmo de Luhn."""
    
    POSITIVE_KEYWORDS = ["visa", "mastercard", "amex", "tarjeta", "credit", "ccv", "cvv", "vencimiento"]

    def find(self, text: str, source: str) -> list[Finding]:
        findings = []
        for match in _CC_PATTERN.finditer(text):
            raw_value = match.group(0)
            normalized = re.sub(r"[\s-]", "", raw_value)
            
            # Filtro básico de longitud
            if len(normalized) < 13 or len(normalized) > 16:
                continue

            is_valid = luhn_checksum(normalized)
            
            # Si no pasa Luhn, lo descartamos como falso positivo (igual que Ferret)
            if not is_valid:
                continue

            # Aquí podrías agregar la lógica de contexto (Confidence) buscando POSITIVE_KEYWORDS
            # alrededor de match.start() y match.end()
            
            findings.append(Finding(
                data_type=DataType.TARJETA_CREDITO,
                raw_value=raw_value,
                normalized_value=normalized,
                is_valid=is_valid,
                confidence=Confidence.ALTA, 
                confidence_score=0.9,
                risk_level=RiskLevel.RESTRINGIDO, # Las tarjetas son nivel Restringido
                source=source,
                reasons=["Validación exitosa del algoritmo de Luhn"]
            ))
            
        return findings