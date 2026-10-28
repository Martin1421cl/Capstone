"""Bitácora (RF-17): quién hizo qué y cuándo."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from ksecure.almacenamiento import bitacora, usuarios
from ksecure.almacenamiento.modelos import Evento
from ksecure.web.app import create_app
from tests.conftest import CLAVE_AUDITOR, cuenta

RUT = "15.432.198-5"


def eventos(admin, **filtros) -> list[dict]:
    r = admin.get("/api/bitacora", params={"por_pagina": 100, **filtros})
    assert r.status_code == 200, r.text
    return r.json()["eventos"]


def acciones(admin, **filtros) -> list[str]:
    return [e["accion"] for e in reversed(eventos(admin, **filtros))]  # del más antiguo al más nuevo


def ultimo(admin, accion) -> dict:
    return next(e for e in eventos(admin) if e["accion"] == accion)


def escanear(c, texto=f"RUT {RUT}".encode()):
    return c.post("/api/archivos", files=[("archivos", ("clientes.txt", texto))]).json()["escaneo_id"]


def primer_hallazgo(c, escaneo_id) -> int:
    return c.get(f"/api/escaneos/{escaneo_id}/hallazgos").json()["items"][0]["id"]


def todo_el_texto(c) -> str:
    """Todo lo que guarda la bitácora, tal cual está en la base."""
    with c.app.state.sesiones() as db:
        return " ".join(f"{e.detalle} {e.usuario} {e.nombre} {e.ip}" for e in db.scalars(select(Evento)))


# --- Qué se anota -----------------------------------------------------------------------------------

def test_cada_dato_original_visto_queda_anotado_sin_el_dato(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    aldo = cuenta(admin, "aldo", "Auditor")
    escaneo_id = escanear(aldo)
    url = f"/api/hallazgos/{primer_hallazgo(aldo, escaneo_id)}/revelar"

    assert aldo.post(url, json={"clave": "clave-mala"}).status_code == 403
    assert aldo.post(url, json={"clave": CLAVE_AUDITOR}).json() == {"valor": RUT}

    fallido, visto = ultimo(admin, "revelar_fallido"), ultimo(admin, "dato_revelado")
    assert fallido["alerta"] is True and fallido["usuario"] == "aldo"
    assert visto["usuario"] == "aldo" and visto["nombre"] == "Aldo" and visto["escaneo_id"] == escaneo_id
    assert "RUT" in visto["detalle"] and "clientes.txt" in visto["detalle"] and f"#{escaneo_id}" in visto["detalle"]
    assert RUT not in todo_el_texto(admin) and "15432198" not in todo_el_texto(admin)
    assert CLAVE_AUDITOR not in todo_el_texto(admin) and "clave-mala" not in todo_el_texto(admin)


def test_bloqueo_de_la_clave_de_auditor(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    url = f"/api/hallazgos/{primer_hallazgo(admin, escanear(admin))}/revelar"
    for _ in range(5):
        admin.post(url, json={"clave": "clave-mala"})
    assert acciones(admin, categoria="Datos originales")[-2:] == ["revelar_fallido", "revelar_bloqueado"]


def test_ingresos_fallidos_sin_guardar_lo_que_se_escribio(admin):
    cuenta(admin, "vale", "Visor")
    anonimo = TestClient(admin.app)
    anonimo.post("/api/sesion/ingresar", json={"usuario": "vale", "clave": "no-es-la-clave"})
    anonimo.post("/api/sesion/ingresar", json={"usuario": "mi-clave-secreta", "clave": "x"})

    fallido = ultimo(admin, "ingreso_fallido")
    assert fallido["usuario"] == "vale" and "intento 1 de 5" in fallido["detalle"] and fallido["alerta"]
    desconocido = ultimo(admin, "ingreso_desconocido")
    assert desconocido["usuario"] is None and desconocido["alerta"]
    texto = todo_el_texto(admin)
    assert "mi-clave-secreta" not in texto and "no-es-la-clave" not in texto


def test_bloqueo_y_cuenta_desactivada(admin):
    cuenta(admin, "vale", "Visor")
    for _ in range(usuarios.MAX_INTENTOS + 1):
        TestClient(admin.app).post("/api/sesion/ingresar", json={"usuario": "vale", "clave": "mala-clave-1"})
    ultimas = acciones(admin, persona=_id(admin, "vale"))[-3:]
    assert ultimas == ["ingreso_fallido", "cuenta_bloqueada", "ingreso_fallido"]  # el último, durante el bloqueo
    assert "bloqueada" in eventos(admin)[0]["detalle"]

    pedro = cuenta(admin, "pedro", "Visor", clave="clave-de-pedro")
    datos = _cuenta(admin, "pedro")
    admin.put(f"/api/usuarios/{datos['id']}", json={**datos, "activo": False})
    assert pedro.get("/api/escaneos").status_code == 401
    TestClient(admin.app).post("/api/sesion/ingresar", json={"usuario": "pedro", "clave": "clave-de-pedro"})
    assert ultimo(admin, "ingreso_fallido")["detalle"] == "Intento en una cuenta desactivada"


def test_sesion_y_contrasenas(admin):
    vale = cuenta(admin, "vale", "Visor")  # entra con temporal y la cambia
    vale.post("/api/sesion/salir")
    sesion = acciones(admin, persona=_id(admin, "vale"))
    assert sesion == ["cuenta_creada", "ingreso", "clave_cambiada", "salida"]
    cambio = ultimo(admin, "clave_cambiada")
    assert cambio["detalle"] == "Reemplazó la contraseña temporal" and cambio["usuario"] == "vale"
    assert ultimo(admin, "ingreso")["detalle"] == "Con una contraseña temporal"


def test_administracion_de_cuentas(admin):
    cuenta(admin, "vale", "Visor")
    vale = _cuenta(admin, "vale")
    admin.put(f"/api/usuarios/{vale['id']}", json={**vale, "rol": "Auditor"})
    admin.put(f"/api/usuarios/{vale['id']}", json={**vale, "rol": "Auditor"})  # sin cambios: no se anota
    admin.put(f"/api/usuarios/{vale['id']}", json={**vale, "rol": "Auditor", "activo": False})
    admin.post(f"/api/usuarios/{vale['id']}/restablecer")

    por_admin = [e for e in eventos(admin, persona=vale["id"]) if e["usuario"] == "admin"]
    assert [e["accion"] for e in reversed(por_admin)] == \
        ["cuenta_creada", "cuenta_editada", "cuenta_desactivada", "clave_restablecida"]
    assert ultimo(admin, "cuenta_editada")["detalle"] == "Cuenta @vale: rol: Visor → Auditor"
    assert ultimo(admin, "cuenta_creada")["detalle"] == "Cuenta @vale (Vale) con rol Visor"


def test_escaneos_y_reglas(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    escaneo_id = escanear(admin)
    admin.delete(f"/api/escaneos/{escaneo_id}")
    regla = admin.post("/api/reglas", json={"nombre": "SOCIO", "patron": r"S-\d{5}", "riesgo": "Interno"}).json()
    admin.put(f"/api/reglas/{regla['id']}", json={**regla, "activa": False})
    admin.delete(f"/api/reglas/{regla['id']}")
    admin.put("/api/reglas/incluidas/RUT", json={"activo": False, "palabras_positivas": ["socio"], "palabras_negativas": []})

    assert acciones(admin, categoria="Escaneos") == ["escaneo_archivos", "escaneo_borrado"]
    assert "clientes.txt · 1 hallazgo" in ultimo(admin, "escaneo_archivos")["detalle"]
    assert "clientes.txt (1 hallazgos" in ultimo(admin, "escaneo_borrado")["detalle"]  # queda aunque se borró
    assert acciones(admin, categoria="Reglas") == ["regla_creada", "regla_editada", "regla_borrada", "validador_ajustado"]
    assert ultimo(admin, "regla_editada")["detalle"] == "«SOCIO» (apagada)"
    assert ultimo(admin, "validador_ajustado")["detalle"] == "RUT: apagado, 1 palabras extra"
    assert "clave_auditor_creada" in acciones(admin)


def test_primer_admin_desde_la_variable_y_desde_la_terminal(tmp_path, capsys):
    from ksecure import restablecer
    url = f"sqlite:///{tmp_path / 'interna.db'}"
    app = create_app(url, acceso="jefe:temporal-12345")
    restablecer.main(["jefe", "--url", url])
    capsys.readouterr()
    with app.state.sesiones() as db:
        filas = list(db.scalars(select(Evento).order_by(Evento.id)))
    assert [e.accion for e in filas] == ["configuracion_inicial", "clave_restablecida"]
    assert "KSECURE_ACCESO" in filas[0].detalle and "temporal-12345" not in filas[0].detalle
    assert filas[1].usuario is None and "terminal" in filas[1].detalle  # no la hizo ninguna cuenta


def test_se_guarda_la_ip(admin):
    TestClient(admin.app).post("/api/sesion/ingresar", json={"usuario": "admin", "clave": "mala-clave-1"},
                               headers={"X-Forwarded-For": "200.1.2.3, 10.0.0.1"})
    assert ultimo(admin, "ingreso_fallido")["ip"] == "200.1.2.3"


# --- Quién la ve y cómo ------------------------------------------------------------------------------

def test_solo_admin_y_solo_lectura(admin):
    for rol in ("Visor", "Auditor"):
        otro = cuenta(admin, rol.lower() + "x", rol)
        assert otro.get("/api/bitacora").status_code == 403
        assert otro.get("/api/bitacora/resumen").status_code == 403
        assert otro.get("/bitacora.html", follow_redirects=False).headers["location"] == "/"
    assert TestClient(admin.app).get("/api/bitacora").status_code == 401
    assert admin.get("/bitacora.html").status_code == 200
    metodos = {m for ruta, ms in admin.app.openapi()["paths"].items() if ruta.startswith("/api/bitacora") for m in ms}
    assert metodos == {"get"}  # no hay cómo editar ni borrar eventos


def test_filtros_paginas_y_resumen(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    url = f"/api/hallazgos/{primer_hallazgo(admin, escanear(admin))}/revelar"
    for _ in range(3):
        admin.post(url, json={"clave": CLAVE_AUDITOR})
    TestClient(admin.app).post("/api/sesion/ingresar", json={"usuario": "admin", "clave": "mala-clave-1"})

    assert set(acciones(admin, categoria="Alertas")) == {"ingreso_fallido"}
    assert acciones(admin, categoria="Datos originales").count("dato_revelado") == 3
    assert {e["accion"] for e in eventos(admin, buscar="CLIENTES.TXT")} == {"escaneo_archivos", "dato_revelado"}
    assert eventos(admin, buscar="100%") == []  # el % se busca literal, no como comodín

    pagina = admin.get("/api/bitacora", params={"por_pagina": 2, "pagina": 2}).json()
    assert pagina["pagina"] == 2 and len(pagina["eventos"]) == 2 and pagina["paginas"] == -(-pagina["total"] // 2)
    todos = eventos(admin)
    assert todos[0]["id"] > todos[-1]["id"]  # del más nuevo al más antiguo

    resumen = admin.get("/api/bitacora/resumen").json()
    assert resumen["datos_vistos"] == 3 and resumen["alertas"] == 1 and resumen["escaneos"] == 1
    assert resumen["categorias"][0] == "Alertas"

    with admin.app.state.sesiones() as db:  # un evento de hace un mes no entra en "últimos 7 días"
        viejo = db.scalars(select(Evento).where(Evento.accion == "escaneo_archivos")).one()
        viejo.fecha -= bitacora.timedelta(days=30)
        db.commit()
    assert "escaneo_archivos" not in acciones(admin, dias=7)
    assert admin.get("/api/bitacora/resumen").json()["escaneos"] == 0


def test_detalle_muy_largo_se_corta(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    archivos = [("archivos", (f"{'x' * 60}-{i}.txt", b"hola")) for i in range(12)]
    admin.post("/api/archivos", files=archivos)
    detalle = ultimo(admin, "escaneo_archivos")["detalle"]
    assert len(detalle) == bitacora.MAX_DETALLE and detalle.endswith("…")


# --- Ayudas -----------------------------------------------------------------------------------------

def _cuenta(admin, usuario) -> dict:
    return next(u for u in admin.get("/api/usuarios").json() if u["usuario"] == usuario)


def _id(admin, usuario) -> int:
    return _cuenta(admin, usuario)["id"]


# --- Descarga -----------------------------------------------------------------------------------------

def test_descargar_csv_con_filtros_y_hora_local(admin):
    admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR})
    escanear(admin)
    admin.post("/api/archivos", files=[("archivos", ("=cmd.txt", b"hola"))])  # nombre que Excel tomaría como fórmula
    r = admin.get("/api/bitacora/csv", params={"categoria": "Escaneos", "desfase": 180})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"].startswith('attachment; filename="bitacora-ksecure-')
    texto = r.content.decode("utf-8")
    filas = texto.lstrip("\ufeff").splitlines()
    assert texto.startswith("\ufeff") and filas[0].startswith("Fecha;Usuario;Nombre;Categoría")
    assert len(filas) == 3 and all(";Escaneos;" in f for f in filas[1:])
    assert "'=cmd.txt" in filas[1] and ";admin;Ana Admin;" in filas[1]  # Excel no lo toma como fórmula
    assert "'" not in filas[2]  # solo se marca lo que Excel tomaría como fórmula

    with admin.app.state.sesiones() as db:
        utc = db.scalars(select(Evento).order_by(Evento.id.desc())).first().fecha
    assert filas[1].startswith((utc - bitacora.timedelta(minutes=180)).strftime("%Y-%m-%d %H:%M"))
    visor = cuenta(admin, "vale", "Visor")
    assert visor.get("/api/bitacora/csv").status_code == 403
