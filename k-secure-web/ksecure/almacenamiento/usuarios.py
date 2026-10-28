"""Cuentas, contraseñas y sesiones de K-Secure.

- Sin registro público: el primer administrador sale de KSECURE_ACCESO (en la nube) o de la
  pantalla de configuración inicial (en un PC); las demás cuentas las crea un administrador.
- Contraseñas con hash bcrypt. 5 intentos fallidos bloquean la cuenta 5 minutos.
- La cookie de sesión lleva un token al azar; la base guarda solo su SHA-256, así una copia
  de la base no sirve para entrar. Una sesión vence tras 30 minutos sin uso o a las 12 horas.
- ¿Olvidaste tu contraseña? Un código de 6 dígitos llega al correo de la cuenta (RF-14).
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ksecure.almacenamiento.modelos import CodigoRecuperacion, Sesion, Usuario

ADMIN, AUDITOR, VISOR = "Admin", "Auditor", "Visor"
NIVEL = {VISOR: 1, AUDITOR: 2, ADMIN: 3}  # cada rol puede todo lo del anterior

MIN_LARGO_CLAVE = 10
MAX_BYTES_CLAVE = 72      # bcrypt no considera más allá de 72 bytes
MAX_INTENTOS = 5
BLOQUEO = timedelta(minutes=5)
INACTIVIDAD = timedelta(minutes=30)
DURACION_MAXIMA = timedelta(hours=12)
REFRESCO = timedelta(seconds=60)  # cada cuánto se anota el último uso (menos escrituras en la base)
RONDAS_BCRYPT = 12                # las pruebas lo bajan para correr rápido

# Recuperar la contraseña con un código al correo
CODIGO_VIGENCIA = timedelta(minutes=10)
CODIGO_INTENTOS = 5                 # intentos fallidos y el código se anula
CODIGO_ESPERA = timedelta(seconds=60)  # entre un código y el siguiente de la misma cuenta
CODIGOS_POR_HORA = 5                # por cuenta
CODIGOS_POR_DIA = 80                # entre todas: Gmail permite unos 100 correos al día
CODIGO_INVALIDO = "El código no es correcto o ya venció"

_USUARIO = re.compile(r"^[a-z0-9._-]{3,30}$")
_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SIN_AMBIGUOS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O, 1/l/I


class ErrorUsuario(ValueError):
    """Dato inválido o acción no permitida; el mensaje se muestra tal cual."""


class CuentaBloqueada(Exception):
    def __init__(self, minutos: int, cuenta: "Usuario", nueva: bool = False):
        super().__init__(f"Demasiados intentos. La cuenta queda bloqueada {minutos} min.")
        self.minutos, self.cuenta = minutos, cuenta
        self.nueva = nueva  # True si se bloqueó recién (no un intento durante el bloqueo)


class CuentaDesactivada(Exception):
    def __init__(self, cuenta: "Usuario"):
        super().__init__("Cuenta desactivada")
        self.cuenta = cuenta


def ahora() -> datetime:
    """UTC sin zona: así se compara igual en SQLite y PostgreSQL."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- Contraseñas --------------------------------------------------------------------------

def hash_clave(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt(RONDAS_BCRYPT)).decode()


def clave_correcta(clave: str, clave_hash: str) -> bool:
    datos = clave.encode()
    if len(datos) > MAX_BYTES_CLAVE:
        return False
    return bcrypt.checkpw(datos, clave_hash.encode())


_HASH_FALSO = None


def _comparar_con_falso(clave: str):
    """Con un usuario que no existe se hace igual el cálculo, para no delatar qué usuarios existen."""
    global _HASH_FALSO
    _HASH_FALSO = _HASH_FALSO or hash_clave(secrets.token_hex(8))
    clave_correcta(clave, _HASH_FALSO)


def validar_clave(clave: str, usuario: str = "") -> None:
    if len(clave) < MIN_LARGO_CLAVE:
        raise ErrorUsuario(f"La contraseña debe tener al menos {MIN_LARGO_CLAVE} caracteres")
    if len(clave.encode()) > MAX_BYTES_CLAVE:
        raise ErrorUsuario("La contraseña es demasiado larga")
    if usuario and clave.lower() == usuario.lower():
        raise ErrorUsuario("La contraseña no puede ser igual al usuario")


def clave_temporal() -> str:
    """Ej. "Kx7m-Pq2r-9Rtw": fácil de dictar, sin caracteres que se confunden."""
    return "-".join("".join(secrets.choice(_SIN_AMBIGUOS) for _ in range(4)) for _ in range(3))


# --- Datos de la cuenta ---------------------------------------------------------------------

