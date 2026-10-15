"""Planillas como tablas (encabezados + filas), como las leía el K-Secure anterior.

Así cada celda se revisa con el nombre de su columna como contexto, y el
resultado dice qué columna es sensible ("rut_comprador → RUT, 99 %").
"""

import csv
import io
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime

import xlrd

from ksecure.preprocessors.office import _Package, xlsx_sheets
from ksecure.preprocessors.texto import MAX_BYTES, decode

EXTENSIONES = (".csv", ".tsv", ".xlsx", ".xls")
MAX_FILAS = 100_000  # shortcut: tope por hoja para no colgar el servidor; subirlo si se escanea en segundo plano


@dataclass
class Hoja:
    nombre: str
    encabezados: list[str]
    # (número de fila como lo ve el usuario en Excel, celdas)
    filas: list[tuple[int, list[str]]]


def _csv(path: str) -> list[tuple[str, list[list[str]]]]:
    with open(path, "rb") as f:
        texto = decode(f.read(MAX_BYTES))
    try:
        dialecto = csv.Sniffer().sniff(texto[:5000], delimiters=",;\t|")
    except csv.Error:
        dialecto = csv.excel_tab if path.lower().endswith(".tsv") else csv.excel
    return [("", list(csv.reader(io.StringIO(texto), dialecto)))]


def _xls(path: str) -> list[tuple[str, list[list[str]]]]:
    libro = xlrd.open_workbook(path, on_demand=True)
    hojas = []
    for hoja in libro.sheets():
        filas = []
        for r in range(min(hoja.nrows, MAX_FILAS + 1)):
            celdas = []
            for c in hoja.row(r):
                if c.ctype == xlrd.XL_CELL_NUMBER and c.value == int(c.value):
                    celdas.append(str(int(c.value)))  # 44.0 -> "44": así un RUT sin DV no queda como "15379476.0"
                elif c.ctype == xlrd.XL_CELL_DATE:
                    celdas.append(datetime(*xlrd.xldate_as_tuple(c.value, libro.datemode)).isoformat(" "))
                else:
                    celdas.append(str(c.value))
            filas.append(celdas)
        hojas.append((hoja.name, filas))
    return hojas


def _xlsx(path: str) -> list[tuple[str, list[list[str]]]]:
    with zipfile.ZipFile(path) as zf:
        return xlsx_sheets(_Package(zf))


def _encabezados(fila: list[str]) -> list[str]:
    """Nombres de columna únicos; una columna sin nombre pasa a ser "columna_3"."""
    vistos: dict[str, int] = {}
    nombres = []
    for i, celda in enumerate(fila, start=1):
        nombre = celda.strip() or f"columna_{i}"
        vistos[nombre] = vistos.get(nombre, 0) + 1
        nombres.append(nombre if vistos[nombre] == 1 else f"{nombre}_{vistos[nombre]}")
    return nombres


def leer_tablas(path: str) -> list[Hoja]:
    if os.path.getsize(path) > MAX_BYTES:
        raise ValueError("archivo demasiado grande")
    ext = os.path.splitext(path)[1].lower()
    lector = {".csv": _csv, ".tsv": _csv, ".xls": _xls, ".xlsx": _xlsx}[ext]
    hojas = []
    for nombre, filas in lector(path):
        con_datos = [(n, f) for n, f in enumerate(filas[:MAX_FILAS + 1], start=1) if any(c.strip() for c in f)]
        if not con_datos:
            continue
        (_, primera), *resto = con_datos
        encabezados = _encabezados(primera)
        ancho = max([len(encabezados)] + [len(f) for _, f in resto])
        encabezados += [f"columna_{i}" for i in range(len(encabezados) + 1, ancho + 1)]
        hojas.append(Hoja(nombre, encabezados, resto))
    return hojas
