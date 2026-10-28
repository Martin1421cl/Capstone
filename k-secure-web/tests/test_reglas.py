import pytest

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.regla import ParametrosRegla, ReglaValidator
from tests.conftest import app_con_admin

PASAPORTE = {
    "nombre": "PASAPORTE", "descripcion": "Pasaporte chileno", "patron": r"\b[A-Z]\d{8}\b",
    "palabras_positivas": ["pasaporte"], "confianza": 70, "riesgo": "Restringido", "visibles": 3,
}


# --- Validador genérico ------------------------------------------------------------

def test_regla_detecta_enmascara_y_usa_contexto():
    v = ReglaValidator(ParametrosRegla("PASAPORTE", r"\b[A-Z]\d{8}\b", palabras_positivas=("pasaporte",),
                                       riesgo=RiskLevel.RESTRINGIDO, visibles=3))
    [m] = v.validate_content("Pasaporte: F12345678", "x")
    assert m.type == "PASAPORTE" and m.masked_text == "******678"
    assert m.confidence == 80 and m.risk_level == RiskLevel.RESTRINGIDO


@pytest.mark.parametrize("validacion, valido, invalido", [
    ("modulo11", "15432198-5", "15432198-4"),
    ("luhn", "4532015112830366", "4532015112830367"),
])
def test_validacion_baja_confianza_si_no_pasa(validacion, valido, invalido):
    v = ReglaValidator(ParametrosRegla("X_ID", r"[\d-]{8,}", validacion=validacion))
    [ok] = v.validate_content(valido, "x")
    [malo] = v.validate_content(invalido, "x")
    assert ok.metadata["validacion_ok"] and not malo.metadata["validacion_ok"]
    assert malo.confidence_level == ConfidenceLevel.LOW and malo.risk_level == RiskLevel.INTERNO


def test_patron_que_calza_vacio_no_genera_hallazgos():
    assert ReglaValidator(ParametrosRegla("VACIO", r"\d*")).validate_content("abc", "x") == []


# --- API y escaneo -------------------------------------------------------------------

@pytest.fixture
def client():
    c = app_con_admin()  # las reglas las cambia un administrador
    c.post("/api/auditor", json={"clave": "clave-auditor-123"})
    return c


def escanear(client, texto: str) -> list[dict]:
    escaneo_id = client.post("/api/archivos", files=[("archivos", ("a.txt", texto.encode()))]).json()["escaneo_id"]
    return client.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"]


def test_regla_nueva_se_usa_al_escanear(client):
    assert escanear(client, "Pasaporte F12345678") == []
    assert client.post("/api/reglas", json=PASAPORTE).status_code == 201
    [h] = escanear(client, "Pasaporte F12345678")
    assert h["tipo"] == "PASAPORTE" and h["valor"] == "******678" and h["riesgo"] == "Restringido"


def test_editar_desactivar_y_borrar_regla(client):
    regla = client.post("/api/reglas", json=PASAPORTE).json()
    assert client.put(f"/api/reglas/{regla['id']}", json={**PASAPORTE, "activa": False}).status_code == 200
    assert escanear(client, "Pasaporte F12345678") == []
    assert client.delete(f"/api/reglas/{regla['id']}").status_code == 204
    assert client.get("/api/reglas").json()["personalizadas"] == []


def test_desactivar_validador_incluido_y_sumarle_palabras(client):
    assert client.put("/api/reglas/incluidas/RUT", json={"activo": False}).status_code == 204
    assert escanear(client, "RUT 15.432.198-5") == []
    client.put("/api/reglas/incluidas/RUT", json={"activo": True, "palabras_positivas": ["Afiliado ", "rut"]})
    [h] = escanear(client, "afiliado 15432198-5")
    assert h["contexto"] == "afiliado"
    rut = next(i for i in client.get("/api/reglas").json()["incluidos"] if i["nombre"] == "RUT")
    assert rut["palabras_positivas"] == ["afiliado", "rut"] and "rut" in rut["palabras_base"]


