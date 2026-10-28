"""¿Olvidaste tu contraseña? Código de 6 dígitos al correo (RF-14)."""

import json
import re
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from ksecure.almacenamiento import usuarios
from ksecure.almacenamiento.modelos import CodigoRecuperacion, Usuario
from ksecure.correo import Correo, ErrorCorreo
from ksecure.web.app import create_app
from tests.conftest import cuenta


class CorreoFalso:
    """Guarda los correos en vez de mandarlos."""
    configurado = True

    def __init__(self, error: str | None = None):
        self.enviados, self.error = [], error

    def enviar(self, para, asunto, texto, html_=None):
        if self.error:
            raise ErrorCorreo(self.error)
        self.enviados.append({"para": para, "asunto": asunto, "texto": texto, "html": html_})

    def codigo(self) -> str:
        return re.search(r"\b\d{6}\b", self.enviados[-1]["texto"]).group()


@pytest.fixture
def correo(admin) -> CorreoFalso:
    admin.app.state.correo = CorreoFalso()
    return admin.app.state.correo


def pedir(app, cuenta_):
    return TestClient(app).post("/api/sesion/recuperar", json={"cuenta": cuenta_})


def confirmar(app, cuenta_, codigo, clave="clave-recuperada-1"):
    c = TestClient(app)
    return c, c.post("/api/sesion/recuperar/confirmar", json={"cuenta": cuenta_, "codigo": codigo, "clave": clave})


def db(c):
    return c.app.state.sesiones()


def atrasar_codigos(c, tiempo):
    with db(c) as s:
        for cod in s.scalars(select(CodigoRecuperacion)):
            cod.creado -= tiempo
            cod.expira -= tiempo
        s.commit()


# --- El camino feliz -----------------------------------------------------------------------------

def test_recuperar_con_el_codigo_del_correo(admin, correo):
    vale = cuenta(admin, "vale", "Visor")
    r = pedir(admin.app, "vale")
    assert r.status_code == 202 and r.json()["minutos"] == 10
    assert len(correo.enviados) == 1
    enviado = correo.enviados[0]
    assert enviado["para"] == "vale@empresa.cl"
    assert correo.codigo() not in enviado["asunto"]  # no se ve en la pantalla bloqueada
    assert correo.codigo() in enviado["html"]

    _, malo = confirmar(admin.app, "vale", "000000" if correo.codigo() != "000000" else "111111")
    assert malo.status_code == 400 and malo.json()["detail"] == usuarios.CODIGO_INVALIDO

    nuevo, ok = confirmar(admin.app, "vale", correo.codigo())
    assert ok.status_code == 200 and ok.json()["usuario"]["usuario"] == "vale"
    assert nuevo.get("/api/escaneos").status_code == 200       # queda con la sesión iniciada
    assert vale.get("/api/escaneos").status_code == 401        # la sesión vieja se cerró
    _, otra = confirmar(admin.app, "vale", correo.codigo(), "otra-clave-nueva")
    assert otra.status_code == 400                             # el código sirve una sola vez
    ingreso = TestClient(admin.app).post("/api/sesion/ingresar", json={"usuario": "vale", "clave": "clave-recuperada-1"})
    assert ingreso.status_code == 200


def test_sirve_el_correo_en_vez_del_usuario_y_con_espacios_en_el_codigo(admin, correo):
    cuenta(admin, "vale", "Visor")
    assert pedir(admin.app, "  VALE@Empresa.cl ").status_code == 202
    codigo = correo.codigo()
    _, r = confirmar(admin.app, "vale@empresa.cl", f"{codigo[:3]} {codigo[3:]}")
    assert r.status_code == 200


def test_desbloquea_la_cuenta_y_quita_la_clave_temporal(admin, correo):
    r = admin.post("/api/usuarios", json={"usuario": "rodrigo", "nombre": "Rodrigo", "correo": "ro@empresa.cl", "rol": "Auditor"})
    assert r.status_code == 201
    for _ in range(usuarios.MAX_INTENTOS):
        TestClient(admin.app).post("/api/sesion/ingresar", json={"usuario": "rodrigo", "clave": "mala-clave-123"})
    with db(admin) as s:
        u = s.scalar(select(Usuario).where(Usuario.usuario == "rodrigo"))
        assert u.bloqueado_hasta is not None and u.debe_cambiar_clave
    pedir(admin.app, "rodrigo")
    nuevo, ok = confirmar(admin.app, "rodrigo", correo.codigo())
    assert ok.status_code == 200
    assert ok.json()["usuario"]["debe_cambiar_clave"] is False and ok.json()["usuario"]["bloqueado"] is False
    assert nuevo.get("/api/escaneos").status_code == 200  # ya no pide cambiar la clave (428)


