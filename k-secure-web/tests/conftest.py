"""Ayudas comunes de las pruebas: cuentas con sesión iniciada en una base en memoria."""

import os

import pytest
from fastapi.testclient import TestClient

from ksecure.almacenamiento import usuarios
from ksecure.web.app import create_app

usuarios.RONDAS_BCRYPT = 4  # bcrypt más liviano: mismas reglas, pruebas rápidas
# Las pruebas nunca mandan correos de verdad, aunque el PC tenga configurado el envío.
os.environ.pop("KSECURE_CORREO_URL", None)
os.environ.pop("KSECURE_CORREO_SECRETO", None)

ADMIN = {"usuario": "admin", "nombre": "Ana Admin", "correo": "ana@empresa.cl", "clave": "clave-admin-123"}
CLAVE_AUDITOR = "clave-auditor-123"


def app_con_admin() -> TestClient:
    """K-Secure recién instalado, con el primer administrador creado y su sesión iniciada."""
    c = TestClient(create_app("sqlite://"))
    assert c.post("/api/sesion/configurar", json=ADMIN).status_code == 201
    return c


def cuenta(admin: TestClient, usuario: str, rol: str, clave: str | None = None) -> TestClient:
    """Crea una cuenta con ese rol y devuelve un navegador aparte con su sesión ya iniciada."""
    r = admin.post("/api/usuarios", json={"usuario": usuario, "nombre": usuario.title(),
                                          "correo": f"{usuario}@empresa.cl", "rol": rol})
    assert r.status_code == 201, r.text
    otro = TestClient(admin.app)
    assert otro.post("/api/sesion/ingresar", json={"usuario": usuario, "clave": r.json()["clave_temporal"]}).status_code == 200
    clave = clave or f"clave-de-{usuario}"
    assert otro.post("/api/sesion/cambiar-clave", json={"nueva": clave}).status_code == 200
    return otro


@pytest.fixture
def admin() -> TestClient:
    return app_con_admin()
