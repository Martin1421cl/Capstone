"""RNF-18: un escaneo largo no bloquea al resto de los usuarios.

El escaneo de archivos subidos corre en un hilo aparte: mientras dura, el servidor sigue respondiendo.
"""

import threading
import time

from fastapi.testclient import TestClient

from ksecure.web.api import escanear as api_escanear
from ksecure.web.app import create_app
from tests.conftest import ADMIN, CLAVE_AUDITOR

DURACION = 1.5  # segundos que tarda el escaneo simulado


def test_un_escaneo_largo_no_bloquea_a_los_demas(tmp_path, monkeypatch):
    original = api_escanear.escanear_archivos

    def escaneo_lento(*args, **kwargs):
        time.sleep(DURACION)  # trabajo pesado que no suelta el hilo, como validar miles de celdas
        return original(*args, **kwargs)

    monkeypatch.setattr(api_escanear, "escanear_archivos", escaneo_lento)

    app = create_app(f"sqlite:///{tmp_path / 'ksecure.db'}")
    # "with": todas las peticiones comparten el mismo servidor (event loop), como en producción.
    with TestClient(app) as cliente:
        assert cliente.post("/api/sesion/configurar", json=ADMIN).status_code == 201
        assert cliente.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201

        respuesta = {}
        escaneo = threading.Thread(target=lambda: respuesta.update(r=cliente.post(
            "/api/archivos", files=[("archivos", ("datos.txt", b"RUT 12.345.678-5"))])))
        escaneo.start()
        time.sleep(0.3)  # el escaneo ya empezó

        inicio = time.perf_counter()
        otra = cliente.get("/api/escaneos")  # otro usuario mira el historial
        espera = time.perf_counter() - inicio

        escaneo.join()
        assert otra.status_code == 200
        assert espera < DURACION / 2, f"la petición esperó {espera:.2f} s al escaneo"
        assert respuesta["r"].status_code == 200
        assert len(cliente.get("/api/escaneos").json()) == 1
