import pytest

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators.base import find_keywords
from ksecure.validators.rut import RutValidator, calcular_dv


def scan(text):
    return RutValidator().validate_content(text, "prueba.txt")


@pytest.mark.parametrize("cuerpo, dv", [
    (12345678, "5"), (7654321, "6"), (15432198, "5"), (9876543, "3"), (16543210, "K"),
])
def test_modulo_11(cuerpo, dv):
    assert calcular_dv(cuerpo) == dv


def test_rut_con_puntos_y_contexto_es_high_y_restringido():
    [m] = scan("RUT del trabajador: 15.432.198-5")
    assert m.confidence_level == ConfidenceLevel.HIGH
    assert m.risk_level == RiskLevel.RESTRINGIDO
    assert m.metadata["rut_normalizado"] == "15432198-5"
    assert m.context.positive_keywords == ["rut", "trabajador"]


@pytest.mark.parametrize("texto", ["15432198-5", "15.432.198 - 5", "15.432.198–5"])
def test_formatos_aceptados(texto):
    assert [m.metadata["rut_normalizado"] for m in scan(texto)] == ["15432198-5"]


def test_dv_k_minuscula():
    [m] = scan("run 16.543.210-k")
    assert m.metadata["checks"]["dv_valido"]
    assert m.metadata["rut_normalizado"] == "16543210-K"


def test_dv_invalido_es_low():
    [m] = scan("15.432.198-4")
    assert not m.metadata["checks"]["dv_valido"]
    assert m.confidence_level == ConfidenceLevel.LOW
    assert m.risk_level == RiskLevel.INTERNO


def test_rut_de_ejemplo_baja_la_confianza():
    [m] = scan("12.345.678-5")
    assert m.metadata["checks"]["rut_de_ejemplo"]
    assert m.confidence_level == ConfidenceLevel.LOW


def test_folio_es_contexto_negativo():
    [m] = scan("folio 20345678-6")
    assert m.context.negative_keywords == ["folio"]
    assert m.confidence_level == ConfidenceLevel.LOW


def test_rut_de_empresa_es_interno():
    [m] = scan("Razón social Comercial Ltda., RUT 76.086.428-5")
    assert m.metadata["persona_juridica"]
    assert m.risk_level == RiskLevel.INTERNO


@pytest.mark.parametrize("texto", [
    "+56 9 1234 5678",       # celular
    "123456789-0",           # 9 dígitos: no es RUT
    "15432198-5abc",         # pegado a letras
    "Ruta 68 km 15432198",   # sin guion
    "1.15.432.198-5",        # parte de otro número
])
def test_no_detecta(texto):
    assert scan(texto) == []


def test_linea_y_columnas():
    found = scan("nombre;rut\nAna;9.876.543-3\nLuis;18765432-7")
    assert [(m.line_number, m.start_column, m.end_column) for m in found] == [(2, 5, 16), (3, 6, 16)]
    assert all(m.filename == "prueba.txt" for m in found)


def test_palabra_completa_y_sin_tildes():
    assert find_keywords("Dirección: Ruta 68", ("rut",)) == []
    assert find_keywords("Cédula de identidad", ("cedula",)) == ["cedula"]