def _normalizar_usuario(usuario: str) -> str:
    usuario = usuario.strip().lower()
    if not _USUARIO.match(usuario):
        raise ErrorUsuario("El usuario debe tener de 3 a 30 caracteres: letras, números, punto, guion o guion bajo")
    return usuario


def _normalizar_correo(correo: str | None, obligatorio: bool = True) -> str | None:
    correo = (correo or "").strip().lower()
    if not correo:
        if obligatorio:
            raise ErrorUsuario("Falta el correo")
        return None
    if not _CORREO.match(correo) or len(correo) > 120:
        raise ErrorUsuario("El correo no es válido")
    return correo


def _validar_rol(rol: str) -> str:
    if rol not in NIVEL:
        raise ErrorUsuario("El rol debe ser Admin, Auditor o Visor")
    return rol


def _validar_nombre(nombre: str) -> str:
    nombre = " ".join(nombre.split())
    if not 2 <= len(nombre) <= 80:
        raise ErrorUsuario("El nombre debe tener de 2 a 80 caracteres")
    return nombre


def _correo_libre(db: Session, correo: str | None, excepto: int | None = None):
    if correo and db.scalar(select(Usuario.id).where(Usuario.correo == correo, Usuario.id != (excepto or 0))):
        raise ErrorUsuario("Ya hay otra cuenta con ese correo")


def buscar(db: Session, usuario: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.usuario == (usuario or "").strip().lower()))


def hay_usuarios(db: Session) -> bool:
    return db.scalar(select(func.count()).select_from(Usuario)) > 0


def _admins_activos(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Usuario).where(Usuario.rol == ADMIN, Usuario.activo))


def crear(db: Session, usuario: str, nombre: str, correo: str | None, rol: str, clave: str,
          debe_cambiar_clave: bool, correo_obligatorio: bool = True) -> Usuario:
    usuario = _normalizar_usuario(usuario)
    correo = _normalizar_correo(correo, correo_obligatorio)
    if db.scalar(select(Usuario.id).where(Usuario.usuario == usuario)):
        raise ErrorUsuario("Ese usuario ya existe")
    _correo_libre(db, correo)
    u = Usuario(usuario=usuario, nombre=_validar_nombre(nombre), correo=correo, rol=_validar_rol(rol),
                clave_hash=hash_clave(clave), activo=True, debe_cambiar_clave=debe_cambiar_clave,
                intentos_fallidos=0, fallos_auditor=0, creado=ahora())
    db.add(u)
    db.commit()
    return u


def crear_admin_inicial(db: Session, acceso: str) -> Usuario | None:
    """Con KSECURE_ACCESO="usuario:contraseña" y la base sin cuentas, crea ese administrador.

    Al entrar debe cambiar la contraseña y registrar su correo. Si ya hay cuentas, no hace nada.
    """
    if ":" not in acceso:
        raise ValueError('KSECURE_ACCESO debe tener la forma "usuario:contraseña"')
    if hay_usuarios(db):
        return None
    usuario, clave = acceso.split(":", 1)
    if not clave:
        raise ValueError("KSECURE_ACCESO no trae contraseña")
    return crear(db, usuario, usuario, None, ADMIN, clave, debe_cambiar_clave=True, correo_obligatorio=False)


def configurar_primer_admin(db: Session, usuario: str, nombre: str, correo: str, clave: str) -> Usuario:
    """Pantalla de configuración inicial: solo funciona mientras no exista ninguna cuenta."""
    if hay_usuarios(db):
        raise ErrorUsuario("K-Secure ya está configurado")
    validar_clave(clave, usuario)
    return crear(db, usuario, nombre, correo, ADMIN, clave, debe_cambiar_clave=False)


def crear_por_admin(db: Session, usuario: str, nombre: str, correo: str, rol: str) -> tuple[Usuario, str]:
    """Cuenta nueva con contraseña temporal: se muestra una vez y se cambia al primer ingreso."""
    temporal = clave_temporal()
    return crear(db, usuario, nombre, correo, rol, temporal, debe_cambiar_clave=True), temporal


def listar(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.activo.desc(), Usuario.nombre)))


def actualizar(db: Session, usuario_id: int, quien: Usuario, nombre: str, correo: str, rol: str,
               activo: bool) -> Usuario:
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise LookupError
    rol = _validar_rol(rol)
    if u.id == quien.id and (rol != u.rol or not activo):
        raise ErrorUsuario("No puedes cambiar tu propio rol ni desactivar tu cuenta")
    deja_de_ser_admin = u.rol == ADMIN and u.activo and (rol != ADMIN or not activo)
    if deja_de_ser_admin and _admins_activos(db) <= 1:
        raise ErrorUsuario("Debe quedar al menos un administrador activo")
    correo = _normalizar_correo(correo)
    _correo_libre(db, correo, excepto=u.id)
    u.nombre, u.correo, u.rol = _validar_nombre(nombre), correo, rol
    if u.activo and not activo:
        cerrar_sesiones(db, u.id)
    u.activo = activo
    db.commit()
    return u


