"""Consultas sobre la base interna: guardar escaneos y leer sus resultados."""

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session

from ksecure.almacenamiento import boveda
from ksecure.almacenamiento.modelos import Escaneo, Hallazgo
from ksecure.almacenamiento.usuarios import ahora
from ksecure.core.models import RiskLevel
from ksecure.escaneo.resultado import ResultadoEscaneo

# De mayor a menor riesgo, para ordenar y para quedarse con el peor de una columna.
ORDEN_RIESGO = [RiskLevel.RESTRINGIDO.value, RiskLevel.CONFIDENCIAL.value,
                RiskLevel.INTERNO.value, RiskLevel.PUBLICO.value]
# Al ordenar por tipo: primero lo que identifica a una persona o permite un fraude. Las reglas personalizadas van al final.
ORDEN_TIPOS = ["RUT", "TARJETA_PAGO", "CUENTA_BANCARIA", "SECRETO", "TELEFONO", "EMAIL", "PATENTE"]
# Revisión de hallazgos (RF-16). En la base, "pendiente" es la columna vacía.
PENDIENTE, CONFIRMADO, FALSO_POSITIVO = "pendiente", "confirmado", "falso_positivo"
ESTADOS = (PENDIENTE, CONFIRMADO, FALSO_POSITIVO)
SIN_FALSOS = "sin_falsos"  # filtro: todo menos los falsos positivos
MAX_NOTA = 200


def _lugar_en(columna, valores: list[str]):
    """Posición del valor en la lista, para ordenar en SQL con un orden propio (no alfabético)."""
    return case({v: i for i, v in enumerate(valores)}, value=columna, else_=len(valores))


_RIESGO, _TIPO = _lugar_en(Hallazgo.riesgo, ORDEN_RIESGO), _lugar_en(Hallazgo.tipo, ORDEN_TIPOS)
# Cada orden: (expresión, descendente). La primera es la que elige el usuario (y la que se invierte);
# las demás desempatan. Siempre se termina por id para que la paginación sea estable.
ORDENES = {
    "riesgo": [(_RIESGO, False), (_TIPO, False), (Hallazgo.confianza, True)],
    "tipo": [(_TIPO, False), (Hallazgo.tipo, False), (_RIESGO, False), (Hallazgo.confianza, True)],
    "confianza": [(Hallazgo.confianza, True), (_RIESGO, False)],
    "ubicacion": [(Hallazgo.fuente, False), (Hallazgo.numero, False), (Hallazgo.columna, False)],
}


def _orden_sql(orden: str, invertir: bool) -> list:
    (principal, desc), *desempates = ORDENES[orden]
    claves = [principal.desc() if desc != invertir else principal.asc()]
    claves += [e.desc() if d else e.asc() for e, d in desempates]
    return claves + [Hallazgo.id]


def guardar(db: Session, resultado: ResultadoEscaneo) -> Escaneo:
    fernet, llave_cifrada = boveda.nueva_llave_escaneo(db)
    escaneo = Escaneo(
        origen_tipo=resultado.origen_tipo, origen_nombre=resultado.origen_nombre,
        filas_por_fuente=resultado.filas_por_fuente, errores=resultado.errores,
        llave_cifrada=llave_cifrada,
    )
    escaneo.hallazgos = [
        Hallazgo(
            fuente=h.fuente, columna=h.columna, posicion=h.posicion, numero=h.numero,
            tipo=h.match.type, riesgo=h.match.risk_level.value,
            confianza=round(h.match.confidence), nivel_confianza=h.match.confidence_level.value,
            contexto=", ".join(h.match.context.positive_keywords),
            valor_enmascarado=h.match.masked_text,
            valor_cifrado=fernet.encrypt(h.match.text.encode()),
        )
        for h in resultado.hallazgos
    ]
    db.add(escaneo)
    db.commit()
    return escaneo


def _conteo_por_riesgo(db: Session, escaneo_id: int) -> dict[str, int]:
    filas = db.execute(select(Hallazgo.riesgo, func.count()).where(Hallazgo.escaneo_id == escaneo_id)
                       .group_by(Hallazgo.riesgo)).all()
    conteo = dict(filas)
    return {r: conteo.get(r, 0) for r in ORDEN_RIESGO}


def _resumen(db: Session, e: Escaneo) -> dict:
    por_riesgo = _conteo_por_riesgo(db, e.id)
    return {
        "id": e.id, "origen_tipo": e.origen_tipo, "origen_nombre": e.origen_nombre,
        "fecha": e.fecha.isoformat(timespec="seconds"),
        "total": sum(por_riesgo.values()), "por_riesgo": por_riesgo,
    }


def listar(db: Session) -> list[dict]:
    escaneos = db.scalars(select(Escaneo).order_by(Escaneo.fecha.desc())).all()
    return [_resumen(db, e) for e in escaneos]


