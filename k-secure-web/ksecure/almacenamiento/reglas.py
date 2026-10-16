"""Mantenedor de reglas: guarda las reglas personalizadas y los ajustes de los validadores incluidos,
y arma la lista de validadores que usa cada escaneo."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ksecure.almacenamiento.modelos import AjusteValidador, Regla
from ksecure.core.models import RiskLevel
from ksecure.validators import INCLUIDOS
from ksecure.validators.base import Validator
from ksecure.validators.patron import MAX_EJEMPLOS, MAX_LARGO
from ksecure.validators.regla import VALIDACIONES, ParametrosRegla, ReglaValidator

_NOMBRE = re.compile(r"^[A-Z][A-Z0-9_]{1,49}$")
MAX_PATRON = 500


def _palabras(lista) -> list[str]:
    return sorted({p.strip().lower() for p in lista or [] if p.strip()})[:50]


def parametros(datos: dict) -> ParametrosRegla:
    """Valida lo que viene de la pantalla y lo convierte en parámetros de un validador."""
    nombre = datos.get("nombre", "").strip().upper()
    if not _NOMBRE.match(nombre):
        raise ValueError("El nombre va en MAYÚSCULAS, sin espacios (ej. PASAPORTE o FICHA_CLINICA)")
    if nombre in INCLUIDOS:
        raise ValueError(f"{nombre} ya es un validador incluido")
    patron = datos.get("patron", "")
    if not patron or len(patron) > MAX_PATRON:
        raise ValueError(f"El patrón es obligatorio y tiene máximo {MAX_PATRON} caracteres")
    try:
        re.compile(patron)
    except re.error as e:
        raise ValueError(f"El patrón no es una expresión regular válida: {e}") from e
    if datos.get("validacion", "ninguna") not in VALIDACIONES:
        raise ValueError("Validación desconocida")
    riesgos = {r.value: r for r in RiskLevel}
    if datos.get("riesgo") not in riesgos:
        raise ValueError("Riesgo desconocido")
    return ParametrosRegla(
        nombre=nombre,
        patron=patron,
        validacion=datos.get("validacion", "ninguna"),
        palabras_positivas=tuple(_palabras(datos.get("palabras_positivas"))),
        palabras_negativas=tuple(_palabras(datos.get("palabras_negativas"))),
        requiere_contexto=bool(datos.get("requiere_contexto")),
        confianza=max(0, min(100, int(datos.get("confianza", 70)))),
        riesgo=riesgos[datos["riesgo"]],
        visibles=max(0, min(20, int(datos.get("visibles", 4)))),
    )


def _a_dict(r: Regla) -> dict:
    return {
        "id": r.id, "nombre": r.nombre, "descripcion": r.descripcion, "patron": r.patron, "ejemplos": r.ejemplos or [],
        "validacion": r.validacion, "palabras_positivas": r.palabras_positivas,
        "palabras_negativas": r.palabras_negativas, "requiere_contexto": r.requiere_contexto,
        "confianza": r.confianza, "riesgo": r.riesgo, "visibles": r.visibles, "activa": r.activa,
    }


def _desde_modelo(r: Regla) -> ParametrosRegla:
    return parametros({**_a_dict(r), "nombre": r.nombre})


def listar(db: Session) -> dict:
    ajustes = {a.nombre: a for a in db.scalars(select(AjusteValidador))}
    incluidos = []
    for nombre, (cls, descripcion) in INCLUIDOS.items():
        a = ajustes.get(nombre)
        incluidos.append({
            "nombre": nombre, "descripcion": descripcion, "activo": a.activo if a else True,
            "palabras_base": list(cls.positive_keywords),
            "palabras_positivas": a.palabras_positivas if a else [],
            "palabras_negativas": a.palabras_negativas if a else [],
        })
    personalizadas = [_a_dict(r) for r in db.scalars(select(Regla).order_by(Regla.nombre))]
    return {"incluidos": incluidos, "personalizadas": personalizadas, "validaciones": list(VALIDACIONES)}


def ajustar_incluido(db: Session, nombre: str, activo: bool, positivas: list, negativas: list):
    if nombre not in INCLUIDOS:
        raise LookupError(nombre)
    a = db.get(AjusteValidador, nombre) or AjusteValidador(nombre=nombre)
    a.activo, a.palabras_positivas, a.palabras_negativas = activo, _palabras(positivas), _palabras(negativas)
    db.add(a)
    db.commit()


def guardar(db: Session, datos: dict, regla_id: int | None = None) -> dict:
    p = parametros(datos)
    r = db.get(Regla, regla_id) if regla_id else Regla()
    if r is None:
        raise LookupError(regla_id)
    otra = db.scalar(select(Regla).where(Regla.nombre == p.nombre))
    if otra and otra.id != r.id:
        raise ValueError(f"Ya existe una regla llamada {p.nombre}")
    r.nombre, r.patron, r.validacion = p.nombre, p.patron, p.validacion
    r.palabras_positivas, r.palabras_negativas = list(p.palabras_positivas), list(p.palabras_negativas)
    r.requiere_contexto, r.confianza, r.riesgo, r.visibles = p.requiere_contexto, p.confianza, p.riesgo.value, p.visibles
    r.descripcion = datos.get("descripcion", "")[:300]
    r.ejemplos = [e.strip()[:MAX_LARGO] for e in datos.get("ejemplos") or [] if e.strip()][:MAX_EJEMPLOS]
    r.activa = bool(datos.get("activa", True))
    db.add(r)
    db.commit()
    return _a_dict(r)


def borrar(db: Session, regla_id: int) -> bool:
    r = db.get(Regla, regla_id)
    if r is None:
        return False
    db.delete(r)
    db.commit()
    return True


def validadores_activos(db: Session) -> list[Validator]:
    """Los validadores que usa un escaneo: los incluidos activos (con sus palabras extra) + las reglas activas."""
    ajustes = {a.nombre: a for a in db.scalars(select(AjusteValidador))}
    validadores: list[Validator] = []
    for nombre, (cls, _) in INCLUIDOS.items():
        a = ajustes.get(nombre)
        if a and not a.activo:
            continue
        v = cls()
        if a:
            # dict.fromkeys: sin repetir una palabra que el validador ya traía (contaría doble).
            v.positive_keywords = tuple(dict.fromkeys(cls.positive_keywords + tuple(a.palabras_positivas)))
            v.negative_keywords = tuple(dict.fromkeys(cls.negative_keywords + tuple(a.palabras_negativas)))
        validadores.append(v)
    for r in db.scalars(select(Regla).where(Regla.activa)):
        validadores.append(ReglaValidator(_desde_modelo(r)))
    return validadores
