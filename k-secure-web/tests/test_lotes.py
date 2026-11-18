"""HU-29: los hallazgos se guardan por lotes mientras se escanea, sin juntarlos todos en memoria (RNF-14)."""

import pytest
from sqlalchemy import func, select

from ksecure.almacenamiento import boveda, repositorio
from ksecure.almacenamiento.db import crear_sesiones
from ksecure.almacenamiento.modelos import Escaneo, Hallazgo
from ksecure.escaneo import resultado as modulo_resultado
from ksecure.escaneo.archivos import escanear_archivos
from ksecure.escaneo.bases_datos import DatosConexion, conectar, escanear_bd
from ksecure.escaneo.resultado import ErrorAlGuardar, ResultadoEscaneo
from ksecure.validators.rut import calcular_dv
from tests.conftest import CLAVE_AUDITOR

FILAS = 120  # cada fila tiene un RUT y un correo: 240 hallazgos


def _rut(cuerpo: int) -> str:
    return f"{cuerpo}-{calcular_dv(cuerpo)}"


@pytest.fixture
def csv(tmp_path):
    ruta = tmp_path / "clientes.csv"
    lineas = ["id;rut;correo"] + [f"{i};{_rut(10_000_000 + i * 7919)};persona{i}@correo.cl" for i in range(FILAS)]
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return str(ruta)


@pytest.fixture
def db():
    sesiones = crear_sesiones("sqlite://")
    with sesiones() as s:
        boveda.configurar(s, CLAVE_AUDITOR)
        yield s


@pytest.fixture
def lote_chico(monkeypatch):
    monkeypatch.setattr(modulo_resultado, "LOTE", 25)


def _guardados(db, escaneo_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Hallazgo).where(Hallazgo.escaneo_id == escaneo_id))


def test_la_memoria_nunca_junta_mas_de_un_lote(csv, lote_chico):
    tamanos = []
    r = ResultadoEscaneo("archivo", "clientes.csv", al_lote=lambda lote: tamanos.append(len(lote)))
    escanear_archivos([(csv, "clientes.csv")], resultado=r)
    assert r.total == FILAS * 2
    assert sum(tamanos) == r.total
    assert max(tamanos) <= 25
    assert r.hallazgos == []  # todo se entregó a la base


def test_sin_lotes_funciona_igual_que_antes(csv):
    r = escanear_archivos([(csv, "clientes.csv")])
    assert len(r.hallazgos) == r.total == FILAS * 2


def test_guardado_por_lotes_queda_completo_y_cifrado(db, csv, lote_chico):
    guardado = repositorio.Guardado(db, "archivo", "clientes.csv")
    r = ResultadoEscaneo("archivo", "clientes.csv", al_lote=guardado.agregar)
    escanear_archivos([(csv, "clientes.csv")], resultado=r)
    escaneo = guardado.terminar(r)

    assert _guardados(db, escaneo.id) == FILAS * 2
    assert escaneo.estado is None and escaneo.filas_por_fuente == {"clientes.csv": FILAS}
    h = db.scalar(select(Hallazgo).where(Hallazgo.escaneo_id == escaneo.id, Hallazgo.tipo == "RUT").limit(1))
    assert boveda.revelar(db, CLAVE_AUDITOR, escaneo.llave_cifrada, h.valor_cifrado).endswith(h.valor_enmascarado[-3:])
    assert repositorio.detalle(db, escaneo.id)["total"] == FILAS * 2


def test_escaneo_en_curso_no_aparece_en_el_historial(db, csv, lote_chico):
    guardado = repositorio.Guardado(db, "archivo", "clientes.csv")
    r = ResultadoEscaneo("archivo", "clientes.csv", al_lote=guardado.agregar)
    escanear_archivos([(csv, "clientes.csv")], resultado=r)
    assert _guardados(db, guardado.escaneo.id) > 0  # ya hay lotes en la base...
    assert repositorio.listar(db) == []               # ...pero todavía no se muestra
    guardado.terminar(r)
    assert [e["id"] for e in repositorio.listar(db)] == [guardado.escaneo.id]


def test_si_el_escaneo_falla_no_queda_a_medias(db, csv, lote_chico):
    guardado = repositorio.Guardado(db, "archivo", "clientes.csv")
    r = ResultadoEscaneo("archivo", "clientes.csv", al_lote=guardado.agregar)
    escanear_archivos([(csv, "clientes.csv")], resultado=r)
    guardado.cancelar()
    assert db.scalar(select(func.count()).select_from(Escaneo)) == 0
    assert db.scalar(select(func.count()).select_from(Hallazgo)) == 0


def test_un_error_de_la_base_interna_detiene_el_escaneo_de_tablas(tmp_path, csv, lote_chico):
    """Un problema al guardar no se confunde con el error de una tabla del cliente."""
    import sqlite3

    ruta = tmp_path / "cliente.db"
    with sqlite3.connect(ruta) as cx:
        cx.execute("CREATE TABLE clientes (id INTEGER PRIMARY KEY, rut TEXT)")
        cx.executemany("INSERT INTO clientes VALUES (?, ?)", [(i, _rut(10_000_000 + i * 7919)) for i in range(60)])

    def falla(_lote):
        raise ErrorAlGuardar("disco lleno")

    r = ResultadoEscaneo("bd", "cliente", al_lote=falla)
    with pytest.raises(ErrorAlGuardar):
        escanear_bd(conectar(DatosConexion(motor="sqlite", ruta=str(ruta))), "cliente", resultado=r)


def test_api_guarda_por_lotes_un_archivo_grande(admin, lote_chico):
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    lineas = ["id;rut;correo"] + [f"{i};{_rut(10_000_000 + i * 7919)};persona{i}@correo.cl" for i in range(FILAS)]
    r = admin.post("/api/archivos", files=[("archivos", ("clientes.csv", "\n".join(lineas).encode()))])
    assert r.status_code == 200, r.text
    escaneo_id = r.json()["escaneo_id"]
    assert admin.get(f"/api/escaneos/{escaneo_id}").json()["total"] == FILAS * 2
    assert [e["id"] for e in admin.get("/api/escaneos").json()] == [escaneo_id]
    bitacora = admin.get("/api/bitacora").json()
    eventos = bitacora["eventos"] if isinstance(bitacora, dict) else bitacora
    assert any(f"{FILAS * 2} hallazgos" in (e.get("detalle") or "") for e in eventos)
