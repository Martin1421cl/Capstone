"""HU-27 / RNF-08: el mismo escaneo de una base da siempre el mismo resultado.

Con un límite de filas menor al tamaño de la tabla, K-Secure debe leer siempre las mismas filas:
ordena por la llave primaria o, si la tabla no tiene, por todas sus columnas.
"""

import sqlite3

import pytest

from ksecure.escaneo import bases_datos
from ksecure.escaneo.bases_datos import DatosConexion, conectar, escanear_bd
from ksecure.validators.rut import calcular_dv


def _rut(cuerpo: int) -> str:
    return f"{cuerpo}-{calcular_dv(cuerpo)}"


CUERPOS = [11111111 + i * 1234567 for i in range(10)]


@pytest.fixture
def base(tmp_path):
    """Tabla con llave primaria de texto y tabla sin llave, ambas cargadas en orden inverso."""
    ruta = tmp_path / "cliente.db"
    with sqlite3.connect(ruta) as cx:
        cx.execute("CREATE TABLE clientes (codigo TEXT PRIMARY KEY, rut_cliente TEXT)")
        cx.execute("CREATE TABLE sin_llave (rut_proveedor TEXT, nombre TEXT)")
        for i, cuerpo in reversed(list(enumerate(CUERPOS))):
            cx.execute("INSERT INTO clientes VALUES (?, ?)", (f"C{i:02d}", _rut(cuerpo)))
            cx.execute("INSERT INTO sin_llave VALUES (?, ?)", (_rut(cuerpo), f"Proveedor {i}"))
    return conectar(DatosConexion(motor="sqlite", ruta=str(ruta)))


def _posiciones(resultado, tabla):
    return sorted(h.posicion for h in resultado.hallazgos if h.fuente == tabla and h.match.type == "RUT")


def test_lee_las_primeras_filas_segun_la_llave_primaria(base):
    r = escanear_bd(base, "cliente", max_filas=3, tablas=["clientes"])
    assert _posiciones(r, "clientes") == ["fila codigo=C00", "fila codigo=C01", "fila codigo=C02"]


def test_mismo_escaneo_mismo_resultado(base):
    a = escanear_bd(base, "cliente", max_filas=4)
    b = escanear_bd(base, "cliente", max_filas=4)
    clave = lambda r: [(h.fuente, h.posicion, h.columna, h.match.text) for h in r.hallazgos]  # noqa: E731
    assert clave(a) == clave(b)
    assert len(a.hallazgos) > 0


def test_tabla_sin_llave_se_ordena_por_sus_columnas(base):
    r = escanear_bd(base, "cliente", max_filas=3, tablas=["sin_llave"])
    leidos = sorted(h.match.text for h in r.hallazgos if h.match.type == "RUT")
    assert leidos == sorted(_rut(c) for c in CUERPOS)[:3]
    assert not r.errores


def test_la_consulta_lleva_order_by(base):
    from sqlalchemy import MetaData, Table

    tabla = Table("clientes", MetaData(), autoload_with=base)
    sql = str(bases_datos._consulta(tabla, ["codigo"], 10))
    assert "ORDER BY clientes.codigo" in sql


def test_si_el_motor_no_puede_ordenar_lee_igual_y_avisa(base, monkeypatch):
    original = bases_datos._consulta

    def sin_orden_posible(tabla, clave, max_filas, ordenar=True):
        if ordenar:
            raise RuntimeError("tipo de dato no ordenable")
        return original(tabla, clave, max_filas, ordenar=False)

    monkeypatch.setattr(bases_datos, "_consulta", sin_orden_posible)
    r = escanear_bd(base, "cliente", max_filas=100, tablas=["sin_llave"])
    assert len(_posiciones(r, "sin_llave")) == len(CUERPOS)
    assert any("sin llave primaria ordenable" in e for e in r.errores)
