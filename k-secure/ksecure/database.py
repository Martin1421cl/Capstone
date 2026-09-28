"""Configuración de conexión a PostgreSQL usando SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Cambia ksecure_user y tu_contraseña por los que crees en PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://ksecure_user:1234@localhost:5432/ksecure_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """Crea las tablas en la base de datos si no existen."""
    Base.metadata.create_all(bind=engine)