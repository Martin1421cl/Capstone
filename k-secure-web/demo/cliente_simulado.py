"""Cliente simulado para probar K-Secure: "Comercial Austral Demo SpA", una empresa FICTICIA.

Crea 11 tablas de un ERP chileno (clientes, RRHH, remuneraciones, pagos, ventas, proveedores,
mesa de ayuda, flota, integraciones, accesos e inventario) con datos 100 % sintéticos:
nombres inventados, RUT con dígito verificador correcto pero al azar, tarjetas que pasan Luhn
pero no existen, etc. Incluye columnas con nombres crípticos, datos escondidos en texto libre
y trampas (folios, códigos de barra, montos) para medir falsos positivos.

Siempre genera los mismos datos (semilla fija): dos cargas iguales se pueden comparar.

Uso (desde la carpeta k-secure-web, con el entorno virtual activado):

  # En Neon (PostgreSQL en la nube). Pega la connection string entre comillas.
  python demo/cliente_simulado.py --url "postgresql://usuario:clave@ep-xxx.neon.tech/cliente_simulado?sslmode=require"

  # Lo mismo, y además crea el usuario de solo lectura que usará K-Secure
  python demo/cliente_simulado.py --url "..." --lector-clave "Lector-K-Secure-2026"

  # En un archivo SQLite, para subirlo en "Escanear archivos" sin internet
  python demo/cliente_simulado.py --sqlite cliente_simulado.db

  # Más volumen (por defecto ~18.000 filas; --escala 5 son ~90.000)
  python demo/cliente_simulado.py --url "..." --escala 5

OJO: borra y vuelve a crear SOLO sus 11 tablas. Úsalo en una base dedicada (ej. "cliente_simulado").
No subas al repo la base generada (.db): trae claves y tokens falsos con forma real, y los
escáneres de secretos de GitHub podrían bloquear el push.
"""

import argparse
import random
import sqlite3
import string
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

SEMILLA = 2026
EMPRESA = "Comercial Austral Demo SpA"
DOMINIO = "australdemo.cl"
USUARIO_LECTOR = "ksecure_lector"

NOMBRES = ["Sofía", "Isidora", "Agustina", "Florencia", "Catalina", "Josefa", "Emilia", "Antonella", "Martina",
           "Javiera", "Fernanda", "Valentina", "Constanza", "Camila", "Francisca", "Daniela", "Carolina", "Paula",
           "Benjamín", "Vicente", "Martín", "Matías", "Joaquín", "Agustín", "Tomás", "Maximiliano", "Lucas",
           "Diego", "Sebastián", "Felipe", "Nicolás", "Cristóbal", "Ignacio", "Francisco", "Rodrigo", "Gonzalo",
           "Claudio", "Patricio", "Luis", "Jorge", "Pedro", "Juan Pablo", "María José", "Ana María"]
APELLIDOS = ["González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva", "Martínez", "Sepúlveda",
             "Morales", "Rodríguez", "López", "Fuentes", "Hernández", "Torres", "Araya", "Flores", "Espinoza",
             "Valenzuela", "Castillo", "Tapia", "Reyes", "Gutiérrez", "Castro", "Pizarro", "Álvarez", "Vásquez",
             "Sánchez", "Fernández", "Ramírez", "Carrasco", "Gómez", "Cortés", "Herrera", "Núñez", "Jara",
             "Vergara", "Rivera", "Figueroa", "Riquelme", "Bravo", "Olivares", "Cáceres", "Molina", "Saavedra"]
COMUNAS = ["Santiago", "Providencia", "Las Condes", "Ñuñoa", "Maipú", "La Florida", "Puente Alto", "San Miguel",
           "Valparaíso", "Viña del Mar", "Concepción", "Talcahuano", "Temuco", "La Serena", "Antofagasta",
           "Rancagua", "Talca", "Puerto Montt", "Iquique", "Chillán", "Osorno", "Punta Arenas"]
CALLES = ["Av. Libertador Bernardo O'Higgins", "Av. Providencia", "Los Carrera", "Av. Pajaritos", "Chacabuco",
          "Colo Colo", "Av. Alemania", "Prat", "Balmaceda", "Freire", "Av. Matta", "Los Aromos", "El Roble",
          "Las Acacias", "Av. Vicuña Mackenna", "San Martín", "Errázuriz", "Manuel Montt"]
