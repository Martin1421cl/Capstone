"""Login, roles y sesiones (RF-12, RF-13, RNF-12)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from ksecure.almacenamiento import usuarios
from ksecure.almacenamiento.modelos import Sesion, Usuario
from ksecure.web.app import create_app
from ksecure.web.sesion import API_PUBLICA, COOKIE
from tests.conftest import ADMIN, CLAVE_AUDITOR, cuenta


def ingresar(app, usuario, clave):
    c = TestClient(app)
    return c, c.post("/api/sesion/ingresar", json={"usuario": usuario, "clave": clave})


def subir(c, texto=b"RUT 15.432.198-5"):
    return c.post("/api/archivos", files=[("archivos", ("a.txt", texto))])


def db(c):
    return c.app.state.sesiones()


# --- Sin sesión no se ve nada ------------------------------------------------------------------

def test_ninguna_ruta_de_la_api_queda_abierta(admin):
    """Recorre todas las rutas: sin sesión, todas responden 401 salvo las públicas."""
    anonimo = TestClient(admin.app)
    revisadas = 0
    for ruta, metodos in admin.app.openapi()["paths"].items():  # todas las rutas que publica la API
        if ruta in API_PUBLICA:
            continue
        url = ruta.replace("{escaneo_id}", "1").replace("{hallazgo_id}", "1").replace("{regla_id}", "1") \
            .replace("{usuario_id}", "1").replace("{nombre}", "RUT")
        for metodo in metodos:
            assert anonimo.request(metodo.upper(), url).status_code == 401, f"{metodo} {ruta}"
            revisadas += 1
    assert revisadas >= 20


def test_paginas_llevan_al_login_y_recuerdan_a_donde_iba(admin):
    anonimo = TestClient(admin.app)
    r = anonimo.get("/resultados.html?id=3", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login.html?volver=%2Fresultados.html%3Fid%3D3"
    assert anonimo.get("/", follow_redirects=False).headers["location"] == "/login.html"
    assert anonimo.get("/docs", follow_redirects=False).status_code == 303
    assert anonimo.get("/login.html").status_code == 200
    assert anonimo.get("/css/ksecure.css").status_code == 200  # estilos y scripts no piden sesión


# --- Primer administrador ------------------------------------------------------------------------

def test_configurar_solo_la_primera_vez_y_con_datos_validos():
    c = TestClient(create_app("sqlite://"))
    assert c.get("/api/sesion").json() == {"configurado": False, "usuario": None, "largo_minimo": 10, "correo": False}
    malos = [({"clave": "corta"}, "al menos 10"), ({"correo": "sin-arroba"}, "correo no es válido"),
             ({"usuario": "a b"}, "usuario debe tener"), ({"clave": "admin"}, "al menos 10")]
    for cambio, mensaje in malos:
        r = c.post("/api/sesion/configurar", json={**ADMIN, **cambio})
        assert r.status_code == 400 and mensaje in r.json()["detail"]
    assert c.post("/api/sesion/configurar", json=ADMIN).status_code == 201
    assert c.get("/api/sesion").json()["usuario"]["rol"] == "Admin"
    otro = TestClient(c.app)
    assert otro.post("/api/sesion/configurar", json={**ADMIN, "usuario": "otro", "correo": "o@x.cl"}).status_code == 400


# --- Ingresar -------------------------------------------------------------------------------------

def test_ingresar_salir_y_errores(admin):
    app = admin.app
    _, r = ingresar(app, "admin", "mala-clave-123")
    assert r.status_code == 401 and r.json()["detail"] == "Usuario o contraseña incorrectos"
    _, r = ingresar(app, "no-existe", "mala-clave-123")
    assert r.status_code == 401 and r.json()["detail"] == "Usuario o contraseña incorrectos"  # no delata usuarios
    c, r = ingresar(app, "  ADMIN ", ADMIN["clave"])  # sin importar mayúsculas ni espacios
    assert r.status_code == 200 and c.get("/api/escaneos").status_code == 200
    assert c.post("/api/sesion/salir").status_code == 204
    assert c.get("/api/escaneos").status_code == 401


def test_cinco_intentos_bloquean_la_cuenta_y_restablecer_la_desbloquea(admin):
    cuenta(admin, "vera", "Visor")
    for _ in range(4):
        assert ingresar(admin.app, "vera", "mala-clave-123")[1].status_code == 401
    r = ingresar(admin.app, "vera", "mala-clave-123")[1]
    assert r.status_code == 429 and "bloqueada 5 min" in r.json()["detail"]
    assert ingresar(admin.app, "vera", "clave-de-vera")[1].status_code == 429  # ni con la correcta
    vera = next(u for u in admin.get("/api/usuarios").json() if u["usuario"] == "vera")
    assert vera["bloqueado"] is True
    temporal = admin.post(f"/api/usuarios/{vera['id']}/restablecer").json()["clave_temporal"]
    c, r = ingresar(admin.app, "vera", temporal)
    assert r.status_code == 200 and r.json()["usuario"]["debe_cambiar_clave"] is True


def test_contrasenas_y_sesiones_no_se_guardan_en_claro(admin):
    with db(admin) as s:
        u = s.scalar(select(Usuario).where(Usuario.usuario == "admin"))
        assert u.clave_hash.startswith("$2") and ADMIN["clave"] not in u.clave_hash  # bcrypt
        token = admin.cookies[COOKIE]
        assert token not in [x.token_hash for x in s.scalars(select(Sesion))]


def test_cookie_solo_http_y_segura_con_https(admin):
    c = TestClient(admin.app)
    r = c.post("/api/sesion/ingresar", json={"usuario": "admin", "clave": ADMIN["clave"]})
    atributos = [a.strip() for a in r.headers["set-cookie"].lower().split(";")[1:]]
    assert "httponly" in atributos and "samesite=lax" in atributos and "secure" not in atributos
    r = c.post("/api/sesion/ingresar", json={"usuario": "admin", "clave": ADMIN["clave"]},
               headers={"x-forwarded-proto": "https"})  # así llega desde Render
    assert "secure" in [a.strip() for a in r.headers["set-cookie"].lower().split(";")[1:]]


def test_otra_pagina_no_puede_hacer_acciones_con_la_cookie(admin):
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR},
                      headers={"origin": "https://sitio-malicioso.com"}).status_code == 403
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR},
                      headers={"origin": "http://testserver"}).status_code == 201


# --- Vencimiento de la sesión ----------------------------------------------------------------------

@pytest.mark.parametrize("campo, atraso", [("ultimo_uso", timedelta(minutes=31)), ("expira", timedelta(hours=13))])
def test_sesion_vence_por_inactividad_o_a_las_12_horas(admin, campo, atraso):
    with db(admin) as s:
        sesion = s.scalars(select(Sesion)).one()
        setattr(sesion, campo, getattr(sesion, campo) - atraso)
        s.commit()
    assert admin.get("/api/escaneos").status_code == 401


def test_la_sesion_se_mantiene_mientras_se_usa(admin):
    with db(admin) as s:
        sesion = s.scalars(select(Sesion)).one()
        sesion.ultimo_uso -= timedelta(minutes=29)
        s.commit()
    assert admin.get("/api/escaneos").status_code == 200
    with db(admin) as s:  # el uso la renueva
        assert usuarios.ahora() - s.scalars(select(Sesion)).one().ultimo_uso < timedelta(minutes=1)


# --- Contraseña temporal y cambio de contraseña -------------------------------------------------

def test_clave_temporal_solo_permite_cambiarla(admin):
    r = admin.post("/api/usuarios", json={"usuario": "tomas", "nombre": "Tomás", "correo": "t@empresa.cl", "rol": "Auditor"})
    temporal = r.json()["clave_temporal"]
    assert len(temporal) == 14 and r.json()["usuario"]["debe_cambiar_clave"] is True
    c, _ = ingresar(admin.app, "tomas", temporal)
    assert c.get("/api/escaneos").status_code == 428
    assert c.get("/historial.html", follow_redirects=False).headers["location"] == "/login.html"
    assert c.get("/api/sesion").json()["usuario"]["usuario"] == "tomas"
    assert c.post("/api/sesion/cambiar-clave", json={"nueva": temporal}).json()["detail"] == \
        "La nueva contraseña debe ser distinta de la anterior"
    assert c.post("/api/sesion/cambiar-clave", json={"nueva": "tomas"}).status_code == 400
    assert c.post("/api/sesion/cambiar-clave", json={"nueva": "clave-de-tomas"}).status_code == 200
    assert c.get("/api/escaneos").status_code == 200
    assert ingresar(admin.app, "tomas", temporal)[1].status_code == 401


def test_cambiar_clave_pide_la_actual_y_cierra_las_otras_sesiones(admin):
    otro_navegador, _ = ingresar(admin.app, "admin", ADMIN["clave"])
    assert admin.post("/api/sesion/cambiar-clave", json={"actual": "mala", "nueva": "nueva-clave-admin"}).status_code == 400
    assert admin.post("/api/sesion/cambiar-clave", json={"actual": ADMIN["clave"], "nueva": "nueva-clave-admin"}).status_code == 200
    assert admin.get("/api/escaneos").status_code == 200        # esta sesión sigue
    assert otro_navegador.get("/api/escaneos").status_code == 401  # la otra se cerró
    assert ingresar(admin.app, "admin", "nueva-clave-admin")[1].status_code == 200


# --- Roles -----------------------------------------------------------------------------------------

def test_permisos_de_cada_rol(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    escaneo_id = subir(admin).json()["escaneo_id"]
    hallazgo = admin.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"][0]["id"]
    visor, auditor = cuenta(admin, "vera", "Visor"), cuenta(admin, "aldo", "Auditor")
    regla = {"nombre": "SOCIO", "patron": r"S-\d{5}", "riesgo": "Interno"}

    # Visor: solo mira resultados enmascarados y reglas.
    assert visor.get(f"/api/escaneos/{escaneo_id}/por-tipo").status_code == 200
    assert visor.get("/api/reglas").status_code == 200
    assert subir(visor).status_code == 403
    assert visor.post(f"/api/hallazgos/{hallazgo}/revelar", json={"clave": CLAVE_AUDITOR}).status_code == 403
    assert visor.delete(f"/api/escaneos/{escaneo_id}").status_code == 403
    assert visor.post("/api/reglas", json=regla).status_code == 403
    assert visor.get("/api/usuarios").status_code == 403
    assert visor.get("/archivos.html", follow_redirects=False).headers["location"] == "/"

    # Auditor: además escanea, revela con la clave de auditor y borra escaneos.
    assert subir(auditor).status_code == 200
    assert auditor.post(f"/api/hallazgos/{hallazgo}/revelar", json={"clave": CLAVE_AUDITOR}).json() == {"valor": "15.432.198-5"}
    assert auditor.post("/api/reglas", json=regla).status_code == 403
    assert auditor.post("/api/auditor", json={"clave": "otra-clave-larga"}).status_code == 403
    assert auditor.get("/api/usuarios").status_code == 403
    assert auditor.get("/usuarios.html", follow_redirects=False).headers["location"] == "/"
    assert auditor.get("/archivos.html").status_code == 200
    assert auditor.delete(f"/api/escaneos/{escaneo_id}").status_code == 204

    # Admin: también reglas y cuentas.
    assert admin.post("/api/reglas", json=regla).status_code == 201
    assert admin.get("/usuarios.html").status_code == 200


def test_bloqueo_de_la_clave_de_auditor_es_por_cuenta(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    escaneo_id = subir(admin).json()["escaneo_id"]
    url = f"/api/hallazgos/{admin.get(f'/api/escaneos/{escaneo_id}/hallazgos').json()['items'][0]['id']}/revelar"
    aldo, berta = cuenta(admin, "aldo", "Auditor"), cuenta(admin, "berta", "Auditor")
    for _ in range(5):
        assert aldo.post(url, json={"clave": "mala-clave"}).status_code == 403
    assert aldo.post(url, json={"clave": CLAVE_AUDITOR}).status_code == 429
    assert berta.post(url, json={"clave": CLAVE_AUDITOR}).status_code == 200  # a Berta no le afecta


# --- Administración de cuentas -----------------------------------------------------------------------

def test_administrar_cuentas(admin):
    visor = cuenta(admin, "vera", "Visor")
    lista = admin.get("/api/usuarios").json()
    assert [u["usuario"] for u in lista] == ["admin", "vera"]
    assert all("clave_hash" not in u for u in lista)
    vera = lista[1]
    nueva = {"usuario": "VERA", "nombre": "Otra", "correo": "otra@empresa.cl", "rol": "Visor"}
    assert admin.post("/api/usuarios", json=nueva).json()["detail"] == "Ese usuario ya existe"
    assert admin.post("/api/usuarios", json={**nueva, "usuario": "vera2", "correo": "VERA@empresa.cl"}).json()["detail"] == \
        "Ya hay otra cuenta con ese correo"
    assert admin.post("/api/usuarios", json={**nueva, "usuario": "vera2", "rol": "Jefe"}).status_code == 400

    cambios = {"nombre": "Vera Rojas", "correo": "vera@empresa.cl", "rol": "Auditor", "activo": True}
    assert admin.put(f"/api/usuarios/{vera['id']}", json=cambios).json()["rol"] == "Auditor"
    assert subir(visor).status_code == 409  # ya es Auditor (409: falta la clave de auditor, no 403)

    assert admin.put(f"/api/usuarios/{vera['id']}", json={**cambios, "activo": False}).status_code == 200
    assert visor.get("/api/escaneos").status_code == 401  # desactivar cierra sus sesiones
    r = ingresar(admin.app, "vera", "clave-de-vera")[1]
    assert r.status_code == 403 and "desactivada" in r.json()["detail"]


def test_siempre_queda_un_administrador(admin):
    yo = admin.get("/api/sesion").json()["usuario"]
    propio = {"nombre": yo["nombre"], "correo": yo["correo"], "rol": "Visor", "activo": True}
    assert "propio rol" in admin.put(f"/api/usuarios/{yo['id']}", json=propio).json()["detail"]
    assert "propio rol" in admin.put(f"/api/usuarios/{yo['id']}", json={**propio, "rol": "Admin", "activo": False}).json()["detail"]
    segundo = cuenta(admin, "bruno", "Admin")
    bruno = segundo.get("/api/sesion").json()["usuario"]
    # Bruno puede quitarle el rol a Ana, pero no al revés después: quedaría sin administradores.
    assert segundo.put(f"/api/usuarios/{yo['id']}", json={**propio, "rol": "Visor"}).status_code == 200
    assert admin.put(f"/api/usuarios/{bruno['id']}", json={"nombre": "Bruno", "correo": "bruno@empresa.cl",
                                                          "rol": "Visor", "activo": True}).status_code == 403
    assert "propio rol" in segundo.put(f"/api/usuarios/{bruno['id']}", json={"nombre": "Bruno", "correo": "bruno@empresa.cl",
                                                                             "rol": "Visor", "activo": True}).json()["detail"]


def test_regla_del_ultimo_administrador_en_la_capa_de_datos(admin):
    """Defensa extra: aunque otra pantalla lo intentara, la base nunca queda sin administradores activos."""
    with db(admin) as s:
        ana = s.scalar(select(Usuario).where(Usuario.usuario == "admin"))
        otro = Usuario(id=999, rol="Admin")
        with pytest.raises(usuarios.ErrorUsuario, match="al menos un administrador"):
            usuarios.actualizar(s, ana.id, otro, ana.nombre, ana.correo, "Visor", True)


def test_tu_propia_cuenta_no_se_restablece_desde_la_web(admin):
    yo = admin.get("/api/sesion").json()["usuario"]
    r = admin.post(f"/api/usuarios/{yo['id']}/restablecer")
    assert r.status_code == 400 and "Cambiar contraseña" in r.json()["detail"]
    assert admin.get("/api/escaneos").status_code == 200  # la sesión sigue abierta


def test_plan_b_restablecer_desde_la_terminal(tmp_path, capsys):
    """Si nadie puede entrar como admin, el comando restablece la cuenta directo en la base."""
    from ksecure import restablecer
    url = f"sqlite:///{tmp_path / 'interna.db'}"
    c = TestClient(create_app(url))
    assert c.post("/api/sesion/configurar", json=ADMIN).status_code == 201

    assert restablecer.main(["--url", url]) == 0
    assert "admin" in capsys.readouterr().out
    assert restablecer.main(["no-existe", "--url", url]) == 1
    capsys.readouterr()
    assert restablecer.main(["ADMIN", "--url", url]) == 0
    temporal = capsys.readouterr().out.split("Contraseña temporal: ")[1].split()[0]

    assert c.get("/api/escaneos").status_code == 401           # su sesión se cerró
    assert ingresar(c.app, "admin", ADMIN["clave"])[1].status_code == 401
    nuevo, r = ingresar(c.app, "admin", temporal)
    assert r.status_code == 200 and r.json()["usuario"]["debe_cambiar_clave"] is True
    assert nuevo.post("/api/sesion/cambiar-clave", json={"nueva": "otra-clave-admin"}).status_code == 200
    assert nuevo.get("/api/usuarios").status_code == 200
