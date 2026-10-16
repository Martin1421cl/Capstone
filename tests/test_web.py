import sqlite3

import pytest
from fastapi.testclient import TestClient

from ksecure.web.api import auditor
from ksecure.web.app import create_app

CLAVE = "clave-auditor-123"


@pytest.fixture
def client():
    auditor.bloqueo.__init__()  # cada test parte sin intentos fallidos
    return TestClient(create_app("sqlite://"))


@pytest.fixture
def con_clave(client):
    assert client.post("/api/auditor", json={"clave": CLAVE}).status_code == 201
    return client


def subir(client, *archivos):
    return client.post("/api/archivos", files=[("archivos", a) for a in archivos])


def test_paginas_y_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert "K-Secure" in client.get("/").text


def test_sin_clave_de_auditor_no_se_escanea(client):
    assert not client.get("/api/auditor").json()["configurada"]
    assert subir(client, ("a.txt", b"RUT 15.432.198-5")).status_code == 409


def test_clave_corta_o_repetida(client):
    assert client.post("/api/auditor", json={"clave": "corta"}).status_code == 400
    assert client.post("/api/auditor", json={"clave": CLAVE}).status_code == 201
    assert client.post("/api/auditor", json={"clave": "otra-clave-larga"}).status_code == 400


def test_escaneo_de_archivos_enmascarado_y_revelado(con_clave):
    c = con_clave
    res = subir(c, ("clientes.csv", "nombre;rut\nAna;15.432.198-5\n".encode("cp1252")),
                ("nada.bin", bytes(range(256))))
    escaneo_id = res.json()["escaneo_id"]

    detalle = c.get(f"/api/escaneos/{escaneo_id}").json()
    assert detalle["origen_nombre"] == "2 archivos"
    assert detalle["por_riesgo"]["Restringido"] == 1
    assert detalle["errores"] == ["nada.bin: tipo de archivo no soportado"]

    [h] = c.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"]
    assert h["valor"] == "**.***.198-5" and h["posicion"] == "fila 2" and h["columna"] == "rut"
    assert "15.432.198" not in str(h)  # el original no sale sin clave

    assert c.post(f"/api/hallazgos/{h['id']}/revelar", json={"clave": "mala-clave"}).status_code == 403
    assert c.post(f"/api/hallazgos/{h['id']}/revelar", json={"clave": CLAVE}).json() == {"valor": "15.432.198-5"}


def test_bloqueo_tras_5_claves_malas(con_clave):
    escaneo_id = subir(con_clave, ("a.txt", b"RUT 15.432.198-5")).json()["escaneo_id"]
    [h] = con_clave.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"]
    url = f"/api/hallazgos/{h['id']}/revelar"
    for _ in range(5):
        assert con_clave.post(url, json={"clave": "mala-clave"}).status_code == 403
    assert con_clave.post(url, json={"clave": CLAVE}).status_code == 429


def test_base_sqlite_con_clasificacion_por_columna(con_clave, tmp_path):
    ruta = tmp_path / "empresa.db"
    with sqlite3.connect(ruta) as conn:
        conn.execute("CREATE TABLE kna1 (id INTEGER PRIMARY KEY, H14510 TEXT, nombre TEXT)")
        conn.executemany("INSERT INTO kna1 (H14510, nombre) VALUES (?, ?)",
                         [("15.432.198-5", "Ana"), ("16.543.210-K", "Luis"), ("", "Sin RUT"), (None, "Otro")])
    escaneo_id = subir(con_clave, ("empresa.db", ruta.read_bytes())).json()["escaneo_id"]

    detalle = con_clave.get(f"/api/escaneos/{escaneo_id}").json()
    assert detalle["filas_revisadas"] == 4
    [col] = detalle["columnas"]
    assert col == {"fuente": "empresa.db › kna1", "columna": "H14510", "filas_con_datos": 2,
                   "porcentaje": 50, "riesgo": "Restringido", "tipo": "RUT"}
    items = con_clave.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"]
    assert [i["posicion"] for i in items] == ["fila id=1", "fila id=2"]


