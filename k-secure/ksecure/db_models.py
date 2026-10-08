from sqlalchemy import Column, Integer, String, Boolean
from ksecure.database import Base

class CompanyData(Base):
    __tablename__ = "company_data"

    id = Column(Integer, primary_key=True, index=True) # <-- Aquí estaba el error
    nombre = Column(String, index=True)
    rut = Column(String, index=True)
    email = Column(String, index=True)
    telefono = Column(String)
    tarjeta_credito = Column(String)
    