BANCOS = ["BancoEstado", "Santander", "BCI", "Scotiabank", "Itaú", "Banco de Chile", "Security", "Falabella",
          "Ripley", "BICE", "Consorcio", "Internacional"]
DOMINIOS_PERSONALES = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.es", "live.cl", "icloud.com"]
CARGOS = [("Vendedor", "Ventas", 650_000), ("Ejecutivo de cuentas", "Ventas", 1_100_000),
          ("Cajero", "Tiendas", 560_000), ("Bodeguero", "Logística", 600_000), ("Conductor", "Logística", 780_000),
          ("Analista contable", "Finanzas", 1_250_000), ("Tesorero", "Finanzas", 1_600_000),
          ("Analista de RRHH", "Personas", 1_150_000), ("Soporte TI", "Tecnología", 1_050_000),
          ("Desarrollador", "Tecnología", 1_900_000), ("Jefe de tienda", "Tiendas", 1_400_000),
          ("Gerente comercial", "Gerencia", 3_800_000)]
AFPS = ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno"]
SALUD = ["Fonasa", "Banmédica", "Colmena", "Consalud", "Cruz Blanca", "Nueva Masvida", "Vida Tres"]
MARCAS = [("Toyota", ["Hilux", "Yaris", "RAV4"]), ("Chevrolet", ["Sail", "Colorado", "N400"]),
          ("Hyundai", ["Accent", "Porter", "Tucson"]), ("Nissan", ["NP300", "Versa", "Kicks"]),
          ("Peugeot", ["Partner", "208", "Boxer"]), ("Suzuki", ["Swift", "Baleno"])]
PRODUCTOS = ["Martillo carpintero 16 oz", "Taladro percutor 650 W", "Set destornilladores 12 pzs",
             "Cinta métrica 5 m", "Pintura látex blanco 1 gl", "Brocha 2 pulgadas", "Silicona transparente",
             "Guantes de seguridad talla L", "Escalera aluminio 5 peldaños", "Alargador 3 m",
             "Ampolleta LED 9 W", "Candado bronce 40 mm", "Manguera jardín 15 m", "Llave inglesa 10 pulgadas",
             "Lija al agua N° 120", "Tornillo volcanita 6x1 (100 u)", "Cemento 25 kg", "Sierra caladora 500 W"]

# Letras de patentes nuevas (sin vocales ni M, N, Ñ, Q).
_LETRAS_PATENTE = "BCDFGHJKLPRSTVWXYZ"
_EJEMPLOS_RUT = {12345678, 87654321, 11111111, 22222222}
_EJEMPLOS_FONO = {"912345678", "987654321"}


@dataclass
class Tabla:
    nombre: str
    columnas: list[tuple[str, str]]  # (nombre, tipo SQL)
    llave: str
    filas: list[tuple] = field(default_factory=list)

    def ddl(self) -> str:
        cols = ",\n  ".join(f"{c} {t}" for c, t in self.columnas)
        return f"CREATE TABLE {self.nombre} (\n  {cols},\n  PRIMARY KEY ({self.llave})\n)"


# --- Datos con forma real ------------------------------------------------------------------

def dv_rut(cuerpo: int) -> str:
    """Dígito verificador con Módulo 11."""
    factores, suma = [2, 3, 4, 5, 6, 7], 0
    for i, d in enumerate(reversed(str(cuerpo))):
        suma += int(d) * factores[i % 6]
    resto = 11 - suma % 11
    return {11: "0", 10: "K"}.get(resto, str(resto))


def _ascii(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c for c in sin_tildes.lower() if c.isalnum())


