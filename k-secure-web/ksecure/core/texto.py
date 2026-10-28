"""Textos comunes a la web, la bitácora y los archivos que se descargan."""

import csv
import io
import re
import unicodedata

# Los mismos nombres que muestra la web (static/js/api.js). Las reglas propias usan su nombre.
NOMBRE_TIPO = {"RUT": "RUT", "TELEFONO": "Teléfono", "TARJETA_PAGO": "Tarjeta de pago", "EMAIL": "Correo",
               "CUENTA_BANCARIA": "Cuenta bancaria", "PATENTE": "Patente", "SECRETO": "Clave o token"}


def nombre_tipo(tipo: str) -> str:
    return NOMBRE_TIPO.get(tipo, tipo)


def celda_csv(valor) -> str:
    """Texto seguro para Excel: lo que empieza con = + - @ se tomaría como fórmula (inyección CSV)."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def csv_excel(encabezados: list[str], filas) -> str:
    """CSV como lo abre Excel en español: separado por ; y con BOM para que respete los tildes."""
    salida = io.StringIO()
    salida.write("﻿")
    w = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    w.writerow(encabezados)
    for fila in filas:
        w.writerow([celda_csv(v) for v in fila])
    return salida.getvalue()


def slug(texto: str, largo: int = 40) -> str:
    """Para nombres de archivo: "Clientes Ñuñoa.xlsx" → "clientes-nunoa-xlsx"."""
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", plano).strip("-")[:largo].strip("-") or "escaneo"
