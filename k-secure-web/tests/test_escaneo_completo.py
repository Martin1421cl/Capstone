"""Escaneo de bases de datos completo y más rápido.

Por defecto K-Secure revisa todas las tablas y todas sus filas (antes, 1.000 por tabla), y los
valores que se repiten en una columna se validan una sola vez sin cambiar el resultado.
"""

import sqlite3

import pytest

from ksecure.escaneo.bases_datos import DatosConexion, conectar, escanear_bd
from ksecure.escaneo.celdas import escanear_filas
from ksecure.escaneo.resultado import ResultadoEscaneo
from ksecure.validators import default_validators
from ksecure.validators.base import find_keywords, normalize
from ksecure.validators.rut import calcular_dv

FILAS = 2500  # más que el antiguo tope de 1.000


def _rut(cuerpo: int) -> str:
    return f"{cuerpo}-{calcular_dv(cuerpo)}"


@pytest.fixture
def base(tmp_path):
    ruta = tmp_path / "grande.db"
    with sqlite3.connect(ruta) as cx:
        cx.execute("CREATE TABLE clientes (id INTEGER PRIMARY KEY, rut_cliente TEXT, estado TEXT)")
        cx.execute("CREATE TABLE proveedores (id INTEGER PRIMARY KEY, rut_proveedor TEXT)")
        cx.executemany("INSERT INTO clientes VALUES (?, ?, ?)",
                       [(i, _rut(10_000_000 + i), "activo") for i in range(1, FILAS + 1)])
        cx.executemany("INSERT INTO proveedores VALUES (?, ?)", [(i, _rut(20_000_000 + i)) for i in range(1, 51)])
    return conectar(DatosConexion(motor="sqlite", ruta=str(ruta)))


def test_por_defecto_revisa_todas_las_tablas_y_todas_las_filas(base):
    r = escanear_bd(base, "cliente")
    assert r.filas_por_fuente == {"clientes": FILAS, "proveedores": 50}
    assert sum(h.match.type == "RUT" for h in r.hallazgos) == FILAS + 50
    assert not r.errores


def test_el_motor_admite_un_tope_para_las_pruebas_internas(base):
    """La web no lo ofrece; solo lo usan las pruebas de lectura determinista (HU-27)."""
    r = escanear_bd(base, "cliente", max_filas=100, tablas=["clientes"])
    assert r.filas_por_fuente == {"clientes": 100}


def test_un_valor_repetido_cuenta_en_cada_fila():
    """Validar una vez cada valor repetido no puede saltarse filas: cada una conserva su hallazgo."""
    filas = [(f"fila id={i}", {"rut_socio": "12.345.678-5", "comuna": "Santiago"}) for i in range(1, 6)]
    r = ResultadoEscaneo("bd", "prueba")
    escanear_filas(r, "socios", filas, default_validators())
    assert [h.posicion for h in r.hallazgos] == [f"fila id={i}" for i in range(1, 6)]
    assert {h.match.text for h in r.hallazgos} == {"12.345.678-5"}


def test_mismo_valor_en_otra_columna_se_valida_con_su_propio_contexto():
    """El nombre de la columna cambia la confianza: la memoria de valores es por columna."""
    r = ResultadoEscaneo("bd", "prueba")
    escanear_filas(r, "t", [("fila 1", {"rut_cliente": "12.345.678-5", "folio": "12.345.678-5"})], default_validators())
    confianza = {h.columna: h.match.confidence for h in r.hallazgos if h.match.type == "RUT"}
    assert confianza.get("rut_cliente", 0) > confianza.get("folio", 0)


def test_palabras_clave_con_y_sin_tildes():
    assert normalize("Cédula") == "cedula" and normalize("RUT") == "rut"
    assert find_keywords("numero de cédula", ("cedula",)) == ["cedula"]
    assert find_keywords("Ruta 5 sur", ("rut",)) == []


def test_la_web_siempre_revisa_la_tabla_completa(admin, base, monkeypatch):
    """La pantalla ya no ofrece un tope de filas, y aunque alguien lo mande a mano, la API lo ignora."""
    from ksecure.web.api import escanear as api_escanear
    from tests.conftest import CLAVE_AUDITOR

    monkeypatch.setattr(api_escanear, "_conectar", lambda conexion: base)
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    conexion = {"motor": "postgresql", "host": "db.ejemplo.cl", "base": "cliente", "usuario": "lector", "clave": "x"}
    r = admin.post("/api/bd/escanear", json={"conexion": conexion, "tablas": ["clientes"], "max_filas": 100})
    assert r.status_code == 200, r.text
    hallazgos = admin.get(f"/api/escaneos/{r.json()['escaneo_id']}/hallazgos").json()["total"]
    assert hallazgos == FILAS  # un RUT por fila: se revisaron las 2.500, no 100


MUESTRAS = [
    "12.345.678-5", "12345678-5", "7.654.321-K", "+56 9 1234 5678", "912345678", "(2) 2345 6789",
    "4111 1111 1111 1111", "4111111111111111", "00-123-45678-9", "123456789", "BB·CL·12", "AB1234",
    "juan.perez@correo.cl", "contacto@empresa.cl", "AKIAIOSFODNN7EXAMPLE", "aws_secret_access_key=" + "a" * 40,
    "ghp_" + "A" * 36, "-----BEGIN RSA PRIVATE KEY-----", "Santiago", "activo", "2026-03-01", "1500000",
    "Paciente con RUT 12.345.678-5 y celular 9 8765 4321", "Ficha ٣٤٥", "", "—",
]


@pytest.mark.parametrize("columna", ["rut_cliente", "obs", "cta_cte", "notas"])
def test_los_filtros_rapidos_no_cambian_lo_que_se_encuentra(columna):
    """Saltarse validadores que no pueden encontrar nada da exactamente los mismos hallazgos."""
    validadores = default_validators()
    for texto in MUESTRAS:
        sin_filtro = [(m.type, m.text, m.confidence) for v in validadores
                      for m in v.validate_content(texto, "t", context_hint=columna)]
        r = ResultadoEscaneo("bd", "prueba")
        escanear_filas(r, "t", [("fila 1", {columna: texto})], validadores)
        assert [(h.match.type, h.match.text, h.match.confidence) for h in r.hallazgos] == sin_filtro, texto