class Generador:
    def __init__(self, semilla: int):
        self.r = random.Random(semilla)
        self._usados: set = set()

    def unico(self, crear, valido=lambda v: True):
        """Repite crear() hasta obtener un valor válido que no se haya usado (RUT, tarjetas, cuentas...)."""
        while True:
            v = crear()
            if valido(v) and v not in self._usados:
                self._usados.add(v)
                return v

    # Personas y empresas
    def nombre(self) -> tuple[str, str, str]:
        return self.r.choice(NOMBRES), self.r.choice(APELLIDOS), self.r.choice(APELLIDOS)

    def cuerpo_rut(self, empresa: bool = False) -> int:
        desde, hasta = (76_000_000, 77_999_999) if empresa else (5_000_000, 26_999_999)
        return self.unico(lambda: self.r.randint(desde, hasta), lambda c: c not in _EJEMPLOS_RUT)

    @staticmethod
    def rut_con_puntos(cuerpo: int) -> str:
        return f"{cuerpo:,}".replace(",", ".") + "-" + dv_rut(cuerpo)

    @staticmethod
    def rut_sin_puntos(cuerpo: int) -> str:
        return f"{cuerpo}-{dv_rut(cuerpo)}"

    def celular(self) -> str:
        n = self.unico(lambda: "9" + str(self.r.randint(3, 9)) + "".join(self.r.choices(string.digits, k=7)),
                       lambda n: n not in _EJEMPLOS_FONO)
        formato = self.r.random()
        if formato < 0.5:
            return f"+56 9 {n[1:5]} {n[5:]}"
        if formato < 0.75:
            return f"+56{n}"
        return f"{n[0]} {n[1:5]} {n[5:]}"

    def fijo(self) -> str:
        if self.r.random() < 0.5:
            return f"+56 2 2{self.r.randint(100, 999)} {self.r.randint(1000, 9999)}"
        area = self.r.choice(["32", "33", "41", "42", "45", "51", "55", "61", "64", "71", "75"])
        return f"+56 {area} {self.r.randint(200, 299)} {self.r.randint(1000, 9999)}"

    def email_personal(self, nombre: str, apellido: str) -> str:
        n, a = _ascii(nombre.split()[0]), _ascii(apellido)
        return self.unico(lambda: f"{n}{self.r.choice(['.', '_', ''])}{a}{self.r.randint(1, 999)}"
                                  f"@{self.r.choice(DOMINIOS_PERSONALES)}")

    def email_corporativo(self, nombre: str, apellido: str, ap_materno: str) -> str:
        base = f"{_ascii(nombre)[0]}{_ascii(apellido)}"
        # jperez, jperezg, jperezgo... y si todas están tomadas, con un número (jperez27)
        return self.unico(lambda: f"{base}{_ascii(ap_materno)[:self.r.randint(0, 2)]}"
                                  f"{self.r.choice(['', '', '', str(self.r.randint(2, 99))])}@{DOMINIO}")

    def tarjeta(self) -> str:
        """Número que pasa Luhn y tiene marca real, pero inventado (no es una tarjeta emitida)."""
        def crear():
            marca = self.r.random()
            if marca < 0.55:
                prefijo, largo = "4", 16
            elif marca < 0.9:
                prefijo, largo = str(self.r.randint(51, 55)), 16
            else:
                prefijo, largo = self.r.choice(["34", "37"]), 15
            cuerpo = prefijo + "".join(self.r.choices(string.digits, k=largo - len(prefijo) - 1))
            return cuerpo + _digito_luhn(cuerpo)
        n = self.unico(crear)
        if len(n) == 15:  # Amex: 4-6-5
            return f"{n[:4]} {n[4:10]} {n[10:]}"
        sep = self.r.choice([" ", "-", ""])
        return sep.join(n[i:i + 4] for i in range(0, 16, 4))

    def cuenta(self) -> str:
        n = self.unico(lambda: str(self.r.randint(1, 9)) + "".join(self.r.choices(string.digits, k=self.r.randint(7, 11))))
        if self.r.random() < 0.15:  # algunos bancos la muestran con guiones
            return f"{n[:2]}-{n[2:5]}-{n[5:]}"
        return n

    def patente(self, antigua: bool = False) -> str:
        if antigua:
            letras = "".join(self.r.choices(string.ascii_uppercase, k=2))
            return self.unico(lambda: f"{letras}{self.r.randint(10, 99)}{self.r.randint(10, 99)}")
        texto = self.unico(lambda: "".join(self.r.choices(_LETRAS_PATENTE, k=4)) + f"{self.r.randint(10, 99)}")
        return self.r.choice([texto, f"{texto[:4]}-{texto[4:]}", f"{texto[:2]}·{texto[2:4]}·{texto[4:]}"])

    def direccion(self) -> tuple[str, str]:
        depto = f", depto {self.r.randint(101, 2405)}" if self.r.random() < 0.35 else ""
        return f"{self.r.choice(CALLES)} {self.r.randint(10, 9999)}{depto}", self.r.choice(COMUNAS)

    def fecha(self, desde: date, hasta: date) -> date:
        return desde + timedelta(days=self.r.randint(0, (hasta - desde).days))

    def momento(self, desde: date, hasta: date) -> datetime:
        d = self.fecha(desde, hasta)
        return datetime(d.year, d.month, d.day, self.r.randint(7, 22), self.r.randint(0, 59), self.r.randint(0, 59))

    def ean13(self) -> str:
        def crear():
            cuerpo = "780" + "".join(self.r.choices(string.digits, k=9))
            suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(cuerpo))
            return cuerpo + str((10 - suma % 10) % 10)
        return self.unico(crear)

    def aws_access_key(self) -> str:
        return "AKIA" + "".join(self.r.choices(string.ascii_uppercase + "234567", k=16))

    def aws_secret(self) -> str:
        return "".join(self.r.choices(string.ascii_letters + string.digits + "+/", k=40))

    def github_token(self) -> str:
        return "ghp_" + "".join(self.r.choices(string.ascii_letters + string.digits, k=36))


