"""Servicio para persistir los hallazgos en PostgreSQL."""

from ksecure.database import SessionLocal
from ksecure.db_models import DBScanResult
from ksecure.models import Finding, DataType

def mask_sensitive_data(finding: Finding) -> str:
    """Enmascara el dato sensible para no guardarlo expuesto en BD."""
    val = finding.normalized_value
    # Para RUT: oculta los primeros dígitos, muestra solo los 4 finales
    if finding.data_type == DataType.RUT and len(val) >= 4:
        return f"{'*' * (len(val) - 4)}{val[-4:]}"
    # Para Teléfonos: muestra el prefijo y los últimos 4
    elif finding.data_type == DataType.TELEFONO_MOVIL and len(val) >= 4:
        return f"{val[:4]}{'*' * (len(val) - 8)}{val[-4:]}"
    return "****"

def save_findings_to_db(findings: list[Finding]) -> None:
    """Recibe una lista de objetos Finding y los guarda en PostgreSQL."""
    if not findings:
        return

    db = SessionLocal()
    try:
        db_records = []
        for f in findings:
            record = DBScanResult(
                source=f.source,
                data_type=f.data_type.value,
                risk_level=f.risk_level.value,
                confidence=f.confidence.value,
                confidence_score=f.confidence_score,
                is_valid=f.is_valid,
                masked_value=mask_sensitive_data(f),
                reasons="; ".join(f.reasons)
            )
            db_records.append(record)
        
        db.add_all(db_records)
        db.commit()
        print(f"\n[+] Alertas: Se guardaron {len(db_records)} registros de forma segura en PostgreSQL.")
    except Exception as e:
        print(f"[-] Error al guardar en BD: {e}")
        db.rollback()
    finally:
        db.close()