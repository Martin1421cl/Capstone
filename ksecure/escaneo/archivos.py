"""Escaneo de archivos: documentos con los preprocesadores y bases SQLite como base de datos."""

from pathlib import Path

from ksecure.escaneo.bases_datos import ConexionError, DatosConexion, conectar, escanear_bd
from ksecure.escaneo.resultado import Hallazgo, ResultadoEscaneo
from ksecure.preprocessors import process_file
from ksecure.validators import default_validators

EXTENSIONES_SQLITE = {".db", ".sqlite", ".sqlite3"}


def _escanear_documento(ruta: str, nombre: str, resultado: ResultadoEscaneo):
    contenido = process_file(ruta)
    if not contenido.success:
        resultado.errores.append(f"{nombre}: {contenido.error}")
        return
    for v in default_validators():
        for m in v.validate_content(contenido.text, nombre):
            resultado.hallazgos.append(Hallazgo(m, nombre, f"línea {m.line_number}"))


def _escanear_sqlite(ruta: str, nombre: str, resultado: ResultadoEscaneo):
    try:
        engine = conectar(DatosConexion("sqlite", ruta=ruta))
    except ConexionError as e:
        resultado.errores.append(f"{nombre}: {e}")
        return
    try:
        parcial = escanear_bd(engine, nombre)
    finally:
        engine.dispose()  # en Windows el archivo queda bloqueado si no se cierra
    for h in parcial.hallazgos:
        h.fuente = f"{nombre} › {h.fuente}"
    resultado.hallazgos += parcial.hallazgos
    resultado.filas_por_fuente.update({f"{nombre} › {t}": n for t, n in parcial.filas_por_fuente.items()})
    resultado.errores += [f"{nombre}: {e}" for e in parcial.errores]


def escanear_archivos(archivos: list[tuple[str, str]]) -> ResultadoEscaneo:
    """archivos: pares (ruta en disco, nombre original). Todos quedan en un mismo escaneo."""
    nombres = [n for _, n in archivos]
    titulo = nombres[0] if len(nombres) == 1 else f"{len(nombres)} archivos"
    resultado = ResultadoEscaneo("archivo", titulo)
    for ruta, nombre in archivos:
        if Path(nombre).suffix.lower() in EXTENSIONES_SQLITE:
            _escanear_sqlite(ruta, nombre, resultado)
        else:
            _escanear_documento(ruta, nombre, resultado)
    return resultado