def _digito_luhn(cuerpo: str) -> str:
    total = 0
    for i, d in enumerate(int(c) for c in reversed(cuerpo)):
        if i % 2 == 0:
            d *= 2
            d = d - 9 if d > 9 else d
        total += d
    return str((10 - total % 10) % 10)


# --- Las 11 tablas -------------------------------------------------------------------------

DESDE, HASTA = date(2024, 1, 1), date(2026, 10, 15)


def generar(escala: float = 1, semilla: int = SEMILLA) -> list[Tabla]:
    g = Generador(semilla)
    r = g.r
    n = lambda base: max(1, round(base * escala))

    # Clientes (personas y empresas). Columnas crípticas: id_tri es el RUT, fon_1 el teléfono.
    clientes = Tabla("cli_maestro", [
        ("cod_cli", "VARCHAR(10)"), ("nom_cli", "VARCHAR(120)"), ("id_tri", "VARCHAR(15)"), ("tip_cli", "VARCHAR(2)"),
        ("fon_1", "VARCHAR(20)"), ("eml_1", "VARCHAR(120)"), ("dir_desp", "VARCHAR(150)"), ("cmn_desp", "VARCHAR(40)"),
        ("fec_alta", "DATE"), ("obs_cli", "TEXT")], "cod_cli")
    for i in range(1, n(2000) + 1):
        empresa = r.random() < 0.15
        nom, ap, am = g.nombre()
        if empresa:
            razon = f"{r.choice(['Inversiones', 'Constructora', 'Transportes', 'Comercial', 'Servicios'])} {ap} {r.choice(['SpA', 'Ltda.', 'y Cía. Ltda.'])}"
            rut, fono = g.rut_con_puntos(g.cuerpo_rut(empresa=True)), g.fijo()
            mail = f"{r.choice(['contacto', 'facturacion', 'compras'])}@{_ascii(ap)}{r.randint(1, 99)}.cl"
        else:
            razon = f"{nom} {ap} {am}"
            rut, fono = g.rut_con_puntos(g.cuerpo_rut()), g.celular()
            mail = g.email_personal(nom, ap) if r.random() < 0.9 else None
        calle, comuna = g.direccion()
        obs = r.choice([None, None, None, "Cliente frecuente", "Despachar después de las 15:00",
                        f"Llamar antes de despachar al {g.celular()}",
                        f"Autoriza retiro: {r.choice(NOMBRES)} {r.choice(APELLIDOS)}, RUT {g.rut_con_puntos(g.cuerpo_rut())}"])
        clientes.filas.append((f"CL{i:06d}", razon, rut, "PJ" if empresa else "PN", fono, mail, calle, comuna,
                               g.fecha(DESDE, HASTA), obs))

    # RRHH: el RUN va sin puntos, como lo exportan muchos sistemas de remuneraciones.
    empleados = Tabla("rh_pers", [
        ("legajo", "INTEGER"), ("run", "VARCHAR(12)"), ("nombres", "VARCHAR(60)"), ("ap_paterno", "VARCHAR(40)"),
        ("ap_materno", "VARCHAR(40)"), ("fec_nac", "DATE"), ("cargo", "VARCHAR(40)"), ("area", "VARCHAR(30)"),
        ("fec_ingreso", "DATE"), ("sueldo_base", "INTEGER"), ("afp", "VARCHAR(20)"), ("salud", "VARCHAR(20)"),
        ("banco", "VARCHAR(30)"), ("nro_cta", "VARCHAR(20)"), ("mail_pers", "VARCHAR(120)"),
        ("mail_corp", "VARCHAR(120)"), ("fono_cel", "VARCHAR(20)"), ("contacto_emerg", "VARCHAR(80)"),
        ("fono_emerg", "VARCHAR(20)")], "legajo")
    for legajo in range(1001, 1001 + n(250)):
        nom, ap, am = g.nombre()
        cargo, area, sueldo = r.choice(CARGOS)
        empleados.filas.append((
            legajo, g.rut_sin_puntos(g.cuerpo_rut()), nom, ap, am, g.fecha(date(1965, 1, 1), date(2005, 12, 31)),
            cargo, area, g.fecha(date(2012, 1, 1), HASTA), int(round(sueldo * r.uniform(0.9, 1.25), -3)),
            r.choice(AFPS), r.choice(SALUD), r.choice(BANCOS), g.cuenta(), g.email_personal(nom, ap),
            g.email_corporativo(nom, ap, am), g.celular(), f"{r.choice(NOMBRES)} {ap}",
            g.celular() if r.random() < 0.7 else g.fijo()))

    # Remuneraciones de un sistema antiguo: el RUT viene partido en número y dígito verificador.
    liquidaciones = Tabla("rem_liquidaciones", [
        ("id_liq", "INTEGER"), ("periodo", "VARCHAR(6)"), ("legajo", "INTEGER"), ("rut_num", "INTEGER"),
        ("rut_dv", "VARCHAR(1)"), ("haberes", "INTEGER"), ("descuentos", "INTEGER"), ("liquido", "INTEGER"),
        ("banco_dep", "VARCHAR(30)"), ("cta_dep", "VARCHAR(20)")], "id_liq")
    id_liq = 1
    for e in empleados.filas:
        cuerpo, dv = e[1].split("-")
        for mes in range(4, 10):
            haberes = int(round(e[9] * r.uniform(1.0, 1.3), -3))
            descuentos = int(round(haberes * r.uniform(0.18, 0.24), -3))
            liquidaciones.filas.append((id_liq, f"2026{mes:02d}", e[0], int(cuerpo), dv, haberes, descuentos,
                                        haberes - descuentos, e[12], e[13]))
            id_liq += 1

    # Pagos: ref_pago guarda el número de tarjeta completo (mala práctica real) o una referencia de transferencia.
    pagos = Tabla("fi_pagos", [
        ("id_pago", "INTEGER"), ("fec_pago", "TIMESTAMP"), ("cod_cli", "VARCHAR(10)"), ("medio", "VARCHAR(3)"),
        ("ref_pago", "VARCHAR(30)"), ("cod_aut", "VARCHAR(6)"), ("monto", "INTEGER"), ("estado", "VARCHAR(12)")],
        "id_pago")
    for i in range(1, n(4000) + 1):
        medio = r.choices(["TC", "TD", "TRF", "EFE"], weights=[40, 30, 20, 10])[0]
        ref = {"TC": g.tarjeta, "TD": g.tarjeta,
               "TRF": lambda: f"TRF-{r.randint(2024, 2026)}-{r.randint(1, 999_999):06d}",
               "EFE": lambda: None}[medio]()
        pagos.filas.append((i, g.momento(DESDE, HASTA), r.choice(clientes.filas)[0], medio, ref,
                            f"{r.randint(0, 999_999):06d}" if medio in ("TC", "TD") else None,
                            r.randint(2, 900) * 990, r.choices(["APROBADO", "RECHAZADO", "ANULADO"], [90, 7, 3])[0]))

    # Ventas: folios de 7 dígitos (trampa: parecen números de cuenta) y RUT del receptor solo en facturas.
    ventas = Tabla("vt_docs", [
        ("folio", "INTEGER"), ("tip_doc", "VARCHAR(3)"), ("fec_emi", "DATE"), ("cod_cli", "VARCHAR(10)"),
        ("rut_rec", "VARCHAR(15)"), ("neto", "INTEGER"), ("iva", "INTEGER"), ("total", "INTEGER"),
        ("glosa", "VARCHAR(120)")], "folio")
    empresas = [c for c in clientes.filas if c[3] == "PJ"] or clientes.filas
    for folio in range(3_104_220, 3_104_220 + n(6000)):
        factura = r.random() < 0.3
        cliente = r.choice(empresas if factura else clientes.filas)
        neto = r.randint(3, 2000) * 840
        ventas.filas.append((folio, "FAC" if factura else "BOL", g.fecha(DESDE, HASTA), cliente[0],
                             cliente[2] if factura else None, neto, round(neto * 0.19), round(neto * 1.19),
                             f"Venta {r.choice(PRODUCTOS).lower()} y otros"))

    # Proveedores: empresas (RUT ≥ 50 millones = Interno), casillas de área (Público) y cuentas corrientes.
    proveedores = Tabla("prov_maestro", [
        ("cod_prov", "VARCHAR(8)"), ("razon_social", "VARCHAR(120)"), ("rut_prov", "VARCHAR(15)"),
        ("giro", "VARCHAR(80)"), ("mail_contacto", "VARCHAR(120)"), ("fono_contacto", "VARCHAR(20)"),
        ("banco", "VARCHAR(30)"), ("cta_cte", "VARCHAR(20)"), ("web", "VARCHAR(80)")], "cod_prov")
    for i in range(1, n(120) + 1):
        ap = r.choice(APELLIDOS)
        sitio = f"{_ascii(ap)}{r.choice(['hnos', 'cia', 'ltda', 'spa'])}{i}.cl"
        proveedores.filas.append((
            f"PR{i:05d}", f"{r.choice(['Distribuidora', 'Importadora', 'Ferretería', 'Maderas'])} {ap} Ltda.",
            g.rut_con_puntos(g.cuerpo_rut(empresa=True)), r.choice(["Ferretería", "Construcción", "Transporte", "Importación"]),
            f"{r.choice(['ventas', 'contacto', 'cobranza', 'facturacion'])}@{sitio}", g.fijo(), r.choice(BANCOS),
            g.cuenta(), f"https://www.{sitio}"))

    # Mesa de ayuda: datos sensibles escritos por los propios clientes en texto libre.
    tickets = Tabla("sop_tickets", [
        ("nro_ticket", "INTEGER"), ("fec_ticket", "TIMESTAMP"), ("cod_cli", "VARCHAR(10)"), ("canal", "VARCHAR(10)"),
        ("asunto", "VARCHAR(80)"), ("detalle", "TEXT"), ("estado", "VARCHAR(10)")], "nro_ticket")
    for i in range(50_001, 50_001 + n(800)):
        nom, ap, _ = g.nombre()
        asunto, detalle = r.choice([
            ("Cambio de correo", lambda: f"Hola, necesito cambiar el correo de mi cuenta a {g.email_personal(nom, ap)}. "
                                         f"Mi RUT es {g.rut_con_puntos(g.cuerpo_rut())}."),
            ("Boleta no recibida", lambda: f"No me llegó la boleta folio {r.choice(ventas.filas)[0]}. "
                                           f"Pueden llamarme al {g.celular()}."),
            ("Cobro duplicado", lambda: f"Pagué con la tarjeta {g.tarjeta()} y el cargo aparece dos veces."),
            ("Cobro duplicado", lambda: f"Me cobraron dos veces en la tarjeta terminada en {r.randint(1000, 9999)}."),
            ("Devolución", lambda: f"Por favor depositen la devolución en mi cuenta {g.cuenta()} del banco "
                                   f"{r.choice(BANCOS)}, a nombre de {nom} {ap}."),
            ("Despacho", lambda: "Quiero cambiar la dirección de despacho a {}, {}.".format(*g.direccion())),
            ("Estacionamiento", lambda: f"Mi patente es {g.patente()}, necesito acceso al estacionamiento de la tienda."),
            ("Felicitaciones", lambda: "Muy buena atención en la tienda, gracias."),
            ("Pedido incompleto", lambda: f"El pedido PED-{r.randint(10_000, 99_999)} llegó incompleto, faltan "
                                          f"{r.randint(1, 5)} unidades."),
        ])
        tickets.filas.append((i, g.momento(DESDE, HASTA), r.choice(clientes.filas)[0],
                              r.choice(["web", "correo", "teléfono", "whatsapp"]), asunto, detalle(),
                              r.choice(["abierto", "cerrado", "cerrado", "cerrado"])))

    # Flota: patentes nuevas y antiguas; nro_motor es la trampa (alfanumérico parecido).
    flota = Tabla("flota", [
        ("id_veh", "INTEGER"), ("ppu", "VARCHAR(10)"), ("marca", "VARCHAR(20)"), ("modelo", "VARCHAR(20)"),
        ("anio", "INTEGER"), ("legajo_conductor", "INTEGER"), ("nro_motor", "VARCHAR(20)"), ("km_actual", "INTEGER")],
        "id_veh")
    for i in range(1, n(60) + 1):
        anio = r.randint(2004, 2026)
        marca, modelos = r.choice(MARCAS)
        flota.filas.append((i, g.patente(antigua=anio < 2008), marca, r.choice(modelos), anio,
                            r.choice(empleados.filas)[0],
                            f"{r.choice(['1KD', '2TR', 'QR25', 'D4CB', 'K14B'])}{r.randint(100_000, 999_999)}",
                            r.randint(5_000, 420_000)))

    # Integraciones: credenciales guardadas en texto plano (lo que un DLP debe encontrar sí o sí).
    integraciones = Tabla("sys_integraciones", [
        ("id", "INTEGER"), ("sistema", "VARCHAR(40)"), ("ambiente", "VARCHAR(10)"), ("endpoint", "VARCHAR(120)"),
        ("credencial", "VARCHAR(120)"), ("notas", "TEXT")], "id")
    sistemas = [("Respaldo S3", "https://s3.sa-east-1.amazonaws.com/austral-respaldos"),
                ("Facturación electrónica", "https://api.facturacion-demo.cl/v2"),
                ("Repositorio ERP", "https://github.com/australdemo/erp-interno"),
                ("Webpay", "https://webpay3g.transbank-demo.cl"),
                ("Correo transaccional", "https://smtp.australdemo.cl"),
                ("Analítica", "https://bi.australdemo.cl")]
    for i in range(1, 13):
        sistema, endpoint = sistemas[(i - 1) % len(sistemas)]
        ambiente = "prod" if i <= 6 else "qa"
        if "S3" in sistema:
            cred, notas = g.aws_access_key(), f"aws_secret_access_key = {g.aws_secret()}"
        elif "Repositorio" in sistema:
            cred, notas = g.github_token(), "Token de despliegue, rotar cada 90 días"
        else:
            cred, notas = None, r.choice(["Credencial en bóveda de TI", "Usa certificado del SII", None])
        integraciones.filas.append((i, sistema, ambiente, endpoint, cred, notas))

    # Accesos: sin datos que K-Secure detecte hoy (las IP no tienen validador). Sirve para medir falsos positivos.
    accesos = Tabla("log_accesos", [
        ("id", "INTEGER"), ("ts", "TIMESTAMP"), ("usuario", "VARCHAR(30)"), ("ip_origen", "VARCHAR(15)"),
        ("accion", "VARCHAR(30)"), ("resultado", "VARCHAR(10)")], "id")
    logins = [e[15].split("@")[0] for e in empleados.filas]  # usuario = parte local del correo corporativo
    for i in range(1, n(3000) + 1):
        accesos.filas.append((i, g.momento(date(2026, 7, 1), HASTA), r.choice(logins),
                              f"{r.choice(['10.0', '192.168', '200.27', '186.10'])}.{r.randint(0, 254)}.{r.randint(1, 254)}",
                              r.choice(["login", "logout", "exportar_reporte", "ver_liquidacion", "editar_cliente"]),
                              r.choices(["ok", "error"], [95, 5])[0]))

    # Inventario: nada sensible. cod_barras (EAN-13, 13 dígitos) es la trampa para el validador de tarjetas.
    inventario = Tabla("inv_productos", [
        ("sku", "VARCHAR(12)"), ("descripcion", "VARCHAR(80)"), ("cod_barras", "VARCHAR(13)"), ("precio", "INTEGER"),
        ("stock", "INTEGER"), ("bodega", "VARCHAR(20)")], "sku")
    for i in range(1, n(500) + 1):
        inventario.filas.append((f"SKU-{i:06d}", f"{r.choice(PRODUCTOS)} ({r.choice(['negro', 'rojo', 'gris', 'estándar'])})",
                                 g.ean13(), r.randint(5, 900) * 90, r.randint(0, 800),
                                 r.choice(["Bodega Central", "Tienda Maipú", "Tienda Concepción", "Tienda Temuco"])))

    return [clientes, empleados, liquidaciones, pagos, ventas, proveedores, tickets, flota,
            integraciones, accesos, inventario]


