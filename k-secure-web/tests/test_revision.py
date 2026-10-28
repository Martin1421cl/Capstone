"""Revisión de hallazgos (RF-16): confirmar, marcar falsos positivos o volver a pendiente."""

import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import text

from ksecure.almacenamiento.db import crear_sesiones
from tests.conftest import CLAVE_AUDITOR, cuenta

PLANILLA = b"nombre,rut,correo,celular\nAna,15.432.198-5,ana@gmail.com,+56 9 8765 4321\nLuis,12.345.678-5,luis@gmail.com,+56 9 1234 5678\n"


@pytest.fixture
def escaneo(admin) -> int:
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    return admin.post("/api/archivos", files=[("archivos", ("clientes.csv", PLANILLA))]).json()["escaneo_id"]


def items(c, escaneo_id, **filtros) -> list[dict]:
    return c.get(f"/api/escaneos/{escaneo_id}/hallazgos", params={"por_pagina": 200, **filtros}).json()["items"]


def marcar(c, escaneo_id, hallazgo_id, estado, nota=None):
    return c.put(f"/api/escaneos/{escaneo_id}/hallazgos/{hallazgo_id}/revision", json={"estado": estado, "nota": nota})


def resumen(c, escaneo_id) -> dict:
    return c.get(f"/api/escaneos/{escaneo_id}").json()["revision"]


def test_todo_parte_pendiente(admin, escaneo):
    assert {h["revision"] for h in items(admin, escaneo)} == {"pendiente"}
    assert resumen(admin, escaneo) == {"pendiente": 6, "confirmado": 0, "falso_positivo": 0}


def test_marcar_uno_y_deshacer(admin, escaneo):
    aldo = cuenta(admin, "aldo", "Auditor")
    telefono = next(h for h in items(aldo, escaneo) if h["tipo"] == "TELEFONO")
    r = marcar(aldo, escaneo, telefono["id"], "falso_positivo", "  Es un número de   pedido ")
    assert r.status_code == 200
    assert r.json()["revision"] == "falso_positivo" and r.json()["revisado_por"] == "aldo"
    assert r.json()["nota"] == "Es un número de pedido" and r.json()["revisado_en"].endswith("Z")
    rut = items(aldo, escaneo)[0]
    assert marcar(aldo, escaneo, rut["id"], "confirmado").json()["nota"] is None
    assert resumen(aldo, escaneo) == {"pendiente": 4, "confirmado": 1, "falso_positivo": 1}

    de_nuevo = marcar(aldo, escaneo, telefono["id"], "pendiente", "da lo mismo").json()
    assert de_nuevo["revision"] == "pendiente" and de_nuevo["revisado_por"] is None and de_nuevo["nota"] is None


def test_filtrar_por_revision(admin, escaneo):
    lista = items(admin, escaneo)
    marcar(admin, escaneo, lista[0]["id"], "confirmado")
    marcar(admin, escaneo, lista[1]["id"], "falso_positivo")
    assert [h["id"] for h in items(admin, escaneo, revision="confirmado")] == [lista[0]["id"]]
    assert [h["id"] for h in items(admin, escaneo, revision="falso_positivo")] == [lista[1]["id"]]
    assert len(items(admin, escaneo, revision="pendiente")) == 4
    assert lista[1]["id"] not in {h["id"] for h in items(admin, escaneo, revision="sin_falsos")}
    assert len(items(admin, escaneo, revision="sin_falsos")) == 5
    por_tipo = admin.get(f"/api/escaneos/{escaneo}/por-tipo", params={"revision": "falso_positivo"}).json()
    assert por_tipo["total"] == 1
    assert admin.get(f"/api/escaneos/{escaneo}/hallazgos", params={"revision": "otro"}).status_code == 422


