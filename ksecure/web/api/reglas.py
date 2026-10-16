"""Endpoints del mantenedor de reglas: crear y ajustar validadores sin programar."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ksecure.almacenamiento import reglas
from ksecure.validators.patron import generar_patron
from ksecure.validators.regla import ReglaValidator
from ksecure.web.api.dependencias import get_db

MAX_TEXTO_PRUEBA = 5000

router = APIRouter(prefix="/api/reglas", tags=["reglas"])


class ReglaIn(BaseModel):
    nombre: str
    descripcion: str = ""
    patron: str
    ejemplos: list[str] = []
    validacion: str = "ninguna"
    palabras_positivas: list[str] = []
    palabras_negativas: list[str] = []
    requiere_contexto: bool = False
    confianza: int = Field(70, ge=0, le=100)
    riesgo: str
    visibles: int = Field(4, ge=0, le=20)
    activa: bool = True


class AjusteIn(BaseModel):
    activo: bool
    palabras_positivas: list[str] = []
    palabras_negativas: list[str] = []


class PruebaIn(BaseModel):
    regla: ReglaIn
    texto: str = Field(max_length=MAX_TEXTO_PRUEBA)


def _400(e: ValueError):
    return HTTPException(400, str(e))


@router.get("")
def listar(db: Session = Depends(get_db)):
    return reglas.listar(db)


@router.put("/incluidas/{nombre}", status_code=204)
def ajustar_incluido(nombre: str, datos: AjusteIn, db: Session = Depends(get_db)):
    """Activa o desactiva un validador incluido y le suma palabras de contexto."""
    try:
        reglas.ajustar_incluido(db, nombre, datos.activo, datos.palabras_positivas, datos.palabras_negativas)
    except LookupError:
        raise HTTPException(404, "Validador no encontrado") from None


@router.post("", status_code=201)
def crear(datos: ReglaIn, db: Session = Depends(get_db)):
    try:
        return reglas.guardar(db, datos.model_dump())
    except ValueError as e:
        raise _400(e) from e


@router.put("/{regla_id}")
def actualizar(regla_id: int, datos: ReglaIn, db: Session = Depends(get_db)):
    try:
        return reglas.guardar(db, datos.model_dump(), regla_id)
    except LookupError:
        raise HTTPException(404, "Regla no encontrada") from None
    except ValueError as e:
        raise _400(e) from e


@router.delete("/{regla_id}", status_code=204)
def borrar(regla_id: int, db: Session = Depends(get_db)):
    if not reglas.borrar(db, regla_id):
        raise HTTPException(404, "Regla no encontrada")


class EjemplosIn(BaseModel):
    ejemplos: list[str]


@router.post("/patron")
def patron_desde_ejemplos(datos: EjemplosIn):
    """Arma el patrón a partir de ejemplos del dato, para no tener que escribir expresiones regulares."""
    try:
        patron, descripcion = generar_patron(datos.ejemplos)
    except ValueError as e:
        raise _400(e) from e
    return {"patron": patron, "descripcion": descripcion}


@router.post("/probar")
def probar(datos: PruebaIn):
    """Prueba una regla (sin guardarla) sobre un texto de ejemplo."""
    try:
        validador = ReglaValidator(reglas.parametros(datos.regla.model_dump()))
    except ValueError as e:
        raise _400(e) from e
    return [{
        "texto": m.text, "enmascarado": m.masked_text, "linea": m.line_number,
        "confianza": round(m.confidence), "nivel": m.confidence_level.value, "riesgo": m.risk_level.value,
        "contexto": m.context.positive_keywords, "validacion_ok": m.metadata["validacion_ok"],
    } for m in validador.validate_content(datos.texto, "prueba")]