def restablecer(db: Session, usuario_id: int) -> tuple[Usuario, str]:
    """Nueva contraseña temporal; también desbloquea la cuenta y cierra sus sesiones."""
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise LookupError
    temporal = clave_temporal()
    u.clave_hash, u.debe_cambiar_clave = hash_clave(temporal), True
    u.intentos_fallidos, u.bloqueado_hasta = 0, None
    cerrar_sesiones(db, u.id)
    db.commit()
    return u, temporal


def cambiar_clave(db: Session, usuario_id: int, actual: str | None, nueva: str, token_actual: str | None,
                  correo: str | None = None) -> Usuario:
    """Con una contraseña temporal no se pide la actual (recién se ingresó con ella)."""
    u = db.get(Usuario, usuario_id)
    if not u.debe_cambiar_clave and not clave_correcta(actual or "", u.clave_hash):
        raise ErrorUsuario("La contraseña actual no es correcta")
    validar_clave(nueva, u.usuario)
    if clave_correcta(nueva, u.clave_hash):
        raise ErrorUsuario("La nueva contraseña debe ser distinta de la anterior")
    if u.correo is None:  # el administrador inicial registra su correo aquí
        nuevo = _normalizar_correo(correo)
        _correo_libre(db, nuevo, excepto=u.id)
        u.correo = nuevo
    u.clave_hash, u.debe_cambiar_clave = hash_clave(nueva), False
    # Las demás sesiones abiertas con la contraseña anterior se cierran.
    actual_hash = _hash_token(token_actual) if token_actual else ""
    for s in list(u.sesiones):
        if s.token_hash != actual_hash:
            db.delete(s)
    db.commit()
    return u


