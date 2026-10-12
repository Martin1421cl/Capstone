import pytest

from ksecure.core.models import ConfidenceLevel, RiskLevel
from ksecure.validators import default_validators
from ksecure.validators.cuenta_bancaria import CuentaBancariaValidator
from ksecure.validators.email import EmailValidator
from ksecure.validators.patente import PatenteValidator
from ksecure.validators.secreto import SecretoValidator
from ksecure.validators.tarjeta import TarjetaValidator, detectar_marca, luhn
from ksecure.validators.telefono import TelefonoValidator


def scan(validator, text):
    return validator.validate_content(text, "prueba.txt")


def completar_luhn(prefijo: str) -> str:
    return next(prefijo + d for d in "0123456789" if luhn(prefijo + d))


# --- Teléfono -------------------------------------------------------------

@pytest.mark.parametrize("texto", [
    "+56 9 6123 4870", "+56961234870", "56961234870", "(+56) 9 6123 4870",
    "9 6123 4870", "961234870", "961 234 870",
])
def test_celular_formatos(texto):
    [m] = scan(TelefonoValidator(), texto)
    assert m.metadata["tipo"] == "movil"
    assert m.metadata["numero_normalizado"] == "+56 9 6123 4870"


def test_celular_con_contexto_es_high_y_confidencial():
    [m] = scan(TelefonoValidator(), "Celular: +56 9 6123 4870")
    assert m.confidence_level == ConfidenceLevel.HIGH
    assert m.risk_level == RiskLevel.CONFIDENCIAL


@pytest.mark.parametrize("texto, normalizado", [
    ("fono 2 2654 3190", "+56 2 2654 3190"),
    ("tel. 22 654 3190", "+56 2 2654 3190"),
    ("Concepción (41) 223 4567", "+56 41 223 4567"),
])
def test_fijos(texto, normalizado):
    [m] = scan(TelefonoValidator(), texto)
    assert m.metadata["tipo"] == "fijo"
    assert m.metadata["numero_normalizado"] == normalizado
    assert m.risk_level == RiskLevel.INTERNO


def test_numero_de_ejemplo_es_low():
    [m] = scan(TelefonoValidator(), "912345678")
    assert m.confidence_level == ConfidenceLevel.LOW


@pytest.mark.parametrize("texto", [
    "RUT 21.234.567-8",            # RUT con puntos
    "91234567-8",                  # RUT sin puntos que empieza con 9
    "4111 1111 1111 1111",         # tarjeta
    "9612348701",                  # 10 dígitos
    "Ruta 68 km 961",              # incompleto
    "$961.234.870",                # monto
])
def test_telefono_no_detecta(texto):
    assert scan(TelefonoValidator(), texto) == []


# --- Tarjeta --------------------------------------------------------------

def test_luhn_y_marca():
    assert luhn("4532015112830366") and not luhn("4532015112830367")
    assert detectar_marca("4532015112830366") == "Visa"
    assert detectar_marca(completar_luhn("541333012345678")) == "Mastercard"
    assert detectar_marca("378282246310005") == "American Express"
    assert detectar_marca("37828224631000") is None  # Amex tiene 15 dígitos


def test_tarjeta_con_contexto_es_restringida_y_truncada():
    [m] = scan(TarjetaValidator(), "Visa 4532 0151 1283 0366 venc 12/27")
    assert m.confidence_level == ConfidenceLevel.HIGH
    assert m.risk_level == RiskLevel.RESTRINGIDO
    assert m.metadata["numero_truncado"] == "453201******0366"


def test_tipo_por_contexto_chileno():
    numero = completar_luhn("541333012345678")
    [m] = scan(TarjetaValidator(), f"tarjeta de débito Redcompra {numero}")
    assert m.metadata["tipo"] == "debito"


def test_tarjeta_de_prueba_transbank_es_low():
    [m] = scan(TarjetaValidator(), "4051 8856 0044 6623")
    assert m.metadata["tarjeta_de_prueba"]
    assert m.confidence_level == ConfidenceLevel.LOW


@pytest.mark.parametrize("texto", [
    "4532 0151 1283 0367",      # Luhn inválido
    "4532-0151 1283 0366",      # separadores mezclados
    "45320 15112 830366",       # agrupación no estándar
    "9532015112830366",         # Luhn ok pero no es de ninguna marca
])
def test_tarjeta_no_detecta(texto):
    assert scan(TarjetaValidator(), texto) == []


# --- Email ----------------------------------------------------------------