def test_historial_y_borrado(con_clave):
    escaneo_id = subir(con_clave, ("a.txt", b"+56 9 6123 4870")).json()["escaneo_id"]
    assert [e["id"] for e in con_clave.get("/api/escaneos").json()] == [escaneo_id]
    assert con_clave.delete(f"/api/escaneos/{escaneo_id}").status_code == 204
    assert con_clave.get(f"/api/escaneos/{escaneo_id}").status_code == 404


def test_nombre_de_archivo_no_se_usa_como_ruta(con_clave):
    escaneo_id = subir(con_clave, ("../../evil.txt", b"RUT 15.432.198-5")).json()["escaneo_id"]
    [h] = con_clave.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"]
    assert h["fuente"] == "evil.txt"


def test_bd_servidor_inalcanzable_da_error_claro(client):
    res = client.post("/api/bd/probar", json={
        "motor": "postgresql", "host": "127.0.0.1", "puerto": 1, "base": "x", "usuario": "u", "clave": "c"})
    assert res.status_code == 400 and res.json()["detail"].startswith("No se pudo conectar")


def test_ordenar_hallazgos(con_clave):
    texto = ("correo ana.rojas@gmail.com\n"           # EMAIL, Confidencial
             "fijo 41 223 4567\n"                     # TELEFONO, Interno
             "tarjeta 4532 0151 1283 0366\n"          # TARJETA_PAGO, Restringido
             "RUT: 15.432.198-5\n")                   # RUT, Restringido
    escaneo_id = subir(con_clave, ("a.txt", texto.encode())).json()["escaneo_id"]
    url = f"/api/escaneos/{escaneo_id}/hallazgos"
    tipos = lambda q="": [h["tipo"] for h in con_clave.get(url + q).json()["items"]]

    # Por defecto, primero el riesgo más alto; a igual riesgo, el RUT antes que la tarjeta.
    assert tipos() == ["RUT", "TARJETA_PAGO", "EMAIL", "TELEFONO"]
    assert tipos("?orden=riesgo&invertir=true") == ["TELEFONO", "EMAIL", "RUT", "TARJETA_PAGO"]
    assert tipos("?orden=tipo") == ["RUT", "TARJETA_PAGO", "TELEFONO", "EMAIL"]
    confianzas = [h["confianza"] for h in con_clave.get(url + "?orden=confianza").json()["items"]]
    assert confianzas == sorted(confianzas, reverse=True)
    assert tipos("?orden=ubicacion") == ["EMAIL", "TELEFONO", "TARJETA_PAGO", "RUT"]  # orden del archivo
    assert con_clave.get(url + "?orden=inventado").status_code == 422


# --- Publicación en la nube ----------------------------------------------------------

from ksecure.almacenamiento.db import normalizar_url


def test_candado_de_acceso():
    c = TestClient(create_app("sqlite://", acceso="equipo:clave-secreta"))
    assert c.get("/").status_code == 401
    assert c.get("/api/escaneos").headers["www-authenticate"].startswith("Basic")
    assert c.get("/api/escaneos", auth=("equipo", "otra")).status_code == 401
    assert c.get("/api/escaneos", auth=("equipo", "clave-secreta")).status_code == 200
    assert c.get("/api/health").status_code == 200  # Render la usa para saber si la app está viva
    with pytest.raises(ValueError):
        create_app("sqlite://", acceso="sin-dos-puntos")


@pytest.mark.parametrize("url, esperada", [
    ("postgres://u:p@ep-x.neon.tech/db?sslmode=require", "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require"),
    ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("sqlite:///data/ksecure.db", "sqlite:///data/ksecure.db"),
])
def test_url_de_neon(url, esperada):
    assert normalizar_url(url) == esperada
