"""Página Seguridad: ejemplo en vivo de enmascarar, cifrar y hashear (pedido del profesor).

No guarda nada: toma un texto corto, lo enmascara con los mismos validadores de los escaneos,
lo cifra con una llave desechable y calcula su hash, para mostrar la diferencia entre las tres.
"""

import hashlib

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ksecure.almacenamiento import reglas
from ksecure.web.api.dependencias import VISOR_O_MAS, get_db

router = APIRouter(prefix="/api/seguridad", tags=["seguridad"], dependencies=[VISOR_O_MAS])


class Ejemplo(BaseModel):
    texto: str = Field(min_length=1, max_length=100)


@router.post("/ejemplo")
def ejemplo(datos: Ejemplo, db: Session = Depends(get_db)):
    """El dato enmascarado (como en Resultados), cifrado (cambia cada vez) y hasheado (siempre igual)."""
    texto = datos.texto.strip()
    encontrados = [m for v in reglas.validadores_activos(db) for m in v.validate_content(texto, "ejemplo")]
    mejor = max(encontrados, key=lambda m: (m.confidence, len(m.text)), default=None)
    dato = mejor.text if mejor else texto
    return {
        "dato": dato,
        "tipo": mejor.type if mejor else None,
        "enmascarado": mejor.masked_text if mejor else None,
        # Llave nueva y desechable en cada llamada: el mismo dato da un cifrado distinto cada vez.
        "cifrado": Fernet(Fernet.generate_key()).encrypt(dato.encode()).decode(),
        "hash": hashlib.sha256(dato.encode()).hexdigest(),
    }
