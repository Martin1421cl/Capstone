"""Bitácora (RF-17): quién hizo qué y cuándo en K-Secure.

Se anota: ingresos (y los fallidos), cambios de cuentas y contraseñas, la clave de auditor, cada dato
original que alguien ve, escaneos y cambios de reglas. Solo la ve un Admin y no se puede editar ni
borrar desde K-Secure.

Regla: la bitácora nunca guarda un dato original ni una contraseña. De un hallazgo anota el valor
enmascarado (el mismo que ve un Visor) y de un ingreso con un usuario que no existe no anota el nombre
escrito, porque a veces la gente escribe la contraseña en el campo del usuario.
"""

from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ksecure.almacenamiento.modelos import Evento, Hallazgo, Usuario
from ksecure.almacenamiento.usuarios import ahora
from ksecure.core.texto import csv_excel, nombre_tipo

SESION, CUENTAS, DATOS, ESCANEOS, REVISION, REGLAS = ("Sesión", "Cuentas", "Datos originales", "Escaneos",
                                                     "Revisión", "Reglas")
CATEGORIAS = (SESION, CUENTAS, DATOS, ESCANEOS, REVISION, REGLAS)
ALERTAS = "Alertas"  # filtro especial: solo intentos fallidos y bloqueos

# código: (categoría, qué pasó, ¿es alerta?)
ACCIONES: dict[str, tuple[str, str, bool]] = {
    "ingreso": (SESION, "Ingresó", False),
    "ingreso_fallido": (SESION, "Ingreso fallido", True),
    "ingreso_desconocido": (SESION, "Ingreso con usuario inexistente", True),
    "cuenta_bloqueada": (SESION, "Cuenta bloqueada", True),
    "salida": (SESION, "Cerró sesión", False),
    "clave_cambiada": (SESION, "Cambió su contraseña", False),
    "codigo_enviado": (SESION, "Pidió un código por correo", False),
    "clave_recuperada": (SESION, "Recuperó su contraseña", False),
    "configuracion_inicial": (CUENTAS, "Configuró K-Secure", False),
    "cuenta_creada": (CUENTAS, "Creó una cuenta", False),
    "cuenta_editada": (CUENTAS, "Editó una cuenta", False),
    "cuenta_desactivada": (CUENTAS, "Desactivó una cuenta", False),
    "cuenta_activada": (CUENTAS, "Activó una cuenta", False),
    "clave_restablecida": (CUENTAS, "Restableció una contraseña", False),
    "clave_auditor_creada": (DATOS, "Creó la clave de auditor", False),
    "dato_revelado": (DATOS, "Vio un dato original", False),
    "revelar_fallido": (DATOS, "Clave de auditor incorrecta", True),
    "revelar_bloqueado": (DATOS, "Bloqueo por clave de auditor", True),
    "escaneo_archivos": (ESCANEOS, "Escaneó archivos", False),
    "escaneo_bd": (ESCANEOS, "Escaneó una base de datos", False),
    "escaneo_borrado": (ESCANEOS, "Borró un escaneo", False),
    "resultados_exportados": (ESCANEOS, "Exportó resultados", False),
    "hallazgo_revisado": (REVISION, "Revisó un hallazgo", False),
    "hallazgos_revisados": (REVISION, "Revisó varios hallazgos", False),
    "regla_creada": (REGLAS, "Creó una regla", False),
    "regla_editada": (REGLAS, "Editó una regla", False),
    "regla_borrada": (REGLAS, "Borró una regla", False),
    "validador_ajustado": (REGLAS, "Ajustó un validador incluido", False),
}

MAX_DETALLE = 500
POR_PAGINA = 25
MAX_CSV = 50_000  # filas por descarga, las más nuevas


def registrar(db: Session, accion: str, detalle: str = "", usuario: Usuario | None = None,
              afectado: Usuario | None = None, ip: str | None = None, escaneo_id: int | None = None,
              guardar: bool = True) -> Evento:
    """Anota un evento. Con guardar=True hace commit (así queda escrito antes de seguir)."""
    categoria, _, alerta = ACCIONES[accion]
    if len(detalle) > MAX_DETALLE:
        detalle = detalle[:MAX_DETALLE - 1] + "…"
    evento = Evento(
        fecha=ahora(), accion=accion, categoria=categoria, alerta=alerta, detalle=detalle,
        usuario_id=usuario.id if usuario else None, usuario=usuario.usuario if usuario else None,
        nombre=usuario.nombre if usuario else None, afectado_id=afectado.id if afectado else None,
        ip=(ip or None) and ip[:45], escaneo_id=escaneo_id,
    )
    db.add(evento)
    if guardar:
        db.commit()
    return evento