# --- Carga -----------------------------------------------------------------------------------

def cargar_sqlite(tablas: list[Tabla], ruta: str) -> None:
    def texto(v):  # SQLite no tiene tipo fecha: se guardan como texto ISO
        return v.isoformat(sep=" ") if isinstance(v, datetime) else v.isoformat() if isinstance(v, date) else v

    with sqlite3.connect(ruta) as con:
        for t in tablas:
            con.execute(f"DROP TABLE IF EXISTS {t.nombre}")
            con.execute(t.ddl())
            marcas = ", ".join("?" * len(t.columnas))
            con.executemany(f"INSERT INTO {t.nombre} VALUES ({marcas})", ([texto(v) for v in f] for f in t.filas))
    con.close()


def cargar_postgres(tablas: list[Tabla], url: str, clave_lector: str | None) -> None:
    import psycopg
    from psycopg import sql

    with psycopg.connect(url, connect_timeout=15) as con:
        with con.cursor() as cur:
            for t in tablas:
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(t.nombre)))
                cur.execute(t.ddl())
                columnas = sql.SQL(", ").join(sql.Identifier(c) for c, _ in t.columnas)
                with cur.copy(sql.SQL("COPY {} ({}) FROM STDIN").format(sql.Identifier(t.nombre), columnas)) as copia:
                    for fila in t.filas:
                        copia.write_row(fila)
                print(f"  {t.nombre:<20} {len(t.filas):>7,} filas".replace(",", "."))
            preparar_lector(cur, clave_lector)
        con.commit()