def test_email_personal_es_confidencial():
    [m] = scan(EmailValidator(), "correo: juan.perez@gmail.com")
    assert m.text == "juan.perez@gmail.com"
    assert m.risk_level == RiskLevel.CONFIDENCIAL


def test_email_de_rol_es_publico():
    [m] = scan(EmailValidator(), "escribir a contacto@duoc.cl")
    assert m.metadata["cuenta_de_rol"]
    assert m.risk_level == RiskLevel.PUBLICO


def test_email_de_ejemplo_es_low():
    [m] = scan(EmailValidator(), "usuario@ejemplo.cl")
    assert m.confidence_level == ConfidenceLevel.LOW


# --- Cuenta bancaria ------------------------------------------------------

@pytest.mark.parametrize("texto, numero", [
    ("Cuenta corriente BancoEstado 00012345678", "00012345678"),
    ("Cuenta RUT 15432198", "15432198"),
    ("Banco Santander cta cte 0-000-12-34567-8", "000012345678"),
])
def test_cuenta_con_contexto(texto, numero):
    [m] = scan(CuentaBancariaValidator(), texto)
    assert m.metadata["numero"] == numero
    assert m.risk_level == RiskLevel.RESTRINGIDO


@pytest.mark.parametrize("texto", [
    "00012345678",                          # sin contexto bancario
    "depósito del 2024-05-12",              # fecha
    "cuenta del cliente 15.432.198-5",      # RUT
    "transferencia de $1.250.000",          # monto con puntos
])
def test_cuenta_no_detecta(texto):
    assert scan(CuentaBancariaValidator(), texto) == []


def test_monto_con_contexto_bancario_queda_low():
    [m] = scan(CuentaBancariaValidator(), "Total transferencia 1250000")
    assert m.confidence_level == ConfidenceLevel.LOW
    assert m.risk_level == RiskLevel.INTERNO


# --- Patente --------------------------------------------------------------

@pytest.mark.parametrize("texto, formato", [
    ("Patente BBCD-12", "nuevo"), ("PPU BB·CD·12", "nuevo"), ("patente del auto CL·12·34", "antiguo"),
])
def test_patentes(texto, formato):
    [m] = scan(PatenteValidator(), texto)
    assert m.metadata["formato"] == formato
    assert m.risk_level == RiskLevel.CONFIDENCIAL


def test_patente_antigua_sin_contexto_es_low():
    [m] = scan(PatenteValidator(), "según norma PC 2023")
    assert m.confidence_level == ConfidenceLevel.LOW


@pytest.mark.parametrize("texto", ["BACD12", "bbcd12", "ISO 9001", "ABCDE12"])
def test_patente_no_detecta(texto):
    assert scan(PatenteValidator(), texto) == []  # con vocal, minúsculas, 3 letras, 5 letras


# --- Secretos -------------------------------------------------------------

def test_aws_access_key():
    [m] = scan(SecretoValidator(), "aws_access_key_id = " + "AKIA" + "2E0A8F3B244C9986")
    assert m.metadata["tipo_secreto"] == "AWS_ACCESS_KEY"
    assert m.risk_level == RiskLevel.RESTRINGIDO


def test_aws_secret_key_marca_solo_el_valor():
    clave = "Zx8/kq2Lm9Pw4Rt7Yu1Io0Pa5Sd3Fg6Hj8Kl2Mn4"
    [m] = scan(SecretoValidator(), f'AWS_SECRET_ACCESS_KEY="{clave}"')
    assert m.text == clave


def test_claves_de_la_documentacion_de_aws_son_low():
    found = scan(SecretoValidator(), "AKIAIOSFODNN7EXAMPLE wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    assert [m.confidence_level for m in found] == [ConfidenceLevel.LOW]


def test_llave_privada():
    [m] = scan(SecretoValidator(), "-----BEGIN OPENSSH PRIVATE KEY-----")
    assert m.metadata["tipo_secreto"] == "LLAVE_PRIVADA"


# --- Todos juntos ---------------------------------------------------------

def test_cada_dato_lo_detecta_solo_su_validador():
    linea = ("Cliente RUT 15.432.198-5, celular +56 9 6123 4870, correo ana.rojas@gmail.com, "
             "Visa 4532 0151 1283 0366, patente BBCD-12")
    tipos = sorted(m.type for v in default_validators() for m in v.validate_content(linea, "x"))
    assert tipos == ["EMAIL", "PATENTE", "RUT", "TARJETA_PAGO", "TELEFONO"]


def test_nombres_unicos():
    nombres = [v.name for v in default_validators()]
    assert len(nombres) == len(set(nombres)) == 7
