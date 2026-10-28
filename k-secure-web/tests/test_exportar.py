"""Exportar resultados en CSV, JSON y PDF (RF-15): siempre enmascarados y con los filtros de la pantalla."""

import io
import json

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from ksecure import exportar
from tests.conftest import CLAVE_AUDITOR, cuenta

RUT, CORREO = "15.432.198-5", "ana.perez@gmail.com"
PLANILLA = f"nombre,rut,correo\nAna,{RUT},{CORREO}\nLuis,12.345.678-5,luis@hotmail.com\n".encode()


@pytest.fixture
def escaneo(admin) -> int:
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    return admin.post("/api/archivos", files=[("archivos", ("Clientes Ñuñoa.csv", PLANILLA))]).json()["escaneo_id"]


def bajar(c, escaneo_id, **params):
    return c.get(f"/api/escaneos/{escaneo_id}/exportar", params=params)


def texto_pdf(contenido: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(contenido)).pages)


def sin_originales(texto: str):
    assert RUT not in texto and "15432198" not in texto and CORREO not in texto and "12.345.678-5" not in texto


def test_csv_para_excel(admin, escaneo):
    r = bajar(admin, escaneo, formato="csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"] == f'attachment; filename="ksecure-escaneo-{escaneo}-clientes-nunoa-csv.csv"'
    texto = r.content.decode("utf-8")
    filas = texto.lstrip("﻿").splitlines()
    assert texto.startswith("﻿") and filas[0].startswith("Fuente;Columna;Posición;Tipo;Riesgo")
    assert len(filas) == 1 + 4 and ";RUT;Restringido;" in filas[1] and ";Alta;" in filas[1]  # mayor riesgo primero
    assert "**.***.198-5" in texto
    sin_originales(texto)


def test_json_para_otros_sistemas(admin, escaneo):
    r = bajar(admin, escaneo, formato="json")
    assert r.headers["content-type"] == "application/json"
    doc = r.json()
    assert doc["generado_por"] == "K-Secure" and "enmascarados" in doc["aviso"]
    assert doc["exportado_por"] == {"usuario": "admin", "nombre": "Ana Admin"}
    assert doc["escaneo"]["origen_nombre"] == "Clientes Ñuñoa.csv" and doc["escaneo"]["total_hallazgos"] == 4
    assert doc["hallazgos_exportados"] == 4 and doc["filtros"] == {"riesgo": None, "tipo": None, "buscar": None, "revision": None}
    primero = doc["hallazgos"][0]
    assert primero["tipo"] == "RUT" and primero["valor_enmascarado"] == "**.***.198-5" and primero["columna"] == "rut"
    sin_originales(json.dumps(doc, ensure_ascii=False))


def test_pdf_de_reporte(admin, escaneo):
    r = bajar(admin, escaneo, formato="pdf", desfase=180)
    assert r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    texto = texto_pdf(r.content)
    for esperado in ("Reporte de escaneo", "Clientes Ñuñoa.csv", "Ana Admin (@admin)", "Resumen por riesgo",
                     "Columnas sensibles", "**.***.198-5", "Página 1 de 1", "no contiene datos originales"):
        assert esperado in texto, esperado
    sin_originales(texto)


def test_respeta_los_filtros(admin, escaneo):
    doc = bajar(admin, escaneo, formato="json", tipo="EMAIL").json()
    assert doc["hallazgos_exportados"] == 2 and {h["tipo"] for h in doc["hallazgos"]} == {"EMAIL"}
    assert doc["filtros"]["tipo"] == "EMAIL" and doc["escaneo"]["total_hallazgos"] == 4  # el resumen es de todo
    assert "tipo Correo" in texto_pdf(bajar(admin, escaneo, formato="pdf", tipo="EMAIL").content)
    assert len(bajar(admin, escaneo, formato="csv", buscar="no-existe").content.decode().splitlines()) == 1


def test_pdf_largo_muestra_los_primeros(admin, monkeypatch):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    filas = "\n".join(f"Persona {i},{RUT}" for i in range(30))
    escaneo_id = admin.post("/api/archivos", files=[("archivos", ("muchos.csv", f"nombre,rut\n{filas}".encode()))]).json()["escaneo_id"]
    monkeypatch.setattr(exportar, "MAX_PDF", 10)
    assert "primeros 10 de 30" in texto_pdf(bajar(admin, escaneo_id, formato="pdf").content)


def test_cualquiera_que_ve_resultados_puede_exportar_y_queda_anotado(admin, escaneo):
    visor = cuenta(admin, "vale", "Visor")
    assert bajar(visor, escaneo, formato="csv").status_code == 200
    assert bajar(TestClient(admin.app), escaneo).status_code == 401
    assert bajar(admin, 999).status_code == 404
    assert bajar(admin, escaneo, formato="xlsx").status_code == 422
    evento = next(e for e in admin.get("/api/bitacora").json()["eventos"] if e["accion"] == "resultados_exportados")
    assert evento["usuario"] == "vale" and evento["escaneo_id"] == escaneo
    assert evento["detalle"] == f"Escaneo #{escaneo}: Clientes Ñuñoa.csv · CSV · 4 hallazgos"


def test_csv_no_ejecuta_formulas(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    escaneo_id = admin.post("/api/archivos", files=[("archivos", ("=HYPERLINK.csv", f"rut\n{RUT}\n".encode()))]).json()["escaneo_id"]
    assert "'=HYPERLINK.csv;" in bajar(admin, escaneo_id, formato="csv").content.decode()
