"""Bóveda: cifrado de los datos originales con la clave del auditor.

Cifrado híbrido, para poder escanear SIN pedir la clave y revelar CON ella:

1. Al crear la clave de auditor se genera un par de llaves RSA. La pública se
   guarda tal cual; la privada se guarda cifrada con la clave del auditor.
2. Cada escaneo genera una llave simétrica (Fernet/AES) nueva, cifra con ella los
   originales y guarda esa llave cifrada con la llave pública RSA.
3. Para revelar un dato hace falta la clave del auditor: abre la llave privada,
   que abre la llave del escaneo, que abre el dato.

Así la base interna nunca tiene un original en claro, ni siquiera para quien la robe.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from sqlalchemy.orm import Session

from ksecure.almacenamiento.modelos import Configuracion

MIN_LARGO_CLAVE = 8
_PUBLICA, _PRIVADA = "llave_publica", "llave_privada"
_OAEP = padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


class ClaveIncorrecta(Exception):
    pass


def esta_configurada(db: Session) -> bool:
    return db.get(Configuracion, _PUBLICA) is not None


def configurar(db: Session, clave: str):
    if esta_configurada(db):
        raise ValueError("La clave de auditor ya está configurada")
    if len(clave) < MIN_LARGO_CLAVE:
        raise ValueError(f"La clave debe tener al menos {MIN_LARGO_CLAVE} caracteres")
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    db.add(Configuracion(clave=_PUBLICA, valor=privada.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)))
    db.add(Configuracion(clave=_PRIVADA, valor=privada.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(clave.encode()))))
    db.commit()


def nueva_llave_escaneo(db: Session) -> tuple[Fernet, bytes]:
    """Llave para cifrar los originales de un escaneo, y esa misma llave cifrada para guardarla."""
    publica = serialization.load_pem_public_key(db.get(Configuracion, _PUBLICA).valor)
    llave = Fernet.generate_key()
    return Fernet(llave), publica.encrypt(llave, _OAEP)


def revelar(db: Session, clave: str, llave_cifrada: bytes, valor_cifrado: bytes) -> str:
    try:
        privada = serialization.load_pem_private_key(db.get(Configuracion, _PRIVADA).valor, clave.encode())
    except ValueError as e:
        raise ClaveIncorrecta() from e
    llave = privada.decrypt(llave_cifrada, _OAEP)
    return Fernet(llave).decrypt(valor_cifrado).decode()