def describir_hallazgo(h: Hallazgo) -> str:
    """Ej. "RUT 15.***.***-5 en clientes.csv · línea 4 (escaneo #3)". Solo el valor enmascarado."""
    donde = " · ".join(p for p in (h.fuente, f"columna {h.columna}" if h.columna else "", h.posicion) if p)
    return f"{nombre_tipo(h.tipo)} {h.valor_enmascarado} en {donde} (escaneo #{h.escaneo_id})"


def _filtrar(consulta, categoria: str = "", persona: int | None = None, buscar: str = "", dias: int | None = None):
    if categoria == ALERTAS:
        consulta = consulta.where(Evento.alerta.is_(True))
    elif categoria:
        consulta = consulta.where(Evento.categoria == categoria)
    if persona:
        consulta = consulta.where(or_(Evento.usuario_id == persona, Evento.afectado_id == persona))
    if dias:
        consulta = consulta.where(Evento.fecha >= ahora() - timedelta(days=dias))
    if texto := buscar.strip().lower():
        consulta = consulta.where(or_(*(func.lower(func.coalesce(c, "")).contains(texto, autoescape=True)
                                        for c in (Evento.detalle, Evento.usuario, Evento.nombre, Evento.ip))))
    return consulta


def listar(db: Session, categoria: str = "", persona: int | None = None, buscar: str = "",
           dias: int | None = None, pagina: int = 1, por_pagina: int = POR_PAGINA) -> dict:
    total = db.scalar(_filtrar(select(func.count()).select_from(Evento), categoria, persona, buscar, dias))
    eventos = db.scalars(_filtrar(select(Evento), categoria, persona, buscar, dias)
                         .order_by(Evento.id.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina))
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina,
            "paginas": max(1, -(-total // por_pagina)), "eventos": [publico(e) for e in eventos]}


def exportar_csv(db: Session, categoria: str = "", persona: int | None = None, buscar: str = "",
                 dias: int | None = None, desfase_min: int = 0) -> str:
    """CSV para Excel (separado por ; y con BOM, como lo abre Excel en español).

    desfase_min es el de la zona horaria del navegador (getTimezoneOffset), para mostrar la hora local.
    """
    eventos = db.scalars(_filtrar(select(Evento), categoria, persona, buscar, dias)
                         .order_by(Evento.id.desc()).limit(MAX_CSV))
    filas = ([(e.fecha - timedelta(minutes=desfase_min)).strftime("%Y-%m-%d %H:%M:%S"), e.usuario, e.nombre,
              e.categoria, ACCIONES.get(e.accion, ("", e.accion))[1], "Sí" if e.alerta else "No", e.detalle,
              e.ip, e.escaneo_id] for e in eventos)
    return csv_excel(["Fecha", "Usuario", "Nombre", "Categoría", "Acción", "Alerta", "Detalle", "IP", "Escaneo"], filas)


def resumen(db: Session, dias: int = 7) -> dict:
    """Las cifras de arriba de la página: lo más importante de los últimos días."""
    desde = ahora() - timedelta(days=dias)
    conteo = dict(db.execute(select(Evento.accion, func.count()).where(Evento.fecha >= desde)
                             .group_by(Evento.accion)).all())
    alertas = sum(n for accion, n in conteo.items() if ACCIONES.get(accion, ("", "", False))[2])
    return {
        "dias": dias,
        "datos_vistos": conteo.get("dato_revelado", 0),
        "alertas": alertas,
        "escaneos": conteo.get("escaneo_archivos", 0) + conteo.get("escaneo_bd", 0),
        "ingresos": conteo.get("ingreso", 0) + conteo.get("clave_recuperada", 0),
    }


def publico(e: Evento) -> dict:
    return {
        "id": e.id, "fecha": e.fecha.isoformat(timespec="seconds") + "Z", "accion": e.accion,
        "titulo": ACCIONES.get(e.accion, ("", e.accion, False))[1], "categoria": e.categoria,
        "alerta": e.alerta, "usuario": e.usuario, "nombre": e.nombre, "detalle": e.detalle,
        "ip": e.ip, "escaneo_id": e.escaneo_id,
    }
