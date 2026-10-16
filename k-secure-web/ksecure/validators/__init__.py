"""Validadores disponibles, como el --checks de ferret-scan."""

from ksecure.validators.cuenta_bancaria import CuentaBancariaValidator
from ksecure.validators.email import EmailValidator
from ksecure.validators.patente import PatenteValidator
from ksecure.validators.rut import RutValidator
from ksecure.validators.secreto import SecretoValidator
from ksecure.validators.tarjeta import TarjetaValidator
from ksecure.validators.telefono import TelefonoValidator

# Validadores programados (los que traen algoritmos propios), con la descripción que ve el usuario.
INCLUIDOS = {
    "RUT": (RutValidator, "RUT y RUN chilenos, con dígito verificador (Módulo 11) y RUT de empresa."),
    "TELEFONO": (TelefonoValidator, "Celulares +56 9 y teléfonos fijos con código de área."),
    "TARJETA_PAGO": (TarjetaValidator, "Tarjetas de crédito y débito: Luhn, marca y tarjetas de prueba."),
    "EMAIL": (EmailValidator, "Correos personales; distingue casillas de área como contacto@."),
    "CUENTA_BANCARIA": (CuentaBancariaValidator, "Números de cuenta, solo con contexto bancario cerca."),
    "PATENTE": (PatenteValidator, "Patentes de vehículos (PPU) nuevas y antiguas."),
    "SECRETO": (SecretoValidator, "Claves de AWS, tokens de GitHub y llaves privadas."),
}


def default_validators():
    return [cls() for cls, _ in INCLUIDOS.values()]