# --- No delata cuentas ---------------------------------------------------------------------------

def test_responde_igual_aunque_la_cuenta_no_exista(admin, correo):
    cuenta(admin, "vale", "Visor")
    otra = cuenta(admin, "pedro", "Visor")
    pedro = next(u for u in admin.get("/api/usuarios").json() if u["usuario"] == "pedro")
    assert admin.put(f"/api/usuarios/{pedro['id']}", json={**pedro, "activo": False}).status_code == 200

    respuestas = [pedir(admin.app, c) for c in ("vale", "no-existe", "nadie@empresa.cl", "pedro", "")]
    assert {r.status_code for r in respuestas} == {202}
    assert len({r.text for r in respuestas}) == 1
    assert [e["para"] for e in correo.enviados] == ["vale@empresa.cl"]  # ni a la inexistente ni a la desactivada

    _, r = confirmar(admin.app, "no-existe", "123456")
    assert r.status_code == 400 and r.json()["detail"] == usuarios.CODIGO_INVALIDO
    assert otra.get("/api/escaneos").status_code == 401


def test_cuenta_sin_correo_no_recibe_codigo():
    """El administrador inicial que sale de KSECURE_ACCESO todavía no registra su correo."""
    falso = CorreoFalso()
    app = create_app("sqlite://", acceso="jefe:temporal-12345", correo=falso)
    assert pedir(app, "jefe").status_code == 202
    assert falso.enviados == []


# --- Límites ---------------------------------------------------------------------------------------

def test_el_codigo_vence_a_los_10_minutos(admin, correo):
    cuenta(admin, "vale", "Visor")
    pedir(admin.app, "vale")
    atrasar_codigos(admin, timedelta(minutes=11))
    _, r = confirmar(admin.app, "vale", correo.codigo())
    assert r.status_code == 400


def test_cinco_intentos_fallidos_anulan_el_codigo(admin, correo):
    cuenta(admin, "vale", "Visor")
    pedir(admin.app, "vale")
    malo = f"{(int(correo.codigo()) + 1) % 10**6:06d}"
    for _ in range(usuarios.CODIGO_INTENTOS):
        assert confirmar(admin.app, "vale", malo)[1].status_code == 400
    assert confirmar(admin.app, "vale", correo.codigo())[1].status_code == 400


def test_una_clave_invalida_no_gasta_el_codigo(admin, correo):
    cuenta(admin, "vale", "Visor")
    pedir(admin.app, "vale")
    _, corta = confirmar(admin.app, "vale", correo.codigo(), "corta")
    assert corta.status_code == 400 and "al menos" in corta.json()["detail"]
    _, igual = confirmar(admin.app, "vale", correo.codigo(), "VALE")
    assert igual.status_code == 400
    assert confirmar(admin.app, "vale", correo.codigo())[1].status_code == 200


def test_espera_un_minuto_entre_codigos_y_el_nuevo_anula_el_anterior(admin, correo):
    cuenta(admin, "vale", "Visor")
    pedir(admin.app, "vale")
    pedir(admin.app, "vale")
    assert len(correo.enviados) == 1  # el segundo pedido llegó antes del minuto
    primero = correo.codigo()
    atrasar_codigos(admin, timedelta(seconds=61))
    pedir(admin.app, "vale")
    assert len(correo.enviados) == 2
    if correo.codigo() != primero:
        assert confirmar(admin.app, "vale", primero)[1].status_code == 400
    assert confirmar(admin.app, "vale", correo.codigo())[1].status_code == 200


