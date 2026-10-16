import pytest
from fastapi.testclient import TestClient

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.regla import ParametrosRegla, ReglaValidator
from ksecure.web.app import create_app

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
    c = TestClient(create_app("sqlite://"))
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
