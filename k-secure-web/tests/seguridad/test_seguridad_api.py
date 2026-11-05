"""Pruebas de seguridad de la API (control de acceso, fuerza bruta, inyección y fuga de datos).

Basadas en los riesgos del OWASP Top 10: A01 control de acceso roto, A03 inyección,
A07 fallas de autenticación y A09 fallas de registro y monitoreo.

Ejecutar solo estas pruebas:  pytest tests/seguridad -v
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ADMIN, CLAVE_AUDITOR, cuenta

ENDPOINTS_PROTEGIDOS = [
    ("get", "/api/escaneos"),
    ("get", "/api/usuarios"),
    ("get", "/api/bitacora"),
    ("get", "/api/reglas"),
    ("post", "/api/auditor"),
    ("post", "/api/hallazgos/1/revelar"),
]


@pytest.mark.parametrize("metodo,url", ENDPOINTS_PROTEGIDOS)
def test_sin_sesion_no_hay_acceso(admin, metodo, url):
    """A01: ningún endpoint de datos responde sin sesión iniciada."""
    anonimo = TestClient(admin.app)
    r = getattr(anonimo, metodo)(url, **({"json": {}} if metodo == "post" else {}))
    assert r.status_code == 401


def test_visor_no_puede_acciones_de_admin(admin):
    """A01: un Visor no puede crear cuentas, reglas ni la clave de auditor (escalada de privilegios)."""
    visor = cuenta(admin, "visor", "Visor")
    assert visor.get("/api/usuarios").status_code == 403
    assert visor.post("/api/usuarios", json={"usuario": "intruso", "nombre": "X",
                                             "correo": "x@x.cl", "rol": "Admin"}).status_code == 403
    assert visor.post("/api/auditor", json={"clave": "otra-clave-larga-123"}).status_code == 403
    assert visor.get("/api/bitacora").status_code == 403


def test_auditor_no_puede_administrar_cuentas(admin):
    auditor = cuenta(admin, "auditor", "Auditor")
    assert auditor.get("/api/usuarios").status_code == 403
    assert auditor.post("/api/reglas/patron", json={"ejemplos": ["AB-1234"]}).status_code == 403


def test_bloqueo_de_cuenta_por_fuerza_bruta(admin):
    """A07: 5 contraseñas incorrectas bloquean la cuenta, incluso si luego se usa la correcta."""
    otro = TestClient(admin.app)
    for _ in range(5):
        r = otro.post("/api/sesion/ingresar", json={"usuario": ADMIN["usuario"], "clave": "incorrecta-123"})
        assert r.status_code in (401, 403, 429)
    r = otro.post("/api/sesion/ingresar", json={"usuario": ADMIN["usuario"], "clave": ADMIN["clave"]})
    assert r.status_code != 200


@pytest.mark.parametrize("usuario", ["' OR '1'='1", "admin'--", "admin\"; DROP TABLE usuarios;--"])
def test_inyeccion_sql_en_login(admin, usuario):
    """A03: el login no se salta con inyección SQL y la tabla de usuarios sigue intacta."""
    otro = TestClient(admin.app)
    r = otro.post("/api/sesion/ingresar", json={"usuario": usuario, "clave": "' OR '1'='1"})
    assert r.status_code != 200
    assert admin.get("/api/usuarios").status_code == 200  # la tabla sigue existiendo


def test_contrasenas_no_se_exponen(admin):
    """La API de usuarios nunca devuelve hashes ni contraseñas."""
    texto = admin.get("/api/usuarios").text
    assert "clave_hash" not in texto and "$2b$" not in texto and ADMIN["clave"] not in texto


def test_exportacion_csv_neutraliza_formulas(admin):
    """Inyección de fórmulas en CSV: un valor que empieza con = no debe llegar como fórmula a Excel."""
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    archivo = "=HYPERLINK(\"http://malo.cl\");RUT 15.432.198-5\n".encode()
    escaneo_id = admin.post("/api/archivos", files=[("archivos", ("=malo.txt", archivo))]).json()["escaneo_id"]
    csv = admin.get(f"/api/escaneos/{escaneo_id}/exportar", params={"formato": "csv"}).text
    for linea in csv.splitlines():
        for celda in linea.split(";"):
            assert not celda.strip('"').startswith(("=", "+", "@")), linea


def test_nombre_de_archivo_con_ruta_no_escapa(admin):
    """Path traversal: un nombre como ../../etc/passwd se trata solo como nombre, sin tocar el disco."""
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    r = admin.post("/api/archivos", files=[("archivos", ("../../etc/passwd.txt", b"RUT 15.432.198-5"))])
    assert r.status_code in (200, 201)
    escaneo_id = r.json()["escaneo_id"]
    [h] = admin.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"]
    assert h["tipo"] == "RUT"  # se escaneó el contenido subido, no un archivo del servidor


def test_clave_de_auditor_incorrecta_queda_en_bitacora(admin):
    """A09: los intentos fallidos de ver originales quedan registrados como alerta."""
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    escaneo_id = admin.post("/api/archivos", files=[("archivos", ("a.txt", b"RUT 15.432.198-5"))]).json()["escaneo_id"]
    [h] = admin.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"]
    assert admin.post(f"/api/hallazgos/{h['id']}/revelar", json={"clave": "mala-clave-xx"}).status_code == 403
    assert "revelar_fallido" in admin.get("/api/bitacora").text


def test_base_del_cliente_se_abre_en_solo_lectura(tmp_path):
    """RNF-01: K-Secure no puede escribir en la base del cliente, aunque lo intente."""
    import sqlite3

    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    from ksecure.escaneo.bases_datos import DatosConexion, conectar

    ruta = tmp_path / "cliente.db"
    with sqlite3.connect(ruta) as conn:
        conn.execute("CREATE TABLE clientes (id INTEGER PRIMARY KEY, rut TEXT)")
        conn.execute("INSERT INTO clientes (rut) VALUES ('15.432.198-5')")

    engine = conectar(DatosConexion(motor="sqlite", ruta=str(ruta)))
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM clientes")).scalar() == 1
        with pytest.raises(OperationalError):
            c.execute(text("INSERT INTO clientes (rut) VALUES ('11.111.111-1')"))
        with pytest.raises(OperationalError):
            c.execute(text("DROP TABLE clientes"))
    engine.dispose()
    with sqlite3.connect(ruta) as conn:
        assert conn.execute("SELECT count(*) FROM clientes").fetchone()[0] == 1


def test_archivo_mayor_a_100_mb_se_rechaza(admin, monkeypatch):
    """RNF-04: un archivo sobre el límite se rechaza con 413 (se prueba con un límite reducido)."""
    from ksecure.web.api import escanear

    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    monkeypatch.setattr(escanear, "MAX_ARCHIVO", 1024)
    r = admin.post("/api/archivos", files=[("archivos", ("grande.txt", b"x" * 2048))])
    assert r.status_code == 413
