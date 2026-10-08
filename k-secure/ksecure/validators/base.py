import re
from typing import List, Optional
from ksecure.models import Finding, DataType, RiskLevel, Confidence

class BaseValidator:
    def __init__(self, name: DataType, pattern: str, risk_level: RiskLevel, confidence: Confidence, score: float, whitelist: Optional[List[str]] = None):
        self.name = name
        self.pattern = re.compile(pattern)
        self.risk_level = risk_level
        self.confidence = confidence
        self.score = score
        self.whitelist = whitelist or [] 

    def is_suppressed(self, value: str) -> bool:
        clean_value = value.strip().replace(" ", "")
        clean_whitelist = [w.replace(" ", "") for w in self.whitelist]
        return clean_value in clean_whitelist

    def is_already_masked(self, value: str) -> bool:
        return value.count('*') > 2 or value.count('X') > 2 or value.count('x') > 2

    def mask(self, value: str) -> str:
        raise NotImplementedError("Debe implementarse en la clase hija")

    def normalize(self, value: str) -> str:
        """Puede ser sobrescrito por clases hijas para estandarizar el formato."""
        return value.strip()

    def find(self, content: str, source: str) -> List[Finding]:
        findings = []
        if not content:
            return findings
            
        for match in self.pattern.finditer(content):
            raw_value = match.group(0)
            
            if self.is_suppressed(raw_value) or self.is_already_masked(raw_value):
                continue
                
            finding = Finding(
                source=source,
                data_type=self.name,
                risk_level=self.risk_level,
                confidence=self.confidence,
                confidence_score=self.score,
                is_valid=True,
                raw_value=raw_value,
                normalized_value=self.normalize(raw_value),
                masked_value=self.mask(raw_value)
            )
            findings.append(finding)
            
        return findings