def columnas_sensibles(db: Session, e: Escaneo) -> list[dict]:
    """Por columna: qué dato tiene, su peor riesgo y en qué % de las filas aparece."""
    de_columna = (Hallazgo.escaneo_id == e.id, Hallazgo.columna.is_not(None))
    filas_con_datos = db.execute(
        select(Hallazgo.fuente, Hallazgo.columna, func.count(func.distinct(Hallazgo.posicion)))
        .where(*de_columna).group_by(Hallazgo.fuente, Hallazgo.columna)).all()
    por_tipo_y_riesgo = db.execute(
        select(Hallazgo.fuente, Hallazgo.columna, Hallazgo.tipo, Hallazgo.riesgo, func.count())
        .where(*de_columna).group_by(Hallazgo.fuente, Hallazgo.columna, Hallazgo.tipo, Hallazgo.riesgo)).all()

    columnas = {}
    for fuente, columna, n in filas_con_datos:
        total = e.filas_por_fuente.get(fuente, 0)
        columnas[(fuente, columna)] = {
            "fuente": fuente, "columna": columna, "filas_con_datos": n,
            "porcentaje": round(100 * n / total) if total else 0,
            "riesgo": RiskLevel.PUBLICO.value, "_tipos": {},
        }
    for fuente, columna, tipo, riesgo, n in por_tipo_y_riesgo:
        c = columnas[(fuente, columna)]
        c["_tipos"][tipo] = c["_tipos"].get(tipo, 0) + n
        if ORDEN_RIESGO.index(riesgo) < ORDEN_RIESGO.index(c["riesgo"]):
            c["riesgo"] = riesgo
    for c in columnas.values():
        tipos = c.pop("_tipos")
        c["tipo"] = max(tipos, key=tipos.get)  # el dato que más aparece en la columna
    return sorted(columnas.values(), key=lambda c: (ORDEN_RIESGO.index(c["riesgo"]), -c["porcentaje"]))


def detalle(db: Session, escaneo_id: int) -> dict | None:
    e = db.get(Escaneo, escaneo_id)
    if e is None:
        return None
    por_tipo = dict(db.execute(select(Hallazgo.tipo, func.count()).where(Hallazgo.escaneo_id == e.id)
                               .group_by(Hallazgo.tipo).order_by(func.count().desc())).all())
    revision = dict(db.execute(select(Hallazgo.revision, func.count()).where(Hallazgo.escaneo_id == e.id)
                               .group_by(Hallazgo.revision)).all())
    return {
        **_resumen(db, e),
        "por_tipo": por_tipo,
        "revision": {PENDIENTE: revision.get(None, 0), CONFIRMADO: revision.get(CONFIRMADO, 0),
                     FALSO_POSITIVO: revision.get(FALSO_POSITIVO, 0)},
        "fuentes": len(e.filas_por_fuente) or len({h.fuente for h in e.hallazgos}),
        "filas_revisadas": sum(e.filas_por_fuente.values()),
        "columnas": columnas_sensibles(db, e),
        "errores": e.errores,
    }


def _filtros(escaneo_id: int, riesgo: str, tipo: str, buscar: str, revision: str = "") -> list:
    """Condiciones comunes a la tabla de hallazgos, la vista por tipo, exportar y revisar varios."""
    condiciones = [Hallazgo.escaneo_id == escaneo_id]
    if revision == PENDIENTE:
        condiciones.append(Hallazgo.revision.is_(None))
    elif revision in (CONFIRMADO, FALSO_POSITIVO):
        condiciones.append(Hallazgo.revision == revision)
    elif revision == SIN_FALSOS:
        condiciones.append(or_(Hallazgo.revision.is_(None), Hallazgo.revision != FALSO_POSITIVO))
    if riesgo:
        condiciones.append(Hallazgo.riesgo == riesgo)
    if tipo:
        condiciones.append(Hallazgo.tipo == tipo)
    if buscar:
        patron = f"%{buscar}%"
        condiciones.append(Hallazgo.fuente.ilike(patron) | Hallazgo.columna.ilike(patron))
    return condiciones


def _item(h: Hallazgo) -> dict:
    """Un hallazgo tal como sale de la API: siempre enmascarado."""
    return {
        "id": h.id, "fuente": h.fuente, "columna": h.columna, "posicion": h.posicion,
        "tipo": h.tipo, "riesgo": h.riesgo, "confianza": h.confianza,
        "nivel_confianza": h.nivel_confianza, "contexto": h.contexto,
        "valor": h.valor_enmascarado,
        "revision": h.revision or PENDIENTE, "revisado_por": h.revisado_por, "nota": h.nota_revision,
        "revisado_en": h.revisado_en.isoformat(timespec="seconds") + "Z" if h.revisado_en else None,
    }


def hallazgos(db: Session, escaneo_id: int, riesgo: str = "", tipo: str = "", buscar: str = "",
              pagina: int = 1, por_pagina: int = 50, orden: str = "riesgo", invertir: bool = False,
              revision: str = "") -> dict:
    q = select(Hallazgo).where(*_filtros(escaneo_id, riesgo, tipo, buscar, revision))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    filas = db.scalars(q.order_by(*_orden_sql(orden, invertir)).offset((pagina - 1) * por_pagina).limit(por_pagina)).all()
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina, "items": [_item(h) for h in filas]}