@pytest.mark.parametrize("cambio, mensaje", [
    ({"patron": "[sin cerrar"}, "expresión regular"),
    ({"nombre": "con espacios"}, "MAYÚSCULAS"),
    ({"nombre": "RUT"}, "validador incluido"),
    ({"riesgo": "Altísimo"}, "Riesgo"),
    ({"validacion": "magia"}, "Validación"),
])
def test_reglas_invalidas_dan_error_claro(client, cambio, mensaje):
    res = client.post("/api/reglas", json={**PASAPORTE, **cambio})
    assert res.status_code == 400 and mensaje in res.json()["detail"]


def test_nombre_repetido(client):
    client.post("/api/reglas", json=PASAPORTE)
    assert "Ya existe" in client.post("/api/reglas", json=PASAPORTE).json()["detail"]


def test_probar_regla_sin_guardarla(client):
    res = client.post("/api/reglas/probar", json={"regla": PASAPORTE, "texto": "x\nPasaporte F12345678 y G87654321"})
    assert [(r["texto"], r["linea"], r["contexto"]) for r in res.json()] == [
        ("F12345678", 2, ["pasaporte"]), ("G87654321", 2, ["pasaporte"])]
    assert client.get("/api/reglas").json()["personalizadas"] == []


# --- Patrón desde ejemplos -----------------------------------------------------------

import re
import sqlite3

from ksecure.almacenamiento.db import crear_sesiones
from ksecure.validators.patron import generar_patron


@pytest.mark.parametrize("ejemplos, descripcion, calza, no_calza", [
    (["F12345678"], "1 letra + 8 números", ["Pasaporte F12345678."], ["F1234567", "AF12345678", "F123456789"]),
    (["FC-123456", "FC-9876543"], "«FC» + guion + 6 a 7 números", ["ficha FC-1234567"], ["XY-123456", "FC-12345"]),
    (["ab 12", "cd 345"], "2 letras + espacio opcional + 2 a 3 números", ["xy12", "xy 123"], ["XY 12"]),
    (["P-1", "12/34"], "1 letra + guion + 1 número o 2 números + barra + 2 números", ["Q-7", "99/01"], ["Q/7"]),
])
def test_patron_desde_ejemplos(ejemplos, descripcion, calza, no_calza):
    patron, texto = generar_patron(ejemplos)
    assert texto == descripcion
    assert all(re.search(patron, t) for t in calza + ejemplos)
    assert not any(re.search(patron, t) for t in no_calza)


@pytest.mark.parametrize("ejemplos", [[], ["  "], ["x" * 61]])
def test_patron_sin_ejemplos_utiles(ejemplos):
    with pytest.raises(ValueError):
        generar_patron(ejemplos)


def test_api_patron_y_ejemplos_guardados(client):
    res = client.post("/api/reglas/patron", json={"ejemplos": ["SOC00123", "SOC99812"]}).json()
    assert res["descripcion"] == "«SOC» + 5 números"
    regla = client.post("/api/reglas", json={**PASAPORTE, "nombre": "SOCIO", "patron": res["patron"],
                                             "ejemplos": ["SOC00123", " ", "SOC99812"]}).json()
    assert regla["ejemplos"] == ["SOC00123", "SOC99812"]
    assert client.post("/api/reglas/patron", json={"ejemplos": []}).status_code == 400


def test_base_antigua_recibe_columnas_nuevas(tmp_path):
    ruta = tmp_path / "vieja.db"
    with sqlite3.connect(ruta) as conn:  # tabla "reglas" como la creó la versión anterior, sin "ejemplos"
        conn.execute("CREATE TABLE reglas (id INTEGER PRIMARY KEY, nombre VARCHAR(50), descripcion VARCHAR(300), "
                     "patron VARCHAR(500), validacion VARCHAR(20), palabras_positivas JSON, palabras_negativas JSON, "
                     "requiere_contexto BOOLEAN, confianza INTEGER, riesgo VARCHAR(20), visibles INTEGER, activa BOOLEAN)")
        conn.execute("INSERT INTO reglas (nombre, patron, riesgo, activa) VALUES ('VIEJA', 'x', 'Interno', 1)")
    crear_sesiones(f"sqlite:///{ruta}")
    with sqlite3.connect(ruta) as conn:
        assert "ejemplos" in [c[1] for c in conn.execute("PRAGMA table_info(reglas)")]
        assert conn.execute("SELECT nombre FROM reglas").fetchall() == [("VIEJA",)]
