"""Modelos de base de datos usando SQLAlchemy para K-Secure."""

import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text
from ksecure.database import Base

class DBScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Mapeo desde el modelo Finding
    source = Column(String, index=True)                 # Origen (ej. sample_data.csv:fila 1)
    data_type = Column(String, index=True)              # Tipo de dato (ej. RUT)
    risk_level = Column(String, index=True)             # Riesgo (ej. Confidencial)
    
    confidence = Column(String)                         # Alta, Media, Baja
    confidence_score = Column(Float)                    # 0.0 - 1.0
    is_valid = Column(Boolean)                          # Validado por algoritmo
    
    # Dato ENMASCARADO (Ej: *******5-4). Jamás guardar raw_value.
    masked_value = Column(String)                       
    reasons = Column(Text)                              # Explicación de la detección