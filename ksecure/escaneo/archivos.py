"""Escaneo de archivos subidos. Cada tipo va por el camino que mejor lo entiende:

- Planillas (csv, tsv, xlsx, xls): como tablas, con el nombre de la columna como contexto.
- Bases SQLite (.db): como base de datos.
- Documentos (docx, pdf, pptx, txt...): como texto, con los preprocesadores de ferret-scan.
"""

from pathlib import Path

from ksecure.escaneo.bases_datos import ConexionError, DatosConexion, conectar, escanear_bd
from ksecure.escaneo.celdas import escanear_filas
from ksecure.escaneo.resultado import Hallazgo, ResultadoEscaneo
from ksecure.preprocessors import process_file
from ksecure.preprocessors.office import OfficeMetadataPreprocessor
from ksecure.preprocessors.tablas import EXTENSIONES as EXTENSIONES_TABLA, leer_tablas
from ksecure.validators import default_validators
from ksecure.validators.base import Validator

EXTENSIONES_SQLITE = {".db", ".sqlite", ".sqlite3"}


def _escanear_texto(texto: str, fuente: str, resultado: ResultadoEscaneo, validators: list[Validator]):
    for v in validators:
        for m in v.validate_content(texto, fuente):
            resultado.hallazgos.append(Hallazgo(m, fuente, f"línea {m.line_number}"))


def _escanear_documento(ruta: str, nombre: str, resultado: ResultadoEscaneo, validators: list[Validator]):
    contenido = process_file(ruta)
    if not contenido.success:
        resultado.errores.append(f"{nombre}: {contenido.error}")
        return
    _escanear_texto(contenido.text, nombre, resultado, validators)


def _escanear_planilla(ruta: str, nombre: str, resultado: ResultadoEscaneo, validators: list[Validator]):
    try:
        hojas = leer_tablas(ruta)
    except Exception as e:  # planilla dañada o protegida con clave
        resultado.errores.append(f"{nombre}: no se pudo leer ({type(e).__name__})")
        return
    for hoja in hojas:
        fuente = f"{nombre} › {hoja.nombre}" if hoja.nombre else nombre
        filas = ((f"fila {n}", dict(zip(hoja.encabezados, celdas))) for n, celdas in hoja.filas)
        escanear_filas(resultado, fuente, filas, validators)
    # Autor, empresa, palabras clave... también pueden filtrar datos (como en ferret-scan).
    if ruta.lower().endswith(".xlsx"):
        metadata = OfficeMetadataPreprocessor().process(ruta)
        if metadata.success and metadata.text:
            _escanear_texto(metadata.text, f"{nombre} › metadata", resultado, validators)


def _escanear_sqlite(ruta: str, nombre: str, resultado: ResultadoEscaneo, validators: list[Validator]):
    try:
        engine = conectar(DatosConexion("sqlite", ruta=ruta))
    except ConexionError as e:
        resultado.errores.append(f"{nombre}: {e}")
        return
    try:
        parcial = escanear_bd(engine, nombre, validators=validators)
    finally:
        engine.dispose()  # en Windows el archivo queda bloqueado si no se cierra
    for h in parcial.hallazgos:
        h.fuente = f"{nombre} › {h.fuente}"
    resultado.hallazgos += parcial.hallazgos
    resultado.filas_por_fuente.update({f"{nombre} › {t}": n for t, n in parcial.filas_por_fuente.items()})
    resultado.errores += [f"{nombre}: {e}" for e in parcial.errores]


def escanear_archivos(archivos: list[tuple[str, str]], validators: list[Validator] | None = None) -> ResultadoEscaneo:
    """archivos: pares (ruta en disco, nombre original). Todos quedan en un mismo escaneo.

    validators: los activos según el mantenedor de reglas; si no se indican, los incluidos.
    """
    validators = validators if validators is not None else default_validators()
    nombres = [n for _, n in archivos]
    titulo = nombres[0] if len(nombres) == 1 else f"{len(nombres)} archivos"
    resultado = ResultadoEscaneo("archivo", titulo)
    for ruta, nombre in archivos:
        ext = Path(nombre).suffix.lower()
        if ext in EXTENSIONES_SQLITE:
            _escanear_sqlite(ruta, nombre, resultado, validators)
        elif ext in EXTENSIONES_TABLA:
            _escanear_planilla(ruta, nombre, resultado, validators)
        else:
            _escanear_documento(ruta, nombre, resultado, validators)
    return resultado