def test_maximo_cinco_codigos_por_hora(admin, correo):
    cuenta(admin, "vale", "Visor")
    for _ in range(usuarios.CODIGOS_POR_HORA + 2):
        pedir(admin.app, "vale")
        atrasar_codigos(admin, timedelta(seconds=61))
    assert len(correo.enviados) == usuarios.CODIGOS_POR_HORA


def test_el_codigo_se_guarda_con_hash(admin, correo):
    cuenta(admin, "vale", "Visor")
    pedir(admin.app, "vale")
    with db(admin) as s:
        guardado = s.scalars(select(CodigoRecuperacion)).one()
    assert correo.codigo() not in guardado.codigo_hash and guardado.codigo_hash.startswith("$2")


def test_si_el_correo_falla_la_web_no_se_cae(admin, caplog):
    admin.app.state.correo = CorreoFalso(error="Clave incorrecta")
    cuenta(admin, "vale", "Visor")
    assert pedir(admin.app, "vale").status_code == 202
    assert "Clave incorrecta" in caplog.text and "@vale" in caplog.text


# --- Envío -----------------------------------------------------------------------------------------

def test_sin_configurar_el_codigo_se_escribe_en_la_terminal(admin, capsys):
    assert not admin.app.state.correo.configurado  # las pruebas no tienen KSECURE_CORREO_*
    cuenta(admin, "vale", "Visor")
    pedir(admin.app, "vale")
    salida = capsys.readouterr().out
    assert "Correo sin configurar" in salida and "vale@empresa.cl" in salida
    assert re.search(r"\b\d{6}\b", salida)


class AppsScriptFalso(BaseHTTPRequestHandler):
    """Se porta como Google: el POST responde 302 y la respuesta queda en otra URL (GET)."""
    recibido: dict = {}
    respuesta = b'{"ok": true, "quedan": 97}'

    def do_POST(self):
        type(self).recibido = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(302)
        self.send_header("Location", "/echo")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(type(self).respuesta)

    def log_message(self, *args):
        pass


@pytest.fixture
def apps_script(monkeypatch):
    for variable in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(variable, raising=False)
    servidor = HTTPServer(("127.0.0.1", 0), AppsScriptFalso)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_port}/exec"
    servidor.shutdown()


def test_envio_por_apps_script_sigue_la_redireccion(apps_script):
    Correo(apps_script, "secreto-de-prueba").enviar("a@b.cl", "Asunto", "Texto", "<p>Texto</p>")
    assert AppsScriptFalso.recibido == {"secreto": "secreto-de-prueba", "para": "a@b.cl", "asunto": "Asunto",
                                        "texto": "Texto", "html": "<p>Texto</p>"}


@pytest.mark.parametrize("respuesta, mensaje", [
    (b'{"ok": false, "error": "Clave incorrecta"}', "Clave incorrecta"),
    (b"<html>Inicia sesion en Google</html>", "Cualquier usuario"),
])
def test_errores_del_apps_script(apps_script, monkeypatch, respuesta, mensaje):
    monkeypatch.setattr(AppsScriptFalso, "respuesta", respuesta)
    with pytest.raises(ErrorCorreo, match=mensaje) as e:
        Correo(apps_script, "secreto-de-prueba").enviar("a@b.cl", "Asunto", "Texto")
    assert "secreto-de-prueba" not in str(e.value)


def test_sin_conexion_avisa_sin_mostrar_el_secreto():
    with pytest.raises(ErrorCorreo, match="No se pudo contactar") as e:
        Correo("http://127.0.0.1:9/exec", "secreto-de-prueba", espera=2).enviar("a@b.cl", "A", "T")
    assert "secreto-de-prueba" not in str(e.value)


def test_correo_de_prueba_solo_admin(admin, correo):
    visor = cuenta(admin, "vale", "Visor")
    assert visor.post("/api/usuarios/correo-prueba").status_code == 403
    r = admin.post("/api/usuarios/correo-prueba")
    assert r.status_code == 200 and r.json()["para"] == "ana@empresa.cl"
    assert correo.enviados[-1]["para"] == "ana@empresa.cl"
    admin.app.state.correo = CorreoFalso(error="Clave incorrecta")
    r = admin.post("/api/usuarios/correo-prueba")
    assert r.status_code == 502 and "Clave incorrecta" in r.json()["detail"]
