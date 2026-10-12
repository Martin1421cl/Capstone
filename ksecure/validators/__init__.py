"""Validadores disponibles, como el --checks de ferret-scan."""

from ksecure.validators.cuenta_bancaria import CuentaBancariaValidator
from ksecure.validators.email import EmailValidator
from ksecure.validators.patente import PatenteValidator
from ksecure.validators.rut import RutValidator
from ksecure.validators.secreto import SecretoValidator
from ksecure.validators.tarjeta import TarjetaValidator
from ksecure.validators.telefono import TelefonoValidator


def default_validators():
    return [
        RutValidator(), TelefonoValidator(), TarjetaValidator(), EmailValidator(),
        CuentaBancariaValidator(), PatenteValidator(), SecretoValidator(),
    ]
