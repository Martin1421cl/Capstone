"""HU-17 (RF-18): comparar dos escaneos de la misma fuente para ver si los datos sensibles aumentaron o disminuyeron."""

import pytest

from ksecure.validators.rut import calcular_dv
from tests.conftest import CLAVE_AUDITOR, cuenta


def _rut(cuerpo: int) -> str:
    return f"{cuerpo}-{calcular_dv(cuerpo)}"


RUTS = [_rut(10_000_000 + i * 7919) for i in range(12)]
# Cada correo empieza distinto: la máscara deja ver las 2 primeras letras (ver la limitación en comparar()).
CORREOS = [f"{'abcdefghijkl'[i]}{i}.persona@correo.cl" for i in range(12)]


def _csv(filas: list[int], con_celular: bool = False) -> bytes:
    encabezado = "id;rut;correo" + (";celular" if con_celular else "")
    lineas = [encabezado]
    for i in filas:
        linea = f"{i};{RUTS[i]};{CORREOS[i]}"
        if con_celular:
            linea += f";+56 9 {8000 + i} {1000 + i}"
        lineas.append(linea)
    return "\n".join(lineas).encode()


def _escanear(cliente, contenido: bytes, nombre: str = "clientes.csv") -> int:
    r = cliente.post("/api/archivos", files=[("archivos", (nombre, contenido))])
    assert r.status_code == 200, r.text
    return r.json()["escaneo_id"]


@pytest.fixture
def escaneos(admin):
    """Primer escaneo: filas 0 a 9. Segundo: se borró la fila 9, entró la 10 y se agregó la columna celular."""
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    antes = _escanear(admin, _csv(list(range(10))))
    despues = _escanear(admin, _csv(list(range(9)) + [10], con_celular=True))
    return antes, despues


def _fila(lista, clave):
    return next(x for x in lista if x["clave"] == clave)


def test_resume_lo_que_aumento_y_disminuyo(admin, escaneos):
    antes, despues = escaneos
    c = admin.get(f"/api/escaneos/{antes}/comparar/{despues}").json()

    assert c["misma_fuente"] is True
    assert c["anterior"]["id"] == antes and c["actual"]["id"] == despues
    assert c["total"] == {"anterior": 20, "actual": 30, "diferencia": 10}
    assert _fila(c["por_tipo"], "RUT") == {"clave": "RUT", "anterior": 10, "actual": 10, "diferencia": 0}
    assert _fila(c["por_tipo"], "TELEFONO")["diferencia"] == 10
    assert sum(r["diferencia"] for r in c["por_riesgo"]) == 10


def test_hallazgos_nuevos_resueltos_y_sin_cambios(admin, escaneos):
    antes, despues = escaneos
    c = admin.get(f"/api/escaneos/{antes}/comparar/{despues}").json()

    # Nuevos: la fila 10 (RUT y correo) y los 10 celulares. Resueltos: la fila 9 que se borró (RUT y correo).
    assert c["nuevos"]["total"] == 12
    assert c["resueltos"]["total"] == 2
    assert c["sin_cambios"] == 18
    assert {h["posicion"] for h in c["resueltos"]["muestra"]} == {"fila 11"}  # fila 1 es el encabezado


def test_columnas_nuevas_y_que_siguen(admin, escaneos):
    antes, despues = escaneos
    columnas = {x["columna"]: x for x in admin.get(f"/api/escaneos/{antes}/comparar/{despues}").json()["columnas"]}
    assert columnas["celular"]["estado"] == "nueva" and columnas["celular"]["anterior"] is None
    assert columnas["rut"]["estado"] == "sigue" and columnas["rut"]["actual"] == 100


def test_el_orden_de_los_ids_no_importa(admin, escaneos):
    antes, despues = escaneos
    al_reves = admin.get(f"/api/escaneos/{despues}/comparar/{antes}").json()
    assert al_reves["anterior"]["id"] == antes and al_reves["total"]["diferencia"] == 10


def test_todo_va_enmascarado(admin, escaneos):
    antes, despues = escaneos
    texto = admin.get(f"/api/escaneos/{antes}/comparar/{despues}").text
    for dato in RUTS + CORREOS:
        assert dato not in texto


def test_avisa_si_no_son_de_la_misma_fuente(admin, escaneos):
    antes, _ = escaneos
    otro = _escanear(admin, _csv([0, 1]), nombre="proveedores.csv")
    assert admin.get(f"/api/escaneos/{antes}/comparar/{otro}").json()["misma_fuente"] is False


def test_errores_claros(admin, escaneos):
    antes, _ = escaneos
    assert admin.get(f"/api/escaneos/{antes}/comparar/{antes}").status_code == 400
    assert admin.get(f"/api/escaneos/{antes}/comparar/9999").status_code == 404


def test_un_visor_puede_comparar(admin, escaneos):
    antes, despues = escaneos
    visor = cuenta(admin, "vicente", "Visor")
    assert visor.get(f"/api/escaneos/{antes}/comparar/{despues}").status_code == 200


def test_sin_sesion_no_se_puede(admin, escaneos):
    from fastapi.testclient import TestClient

    antes, despues = escaneos
    assert TestClient(admin.app).get(f"/api/escaneos/{antes}/comparar/{despues}").status_code == 401
