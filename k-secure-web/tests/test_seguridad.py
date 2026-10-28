"""Página Seguridad: ejemplo en vivo de enmascarar, cifrar y hashear."""

import hashlib

from fastapi.testclient import TestClient

from tests.conftest import cuenta


def probar(c, texto):
    return c.post("/api/seguridad/ejemplo", json={"texto": texto})


def test_enmascara_como_los_escaneos_cifra_distinto_y_hashea_igual(admin):
    visor = cuenta(admin, "vale", "Visor")  # cualquier rol puede verla
    uno, dos = probar(visor, "15.432.198-5").json(), probar(visor, "15.432.198-5").json()
    assert uno["tipo"] == "RUT" and uno["enmascarado"] == "**.***.198-5"
    assert uno["cifrado"] != dos["cifrado"] and "15.432.198-5" not in uno["cifrado"]
    assert uno["hash"] == dos["hash"] == hashlib.sha256(b"15.432.198-5").hexdigest()


def test_busca_el_dato_dentro_del_texto(admin):
    r = probar(admin, "mi correo es ana.perez@gmail.com").json()
    assert r["tipo"] == "EMAIL" and r["dato"] == "ana.perez@gmail.com" and "ana.perez" not in r["enmascarado"]


def test_texto_sin_dato_sensible(admin):
    r = probar(admin, "hola mundo").json()
    assert r["tipo"] is None and r["enmascarado"] is None and r["hash"] == hashlib.sha256(b"hola mundo").hexdigest()


def test_limites_y_sesion(admin):
    assert probar(admin, "x" * 101).status_code == 422
    assert probar(admin, "").status_code == 422
    assert probar(TestClient(admin.app), "15.432.198-5").status_code == 401
    assert cuenta(admin, "pedro", "Visor").get("/seguridad.html").status_code == 200