# --- Ingreso y sesiones ---------------------------------------------------------------------

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def autenticar(db: Session, usuario: str, clave: str) -> Usuario | None:
    """Devuelve la cuenta si la contraseña es correcta; None si no. Lleva la cuenta de los intentos."""
    u = buscar(db, usuario)
    if u is None:
        _comparar_con_falso(clave)
        return None
    momento = ahora()
    if u.bloqueado_hasta and u.bloqueado_hasta > momento:
        raise CuentaBloqueada(int((u.bloqueado_hasta - momento).total_seconds() // 60) + 1, u)
    if not clave_correcta(clave, u.clave_hash):
        u.intentos_fallidos = (u.intentos_fallidos or 0) + 1
        if u.intentos_fallidos >= MAX_INTENTOS:
            u.intentos_fallidos, u.bloqueado_hasta = 0, momento + BLOQUEO
            db.commit()
            raise CuentaBloqueada(int(BLOQUEO.total_seconds() // 60), u, nueva=True)
        db.commit()
        return None
    if not u.activo:
        raise CuentaDesactivada(u)
    u.intentos_fallidos, u.bloqueado_hasta = 0, None
    db.commit()
    return u


def abrir_sesion(db: Session, u: Usuario) -> str:
    momento = ahora()
    # De paso se borran las sesiones vencidas de todos.
    for vieja in db.scalars(select(Sesion).where(
            (Sesion.expira < momento) | (Sesion.ultimo_uso < momento - INACTIVIDAD))):
        db.delete(vieja)
    token = secrets.token_urlsafe(32)
    u.ultimo_ingreso = momento
    db.add(Sesion(token_hash=_hash_token(token), usuario_id=u.id, creada=momento, ultimo_uso=momento,
                  expira=momento + DURACION_MAXIMA))
    db.commit()
    return token


def usuario_de_sesion(db: Session, token: str | None) -> Usuario | None:
    """La cuenta dueña de la sesión, o None si no existe, venció o la cuenta está desactivada."""
    if not token:
        return None
    s = db.get(Sesion, _hash_token(token))
    if s is None:
        return None
    momento = ahora()
    if s.expira < momento or s.ultimo_uso + INACTIVIDAD < momento or not s.usuario.activo:
        db.delete(s)
        db.commit()
        return None
    if momento - s.ultimo_uso > REFRESCO:
        s.ultimo_uso = momento
        db.commit()
    return s.usuario


def cerrar_sesion(db: Session, token: str | None):
    if token and (s := db.get(Sesion, _hash_token(token))):
        db.delete(s)
        db.commit()


def cerrar_sesiones(db: Session, usuario_id: int):
    for s in db.scalars(select(Sesion).where(Sesion.usuario_id == usuario_id)):
        db.delete(s)


# --- Recuperar la contraseña por correo (RF-14) -------------------------------------------------

def _buscar_cuenta(db: Session, cuenta: str) -> Usuario | None:
    """Por usuario o por correo, sin importar mayúsculas."""
    texto = (cuenta or "").strip().lower()
    if not texto:
        return None
    campo = Usuario.correo if "@" in texto else Usuario.usuario
    return db.scalar(select(Usuario).where(campo == texto))


def pedir_codigo(db: Session, cuenta: str) -> tuple[Usuario, str] | None:
    """Crea un código nuevo y devuelve (cuenta, código) para mandarlo por correo.

    Devuelve None si no corresponde enviarlo: la cuenta no existe, está desactivada, no tiene
    correo o ya pidió demasiados códigos. La web responde lo mismo en todos los casos, así no
    delata qué cuentas existen. Pedir un código nuevo anula el anterior.
    """
    u = _buscar_cuenta(db, cuenta)
    if u is None or not u.activo or not u.correo:
        return None
    momento = ahora()
    db.execute(delete(CodigoRecuperacion).where(CodigoRecuperacion.creado < momento - timedelta(days=1)))
    recientes = list(db.scalars(select(CodigoRecuperacion.creado).where(
        CodigoRecuperacion.usuario_id == u.id, CodigoRecuperacion.creado > momento - timedelta(hours=1))))
    del_dia = db.scalar(select(func.count()).select_from(CodigoRecuperacion))
    if (len(recientes) >= CODIGOS_POR_HORA or del_dia >= CODIGOS_POR_DIA
            or any(c > momento - CODIGO_ESPERA for c in recientes)):
        db.commit()
        return None
    db.execute(update(CodigoRecuperacion).where(CodigoRecuperacion.usuario_id == u.id,
                                                CodigoRecuperacion.usado.is_(False)).values(usado=True))
    codigo = f"{secrets.randbelow(10**6):06d}"
    db.add(CodigoRecuperacion(usuario_id=u.id, codigo_hash=hash_clave(codigo), creado=momento,
                              expira=momento + CODIGO_VIGENCIA, intentos=0, usado=False))
    db.commit()
    return u, codigo


def recuperar_clave(db: Session, cuenta: str, codigo: str, nueva: str) -> Usuario:
    """Con el código del correo crea la contraseña nueva.

    También desbloquea la cuenta, quita la contraseña temporal y cierra todas sus sesiones.
    Cualquier problema con la cuenta o el código da el mismo mensaje.
    """
    validar_clave(nueva)
    codigo = re.sub(r"\D", "", codigo or "")
    u = _buscar_cuenta(db, cuenta)
    vigente = None
    if u is not None and u.activo and len(codigo) == 6:
        vigente = db.scalar(select(CodigoRecuperacion).where(
            CodigoRecuperacion.usuario_id == u.id, CodigoRecuperacion.usado.is_(False),
            CodigoRecuperacion.expira > ahora()).order_by(CodigoRecuperacion.creado.desc()).limit(1))
    if vigente is None:
        _comparar_con_falso(codigo)  # mismo tiempo de respuesta que con una cuenta real
        raise ErrorUsuario(CODIGO_INVALIDO)
    if not clave_correcta(codigo, vigente.codigo_hash):
        vigente.intentos = (vigente.intentos or 0) + 1
        vigente.usado = vigente.intentos >= CODIGO_INTENTOS
        db.commit()
        raise ErrorUsuario(CODIGO_INVALIDO)
    validar_clave(nueva, u.usuario)  # antes de gastar el código: si falla, se puede reintentar
    vigente.usado = True
    u.clave_hash, u.debe_cambiar_clave = hash_clave(nueva), False
    u.intentos_fallidos, u.bloqueado_hasta = 0, None
    cerrar_sesiones(db, u.id)
    db.commit()
    return u


def publico(u: Usuario) -> dict:
    """Lo que se le muestra al navegador de una cuenta (nunca el hash)."""
    momento = ahora()
    return {
        "id": u.id, "usuario": u.usuario, "nombre": u.nombre, "correo": u.correo, "rol": u.rol,
        "activo": u.activo, "debe_cambiar_clave": u.debe_cambiar_clave,
        "bloqueado": bool(u.bloqueado_hasta and u.bloqueado_hasta > momento),
        "ultimo_ingreso": u.ultimo_ingreso.isoformat(timespec="seconds") + "Z" if u.ultimo_ingreso else None,
    }
