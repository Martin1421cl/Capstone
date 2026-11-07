"""Pruebas de rendimiento: K-Secure debe escanear volúmenes realistas en tiempos razonables.

Los umbrales son holgados (pensados para un notebook de estudiante) y sirven como alerta si un
cambio en el motor lo vuelve mucho más lento. Se pueden ajustar con la variable KSECURE_FACTOR_TIEMPO
(por ejemplo 2 en un PC lento).

Ejecutar solo estas pruebas:  pytest tests/rendimiento -v -s
"""

import os
import random
import time

from tests.conftest import CLAVE_AUDITOR

FACTOR = float(os.environ.get("KSECURE_FACTOR_TIEMPO", "1"))


def _rut(n: int) -> str:
    """RUT chileno válido (dígito verificador con Módulo 11) con puntos y guion."""
    suma, mult = 0, 2
    for d in reversed(str(n)):
        suma += int(d) * mult
        mult = 2 if mult == 7 else mult + 1
    dv = 11 - suma % 11
    dv = {10: "K", 11: "0"}.get(dv, str(dv))
    return f"{n:,}".replace(",", ".") + f"-{dv}"


def _csv(filas: int) -> bytes:
    random.seed(7)
    lineas = ["id;nombre;rut;correo;celular;comentario"]
    for i in range(filas):
        lineas.append(f"{i};Persona {i};{_rut(random.randint(5_000_000, 25_000_000))};"
                      f"persona{i}@correo.cl;+56 9 {random.randint(1000, 9999)} {random.randint(1000, 9999)};"
                      "cliente frecuente sin observaciones")
    return "\n".join(lineas).encode("utf-8")


def _cronometrar(cliente, nombre: str, contenido: bytes) -> tuple[float, int]:
    inicio = time.perf_counter()
    r = cliente.post("/api/archivos", files=[("archivos", (nombre, contenido))])
    segundos = time.perf_counter() - inicio
    assert r.status_code in (200, 201), r.text
    total = cliente.get(f"/api/escaneos/{r.json()['escaneo_id']}/hallazgos").json()["total"]
    return segundos, total


def test_csv_de_2000_filas_en_menos_de_30_segundos(admin):
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    segundos, total = _cronometrar(admin, "clientes_2000.csv", _csv(2000))
    print(f"\n2.000 filas: {segundos:.2f} s, {total} hallazgos ({2000 / segundos:.0f} filas/s)")
    assert total >= 2000 * 2  # al menos RUT y correo en cada fila
    assert segundos < 30 * FACTOR


def test_texto_largo_sin_datos_sensibles_es_rapido(admin):
    """Un documento grande sin datos sensibles no debe gatillar trabajo extra (ni falsos positivos)."""
    assert admin.post("/api/auditor", json={"clave": CLAVE_AUDITOR}).status_code == 201
    texto = ("El informe trimestral muestra un aumento en las ventas de la región. " * 20_000).encode()
    segundos, total = _cronometrar(admin, "informe.txt", texto)
    print(f"\n~1,4 MB de texto: {segundos:.2f} s, {total} hallazgos")
    assert total == 0
    assert segundos < 15 * FACTOR


def test_validador_rut_procesa_miles_por_segundo():
    from ksecure.validators.rut import RutValidator

    texto = "\n".join(f"RUT del cliente: {_rut(10_000_000 + i)}" for i in range(5000))
    inicio = time.perf_counter()
    encontrados = RutValidator().validate_content(texto, "prueba.txt")
    segundos = time.perf_counter() - inicio
    print(f"\n5.000 RUT: {segundos:.2f} s")
    assert len(encontrados) == 5000
    assert segundos < 10 * FACTOR
