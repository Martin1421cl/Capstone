from fastapi.testclient import TestClient

from ksecure.web.app import app

client = TestClient(app)


def test_home_y_health():
    assert "K-Secure" in client.get("/").text
    assert client.get("/health").json() == {"status": "ok"}


def test_scan_varios_archivos():
    res = client.post("/scan", files=[
        ("files", ("clientes.csv", "nombre;rut\nAna;15.432.198-5\n".encode("cp1252"), "text/csv")),
        ("files", ("nada.bin", bytes(range(256)), "application/octet-stream")),
    ])
    assert res.status_code == 200
    ok, malo = res.json()["results"]
    assert ok["success"] and [m["text"] for m in ok["matches"]] == ["15.432.198-5"]
    assert ok["matches"][0]["risk_level"] == "Restringido"
    assert not malo["success"] and malo["error"] == "tipo de archivo no soportado"
    assert res.json()["total_matches"] == 1


def test_nombre_de_archivo_no_se_usa_como_ruta():
    res = client.post("/scan", files=[("files", ("../../evil.txt", b"RUT 15.432.198-5", "text/plain"))])
    [r] = res.json()["results"]
    assert r["filename"] == "evil.txt" and r["success"]