def preparar_lector(cur, clave: str | None) -> None:
    """Usuario que solo puede leer (SELECT): es el que se le pide a un cliente real para K-Secure.

    Con clave lo crea (o le cambia la clave). Sin clave, si ya existe, solo le devuelve el permiso
    de lectura, que se pierde al recrear las tablas.
    """
    from psycopg import sql

    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (USUARIO_LECTOR,))
    existe = cur.fetchone() is not None
    if not existe and not clave:
        return
    cur.execute("SELECT current_database()")
    base = cur.fetchone()[0]
    rol = sql.Identifier(USUARIO_LECTOR)
    if clave:
        accion = "ALTER ROLE {} WITH LOGIN PASSWORD {}" if existe else "CREATE ROLE {} WITH LOGIN PASSWORD {}"
        cur.execute(sql.SQL(accion).format(rol, sql.Literal(clave)))
    cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(base), rol))
    cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(rol))
    cur.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(rol))
    print(f"\nUsuario de solo lectura listo: {USUARIO_LECTOR} (base {base})")


def _host(url: str) -> str:
    """Solo el servidor, para mostrarlo sin la clave."""
    resto = url.split("@", 1)[-1]
    return resto.split("/", 1)[0].split("?", 1)[0]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=f"Crea el cliente simulado de K-Secure ({EMPRESA}, ficticia).")
    destino = p.add_mutually_exclusive_group(required=True)
    destino.add_argument("--url", help="connection string de PostgreSQL / Neon (postgresql://...)")
    destino.add_argument("--sqlite", help="ruta del archivo .db a crear")
    p.add_argument("--escala", type=float, default=1, help="multiplica el volumen (1 = ~18.000 filas)")
    p.add_argument("--lector-clave", help=f"crea el usuario {USUARIO_LECTOR} (solo lectura) con esta clave")
    p.add_argument("--semilla", type=int, default=SEMILLA, help=argparse.SUPPRESS)
    a = p.parse_args(argv)

    if a.lector_clave is not None:
        if a.sqlite:
            p.error("--lector-clave es solo para PostgreSQL (SQLite no tiene usuarios)")
        if len(a.lector_clave) < 12:
            p.error("la clave del lector debe tener al menos 12 caracteres (mayúsculas, minúsculas, números y símbolos)")
    if a.escala <= 0:
        p.error("--escala debe ser mayor que 0")

    tablas = generar(a.escala, a.semilla)
    total = sum(len(t.filas) for t in tablas)
    if a.sqlite:
        Path(a.sqlite).unlink(missing_ok=True)
        cargar_sqlite(tablas, a.sqlite)
        print(f"Listo: {a.sqlite} con {len(tablas)} tablas y {total:,} filas.".replace(",", "."))
        print("Súbelo en K-Secure → Archivos.")
    else:
        print(f"Cargando {EMPRESA} en {_host(a.url)}...")
        try:
            cargar_postgres(tablas, a.url, a.lector_clave)
        except Exception as e:  # mostrar el error del servidor sin el traceback completo
            print(f"\nNo se pudo cargar: {str(e).splitlines()[0]}", file=sys.stderr)
            return 1
        print(f"\nListo: {len(tablas)} tablas y {total:,} filas.".replace(",", "."))
        print("En K-Secure → Base de datos → PostgreSQL, usa el host y la base de la connection string"
              + (f", con el usuario {USUARIO_LECTOR}." if a.lector_clave else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
