"""El cliente simulado (demo/cliente_simulado.py) genera datos válidos y K-Secure encuentra lo que debe."""

import importlib.util
from pathlib import Path

import pytest

from ksecure.escaneo.bases_datos import DatosConexion, conectar, escanear_bd
from ksecure.validators.rut import calcular_dv
from ksecure.validators.tarjeta import luhn

_RUTA = Path(__file__).resolve().parents[1] / "demo" / "cliente_simulado.py"
_spec = importlib.util.spec_from_file_location("cliente_simulado", _RUTA)
cliente_simulado = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cliente_simulado)


@pytest.fixture(scope="module")
def tablas():
    return {t.nombre: t for t in cliente_simulado.generar(escala=0.1)}


def _columna(tabla, nombre):
    i = [c for c, _ in tabla.columnas].index(nombre)
    return [f[i] for f in tabla.filas if f[i] is not None]


def test_siempre_genera_lo_mismo():
    a = cliente_simulado.generar(escala=0.05)
    b = cliente_simulado.generar(escala=0.05)
    assert [t.filas for t in a] == [t.filas for t in b]


def test_datos_con_forma_real(tablas):
    # Todos los RUT tienen el dígito verificador correcto (Módulo 11).
    for rut in _columna(tablas["cli_maestro"], "id_tri") + _columna(tablas["rh_pers"], "run"):
        cuerpo, dv = rut.replace(".", "").split("-")
        assert calcular_dv(int(cuerpo)) == dv
    # Las tarjetas pasan Luhn; las transferencias no son tarjetas.
    for ref in _columna(tablas["fi_pagos"], "ref_pago"):
        if not ref.startswith("TRF-"):
            assert luhn(ref.replace(" ", "").replace("-", ""))
    # Las llaves primarias no se repiten.
    for t in tablas.values():
        i = [c for c, _ in t.columnas].index(t.llave)
        assert len({f[i] for f in t.filas}) == len(t.filas), t.nombre


def test_k_secure_encuentra_lo_sensible_y_respeta_las_trampas(tablas, tmp_path):
    ruta = tmp_path / "cliente_simulado.db"
    cliente_simulado.cargar_sqlite(list(tablas.values()), str(ruta))
    resultado = escanear_bd(conectar(DatosConexion(motor="sqlite", ruta=str(ruta))), "simulado", max_filas=100_000)
    tipos = {}
    for h in resultado.hallazgos:
        tipos.setdefault(f"{h.fuente}.{h.columna}", set()).add(h.match.type)

    esperado = {
        "cli_maestro.id_tri": "RUT", "cli_maestro.fon_1": "TELEFONO", "cli_maestro.eml_1": "EMAIL",
        "rh_pers.run": "RUT", "rh_pers.nro_cta": "CUENTA_BANCARIA", "rh_pers.mail_pers": "EMAIL",
        "fi_pagos.ref_pago": "TARJETA_PAGO", "vt_docs.rut_rec": "RUT", "prov_maestro.cta_cte": "CUENTA_BANCARIA",
        "flota.ppu": "PATENTE", "sys_integraciones.credencial": "SECRETO",
    }
    for columna, tipo in esperado.items():
        assert tipo in tipos.get(columna, set()), columna

    # Trampas: números con forma parecida que no son datos personales.
    for trampa in ("vt_docs.folio", "fi_pagos.cod_aut", "inv_productos.cod_barras", "flota.nro_motor",
                   "log_accesos.ip_origen", "vt_docs.total"):
        assert trampa not in tipos, trampa
