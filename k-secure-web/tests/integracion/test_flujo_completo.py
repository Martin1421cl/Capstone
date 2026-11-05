"""Pruebas de integración: recorren K-Secure de punta a punta a través de la API.

A diferencia de las pruebas unitarias (un validador o una función a la vez), aquí se ejercitan
juntos la web, la sesión y los roles, el motor de escaneo, la bóveda de cifrado, la base interna
y la bitácora, tal como los usa una persona desde el navegador.

Ejecutar solo estas pruebas:  pytest tests/integracion -v
"""

import json

from tests.conftest import CLAVE_AUDITOR, cuenta

CSV_CLIENTES = (
    "nombre;rut;correo;celular;tarjeta\n"
    "Ana Pérez;15.432.198-5;ana.perez@gmail.com;+56 9 8765 4321;4111 1111 1111 1111\n"
    "Luis Soto;16.543.210-K;lsoto@empresa.cl;987654321;\n"
).encode("utf-8")


def _escanear(cliente, nombre="clientes.csv", contenido=CSV_CLIENTES) -> int:
    r = cliente.post("/api/archivos", files=[("archivos", (nombre, contenido))])
    assert r.status_code in (200, 201), r.text
    return r.json()["escaneo_id"]


def _hallazgos(cliente, escaneo_id) -> list[dict]:
    r = cliente.get(f"/api/escaneos/{escaneo_id}/hallazgos")
    assert r.status_code == 200, r.text
    return r.json()["items"]


def test_flujo_admin_auditor_visor(admin):
    """Admin configura, Auditor escanea y revela, Visor solo ve enmascarado."""
    # 1. El administrador crea la clave de auditor y las cuentas del equipo.
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    auditor = cuenta(admin, "auditora", "Auditor")
    visor = cuenta(admin, "visor", "Visor")

    # 2. La auditora sube un archivo y K-Secure lo escanea.
    escaneo_id = _escanear(auditor)
    hallazgos = _hallazgos(auditor, escaneo_id)
    tipos = {h["tipo"] for h in hallazgos}
    assert {"RUT", "EMAIL"} <= tipos, tipos

    # 3. Ningún original sale enmascarado de la API sin la clave.
    texto = json.dumps(hallazgos, ensure_ascii=False)
    for original in ("15.432.198", "16.543.210", "ana.perez@gmail.com", "4111 1111 1111 1111"):
        assert original not in texto

    # 4. El visor ve el mismo escaneo, pero no puede revelar ni escanear.
    assert len(_hallazgos(visor, escaneo_id)) == len(hallazgos)
    rut = next(h for h in hallazgos if h["tipo"] == "RUT")
    assert visor.post(f"/api/hallazgos/{rut['id']}/revelar", json={"clave": CLAVE_AUDITOR}).status_code == 403
    assert visor.post("/api/archivos", files=[("archivos", ("a.txt", b"RUT 15.432.198-5"))]).status_code == 403

    # 5. La auditora revela el original con la clave correcta.
    r = auditor.post(f"/api/hallazgos/{rut['id']}/revelar", json={"clave": CLAVE_AUDITOR})
    assert r.status_code == 200 and r.json()["valor"] in ("15.432.198-5", "16.543.210-K")

    # 6. Todo quedó en la bitácora, sin datos originales.
    bitacora = admin.get("/api/bitacora").json()
    acciones = json.dumps(bitacora, ensure_ascii=False)
    assert "dato_revelado" in acciones
    assert "15.432.198-5" not in acciones


def test_revision_y_exportacion_sin_falsos_positivos(admin):
    """Marcar un falso positivo y exportar solo los confirmados, siempre enmascarados."""
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    escaneo_id = _escanear(admin)
    hallazgos = _hallazgos(admin, escaneo_id)
    assert len(hallazgos) >= 2

    falso, verdadero = hallazgos[0], hallazgos[1]
    url = f"/api/escaneos/{escaneo_id}/hallazgos"
    assert admin.put(f"{url}/{falso['id']}/revision",
                     json={"estado": "falso_positivo", "nota": "dato de prueba"}).status_code == 200
    assert admin.put(f"{url}/{verdadero['id']}/revision", json={"estado": "confirmado"}).status_code == 200

    for formato in ("csv", "json"):
        r = admin.get(f"/api/escaneos/{escaneo_id}/exportar",
                      params={"formato": formato, "revision": "confirmado"})
        assert r.status_code == 200, r.text
        assert "attachment" in r.headers["content-disposition"]
        assert "15.432.198-5" not in r.text and "ana.perez@gmail.com" not in r.text


def test_borrar_escaneo_elimina_sus_hallazgos(admin):
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    escaneo_id = _escanear(admin)
    assert _hallazgos(admin, escaneo_id)
    assert admin.delete(f"/api/escaneos/{escaneo_id}").status_code == 204
    assert admin.get(f"/api/escaneos/{escaneo_id}").status_code == 404


def test_regla_creada_en_pantalla_se_usa_al_escanear(admin):
    """Una regla nueva (ficha clínica) se arma desde ejemplos y el motor la aplica al siguiente escaneo."""
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    patron = admin.post("/api/reglas/patron", json={"ejemplos": ["FC-123456", "FC-654321"]})
    assert patron.status_code == 200, patron.text
    regla = {"nombre": "FICHA_CLINICA", "descripcion": "Ficha clínica", "patron": patron.json()["patron"],
             "ejemplos": ["FC-123456", "FC-654321"], "riesgo": "Confidencial"}
    r = admin.post("/api/reglas", json=regla)
    assert r.status_code == 201, r.text

    escaneo_id = _escanear(admin, "fichas.txt", b"Paciente con ficha FC-777888 ingresado hoy")
    assert any(h["tipo"] == "FICHA_CLINICA" for h in _hallazgos(admin, escaneo_id))
