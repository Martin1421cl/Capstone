from ksecure.database import SessionLocal
from ksecure.db_models import DBScanResult
from ksecure.models import Finding
from typing import List

def save_findings_to_db(findings: List[Finding]):
    db = SessionLocal()
    try:
        for finding in findings:
            db_result = DBScanResult(
                source=finding.source,
                data_type=finding.data_type,
                risk_level=finding.risk_level,
                confidence=finding.confidence,
                confidence_score=finding.confidence_score,
                is_valid=finding.is_valid,
                masked_value=finding.masked_value
            )
            db.add(db_result)
        db.commit()
    finally:
        db.close()