def test_marcar_todos_los_del_filtro(admin, escaneo):
    r = admin.post(f"/api/escaneos/{escaneo}/revision",
                   json={"estado": "falso_positivo", "nota": "Celulares de prueba", "tipo": "TELEFONO"})
    assert r.json() == {"marcados": 2}
    assert {h["revision"] for h in items(admin, escaneo, tipo="TELEFONO")} == {"falso_positivo"}
    assert {h["revision"] for h in items(admin, escaneo, tipo="RUT")} == {"pendiente"}
    # Solo los pendientes: no pisa lo que ya se revisó
    assert admin.post(f"/api/escaneos/{escaneo}/revision",
                      json={"estado": "confirmado", "revision": "pendiente"}).json() == {"marcados": 4}
    assert resumen(admin, escaneo) == {"pendiente": 0, "confirmado": 4, "falso_positivo": 2}
    evento = next(e for e in admin.get("/api/bitacora").json()["eventos"] if e["accion"] == "hallazgos_revisados")
    assert evento["detalle"].startswith("4 hallazgos → Confirmado (escaneo #")


def test_solo_auditor_y_admin_marcan_y_queda_en_la_bitacora(admin, escaneo):
    visor = cuenta(admin, "vale", "Visor")
    h = items(visor, escaneo)[0]
    assert marcar(visor, escaneo, h["id"], "confirmado").status_code == 403
    assert visor.post(f"/api/escaneos/{escaneo}/revision", json={"estado": "confirmado"}).status_code == 403
    assert marcar(TestClient(admin.app), escaneo, h["id"], "confirmado").status_code == 401
    assert marcar(admin, escaneo, 99999, "confirmado").status_code == 404
    assert marcar(admin, escaneo + 1, h["id"], "confirmado").status_code == 404  # de otro escaneo
    assert marcar(admin, escaneo, h["id"], "dudoso").status_code == 422

    marcar(admin, escaneo, h["id"], "falso_positivo", "RUT de ejemplo")
    evento = next(e for e in admin.get("/api/bitacora").json()["eventos"] if e["accion"] == "hallazgo_revisado")
    assert evento["categoria"] == "Revisión" and evento["escaneo_id"] == escaneo
    assert evento["detalle"].startswith("Falso positivo: RUT **.***.198-5 en clientes.csv")
    assert evento["detalle"].endswith("· motivo: «RUT de ejemplo»")
    assert "15.432.198-5" not in evento["detalle"]


def test_exportar_incluye_la_revision(admin, escaneo):
    lista = items(admin, escaneo)
    marcar(admin, escaneo, lista[0]["id"], "falso_positivo", "Dato de prueba")
    doc = admin.get(f"/api/escaneos/{escaneo}/exportar", params={"formato": "json"}).json()
    assert doc["escaneo"]["revision"]["falso_positivo"] == 1
    primero = next(h for h in doc["hallazgos"] if h["id"] == lista[0]["id"])
    assert primero["revision"] == "falso_positivo" and primero["nota_revision"] == "Dato de prueba"
    sin_falsos = admin.get(f"/api/escaneos/{escaneo}/exportar", params={"formato": "json", "revision": "sin_falsos"}).json()
    assert sin_falsos["hallazgos_exportados"] == 5
    csv = admin.get(f"/api/escaneos/{escaneo}/exportar", params={"formato": "csv"}).content.decode()
    assert ";Revisión;Revisado por;Motivo" in csv.splitlines()[0] and ";Falso positivo;admin;Dato de prueba" in csv
    pdf = admin.get(f"/api/escaneos/{escaneo}/exportar", params={"formato": "pdf", "revision": "sin_falsos"}).content
    texto = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    assert "revisión: sin falsos positivos" in texto and "1 falsos positivos" in texto


def test_base_anterior_recibe_las_columnas_de_revision(tmp_path):
    """Una base de una versión anterior (sin las columnas de revisión) se actualiza sola al arrancar."""
    url = f"sqlite:///{tmp_path / 'vieja.db'}"
    sesiones = crear_sesiones(url)
    with sesiones() as db:
        for col in ("revision", "revisado_por", "revisado_en", "nota_revision"):
            db.execute(text("DROP INDEX IF EXISTS ix_hallazgos_revision"))
            db.execute(text(f"ALTER TABLE hallazgos DROP COLUMN {col}"))
        db.commit()
    with crear_sesiones(url)() as db:
        columnas = {fila[1] for fila in db.execute(text("PRAGMA table_info(hallazgos)"))}
    assert {"revision", "revisado_por", "revisado_en", "nota_revision"} <= columnas