def para_exportar(db: Session, escaneo_id: int, riesgo: str = "", tipo: str = "", buscar: str = "",
                  revision: str = "") -> dict | None:
    """Resumen del escaneo y todos sus hallazgos con estos filtros (enmascarados, del mayor riesgo al menor)."""
    resumen = detalle(db, escaneo_id)
    if resumen is None:
        return None
    q = select(Hallazgo).where(*_filtros(escaneo_id, riesgo, tipo, buscar, revision)).order_by(*_orden_sql("riesgo", False))
    return {"escaneo": resumen, "filtros": {"riesgo": riesgo, "tipo": tipo, "buscar": buscar, "revision": revision},
            "hallazgos": [_item(h) for h in db.scalars(q)]}


def por_tipo(db: Session, escaneo_id: int, riesgo: str = "", tipo: str = "", buscar: str = "",
             pagina: int = 1, por_pagina: int = 50, revision: str = "") -> dict:
    """Hallazgos como planilla: una columna por tipo de dato, cada una con sus valores enmascarados.

    Las columnas son independientes: la fila 1 del RUT y la fila 1 del correo pueden venir de lugares
    distintos. Todas comparten la paginación (la página n trae los hallazgos n de cada tipo), así que hay
    tantas páginas como necesite la columna más larga. Dentro de cada columna, primero el mayor riesgo.
    """
    filtros = _filtros(escaneo_id, riesgo, tipo, buscar, revision)
    columnas: dict[str, dict] = {}
    for t, r, n in db.execute(select(Hallazgo.tipo, Hallazgo.riesgo, func.count())
                              .where(*filtros).group_by(Hallazgo.tipo, Hallazgo.riesgo)).all():
        c = columnas.setdefault(t, {"tipo": t, "total": 0, "riesgo": RiskLevel.PUBLICO.value})
        c["total"] += n
        if ORDEN_RIESGO.index(r) < ORDEN_RIESGO.index(c["riesgo"]):
            c["riesgo"] = r  # la columna muestra el peor riesgo que contiene

    # Mismo orden que al ordenar por tipo: RUT, tarjetas, cuentas... y las reglas personalizadas al final.
    orden_tipo = {t: i for i, t in enumerate(ORDEN_TIPOS)}
    lista = sorted(columnas.values(), key=lambda c: (orden_tipo.get(c["tipo"], len(ORDEN_TIPOS)), c["tipo"]))
    for c in lista:
        filas = db.scalars(select(Hallazgo).where(*filtros, Hallazgo.tipo == c["tipo"])
                           .order_by(*_orden_sql("riesgo", False))
                           .offset((pagina - 1) * por_pagina).limit(por_pagina)).all()
        c["items"] = [_item(h) for h in filas]

    mas_larga = max((c["total"] for c in lista), default=0)
    return {
        "total": sum(c["total"] for c in lista), "pagina": pagina, "por_pagina": por_pagina,
        "paginas": max(1, -(-mas_larga // por_pagina)),  # división hacia arriba
        "columnas": lista,
    }


def _marca(estado: str, quien, nota: str | None) -> dict:
    """Los campos de la revisión. Volver a "pendiente" borra quién, cuándo y por qué."""
    if estado not in ESTADOS:
        raise ValueError("Estado de revisión no válido")
    if estado == PENDIENTE:
        return {"revision": None, "revisado_por": None, "revisado_en": None, "nota_revision": None}
    nota = " ".join((nota or "").split())[:MAX_NOTA] or None
    return {"revision": estado, "revisado_por": quien.usuario, "revisado_en": ahora(), "nota_revision": nota}


def revisar(db: Session, escaneo_id: int, hallazgo_id: int, estado: str, quien, nota: str | None = None) -> Hallazgo | None:
    """Marca un hallazgo como confirmado, falso positivo o de nuevo pendiente."""
    h = db.get(Hallazgo, hallazgo_id)
    if h is None or h.escaneo_id != escaneo_id:
        return None
    for campo, valor in _marca(estado, quien, nota).items():
        setattr(h, campo, valor)
    db.commit()
    return h


def revisar_filtrados(db: Session, escaneo_id: int, estado: str, quien, nota: str | None = None, riesgo: str = "",
                      tipo: str = "", buscar: str = "", revision: str = "") -> int:
    """Marca de una vez todos los hallazgos que cumplen los filtros (ej. una columna completa). Devuelve cuántos."""
    resultado = db.execute(update(Hallazgo).where(*_filtros(escaneo_id, riesgo, tipo, buscar, revision))
                           .values(**_marca(estado, quien, nota)).execution_options(synchronize_session=False))
    db.commit()
    return resultado.rowcount


def borrar(db: Session, escaneo_id: int) -> bool:
    e = db.get(Escaneo, escaneo_id)
    if e is None:
        return False
    db.delete(e)
    db.commit()
    return True


def revelar(db: Session, hallazgo_id: int, clave: str) -> str | None:
    h = db.get(Hallazgo, hallazgo_id)
    if h is None:
        return None
    return boveda.revelar(db, clave, h.escaneo.llave_cifrada, h.valor_cifrado)
