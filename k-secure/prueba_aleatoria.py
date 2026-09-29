"""Prueba con datos aleatorios: mide aciertos, pérdidas y falsas alertas.

Genera registros con datos sensibles y "ruido" mezclados al azar (RUT,
celulares, fijos, tarjetas, correos, direcciones, nombres, GPS, montos,
folios, pedidos, IMEI...). Como el generador sabe qué plantó en cada
registro, puede comparar contra lo que detecta el motor.

Los hallazgos se guardan en PostgreSQL (igual que demo.py) con origen
"rand:<semilla>:registro N".

Uso:
    python prueba_aleatoria.py                    # 10 registros, semilla al azar
    python prueba_aleatoria.py --registros 20 --semilla 42
    python prueba_aleatoria.py --con-correo       # activa EmailValidator
    python prueba_aleatoria.py --no-guardar       # no escribe en la BD
"""

import argparse
import random
import re
from collections import Counter
from dataclasses import dataclass

from ksecure.database import init_db
from ksecure.db_service import save_findings_to_db
from ksecure.models import DataType, RiskLevel
from ksecure.scanner import KSecureScanner
from ksecure.validators.credit_card import CardValidator, cargar_tabla_bin, luhn_checksum
from ksecure.validators.email import EmailValidator
from ksecure.validators.phone import PhoneValidator
from ksecure.validators.rut import RutValidator, calcular_dv

NOMBRES = ["Camila", "Matías", "Valentina", "Benjamín", "Javiera", "Vicente", "Catalina",
           "Tomás", "Fernanda", "Joaquín", "Isidora", "Martín", "Antonia", "Diego", "Florencia"]
APELLIDOS = ["González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva",
             "Martínez", "Sepúlveda", "Morales", "Rodríguez", "López", "Fuentes", "Araya"]
VIAS = ["Av.", "Avenida", "Calle", "Pasaje", "Camino"]
CALLES = ["Libertador Bernardo O'Higgins", "Providencia", "Los Carrera", "Irarrázaval",
          "Vicuña Mackenna", "Gran Avenida", "Pedro de Valdivia", "Colón", "Brasil", "Prat"]
COMUNAS = ["Santiago", "Ñuñoa", "Maipú", "Puente Alto", "Concepción", "Valparaíso",
           "Viña del Mar", "Temuco", "Antofagasta", "La Florida"]
DOMINIOS = ["gmail.com", "hotmail.com", "outlook.cl", "empresa.cl", "duocuc.cl", "uc.cl", "yahoo.es"]
PALABRA_TIPO = {"credito": "crédito", "debito": "débito", "prepago": "prepago"}

CATEGORIA_POR_TIPO = {
    DataType.RUT: "RUT",
    DataType.TELEFONO_MOVIL: "Teléfono",
    DataType.CORREO_ELECTRONICO: "Correo",
    DataType.TARJETA_CREDITO: "Tarjeta",
    DataType.TARJETA_DEBITO: "Tarjeta",
    DataType.TARJETA_PREPAGO: "Tarjeta",
    DataType.TARJETA_NO_DETERMINADA: "Tarjeta",
}
TIPO_TARJETA = {
    DataType.TARJETA_CREDITO: "credito",
    DataType.TARJETA_DEBITO: "debito",
    DataType.TARJETA_PREPAGO: "prepago",
}


@dataclass
class Plantado:
    categoria: str          # qué se generó (ej. "rut_valido", "monto")
    texto: str              # cómo aparece en el registro
    clave: str              # dígitos (o correo) para cruzar con los hallazgos
    esperado: str | None    # categoría que DEBERÍA detectarse (None = nada)
    tipo_real: str | None = None  # para tarjetas: credito / debito / prepago
    detectado: bool = False


def clave_de(valor: str) -> str:
    return re.sub(r"[^0-9K]", "", valor.upper())


def digitos(rng, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def completar_luhn(prefijo: str) -> str:
    return next(prefijo + d for d in "0123456789" if luhn_checksum(prefijo + d))


def con_etiqueta(rng, etiquetas: list[str], valor: str) -> str:
    etiqueta = rng.choice(etiquetas + [""])
    return f"{etiqueta}: {valor}" if etiqueta else valor


# --------------------------- Generadores ---------------------------------

def gen_rut(rng, valido: bool) -> Plantado:
    cuerpo = rng.randint(1_000_000, 26_000_000)
    dv = calcular_dv(cuerpo)
    if not valido:
        dv = rng.choice([d for d in "0123456789K" if d != dv])
    cuerpo_str = f"{cuerpo:,}".replace(",", ".") if rng.random() < 0.6 else str(cuerpo)
    valor = f"{cuerpo_str}-{dv if rng.random() < 0.5 else dv.lower()}"
    texto = con_etiqueta(rng, ["RUT", "Rut cliente", "RUN", "Rut trabajador", "Cédula"], valor)
    return Plantado("rut_valido" if valido else "rut_dv_malo", texto, clave_de(valor), "RUT")


def gen_celular(rng) -> Plantado:
    n = "9" + digitos(rng, 8)
    valor = rng.choice([
        f"+56 9 {n[1:5]} {n[5:]}", f"+56{n}", f"56 9 {n[1:5]} {n[5:]}", n, f"9 {n[1:5]} {n[5:]}",
    ])
    texto = con_etiqueta(rng, ["Celular", "Teléfono", "Contacto", "WhatsApp", "cel"], valor)
    return Plantado("celular", texto, clave_de(valor), "Teléfono")


def gen_fijo(rng) -> Plantado:
    if rng.random() < 0.5:
        valor = f"+56 2 2{digitos(rng, 3)} {digitos(rng, 4)}"
    else:
        valor = f"+56 {rng.choice(['32', '41', '45', '55', '71'])} {digitos(rng, 3)} {digitos(rng, 4)}"
    texto = con_etiqueta(rng, ["Teléfono fijo", "Oficina", "Fono"], valor)
    return Plantado("fijo", texto, clave_de(valor), None)


def _numero_tarjeta(rng) -> tuple[str, str, str | None]:
    """Retorna (número, marca, tipo_real)."""
    tabla = cargar_tabla_bin()
    if tabla and rng.random() < 0.4:
        bin_, info = rng.choice(list(tabla.items()))
        largo = 15 if info["marca"] == "American Express" else 16
        return completar_luhn(bin_ + digitos(rng, largo - len(bin_) - 1)), info["marca"], info["tipo"]

    marca, prefijo, largo, tipo = rng.choice([
        ("Visa", "4" + str(rng.randint(0, 9)), 16, None),
        ("Mastercard", str(rng.randint(51, 55)), 16, None),
        ("Mastercard", str(rng.randint(2221, 2720)), 16, None),
        ("American Express", rng.choice(["34", "37"]), 15, "credito"),
        ("Maestro", rng.choice(["5018", "6304", "6759"]), 16, "debito"),
        ("Visa Electron", rng.choice(["4508", "4913", "4917"]), 16, "debito"),
        ("Discover", "6011", 16, None),
    ])
    tipo = tipo or rng.choice(["credito", "debito"])
    numero = completar_luhn(prefijo + digitos(rng, largo - len(prefijo) - 1))
    return numero, marca, tipo


def _formatear_tarjeta(rng, numero: str) -> str:
    estilo = rng.choice(["junto", "espacios", "guiones"])
    if estilo == "junto":
        return numero
    grupos = ([numero[:4], numero[4:10], numero[10:]] if len(numero) == 15
              else [numero[i:i + 4] for i in range(0, len(numero), 4)])
    return (" " if estilo == "espacios" else "-").join(grupos)


def gen_tarjeta(rng, luhn_valido: bool) -> Plantado:
    numero, marca, tipo = _numero_tarjeta(rng)
    if not luhn_valido:
        numero = numero[:-1] + str((int(numero[-1]) + rng.randint(1, 9)) % 10)
    valor = _formatear_tarjeta(rng, numero)
    etiqueta = rng.choice([f"Tarjeta de {PALABRA_TIPO[tipo]}", "Tarjeta", f"Pago con {marca}", "N° tarjeta", ""])
    texto = f"{etiqueta} {valor}".strip()
    if luhn_valido:
        return Plantado("tarjeta_valida", texto, numero, "Tarjeta", tipo_real=tipo)
    return Plantado("tarjeta_luhn_malo", texto, numero, None)


def gen_correo(rng) -> Plantado:
    usuario = f"{rng.choice(NOMBRES)}.{rng.choice(APELLIDOS)}{rng.choice(['', str(rng.randint(1, 99))])}"
    usuario = usuario.lower().replace("á", "a").replace("é", "e").replace("í", "i") \
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    valor = f"{usuario}@{rng.choice(DOMINIOS)}"
    texto = con_etiqueta(rng, ["Correo", "Email", "Enviar a", "Mail"], valor)
    return Plantado("correo", texto, valor.lower(), "Correo")


def gen_direccion(rng) -> Plantado:
    depto = f", depto {rng.randint(1, 2500)}" if rng.random() < 0.3 else ""
    valor = f"{rng.choice(VIAS)} {rng.choice(CALLES)} {rng.randint(1, 9999)}{depto}, {rng.choice(COMUNAS)}"
    texto = con_etiqueta(rng, ["Dirección", "Domicilio", "Despacho a"], valor)
    return Plantado("direccion", texto, clave_de(valor), "Dirección")


def gen_nombre(rng) -> Plantado:
    valor = f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}"
    texto = con_etiqueta(rng, ["Nombre", "Titular", "Paciente", "Cliente"], valor)
    return Plantado("nombre", texto, "", "Nombre")


def gen_gps(rng) -> Plantado:
    valor = f"{rng.uniform(-56, -17.5):.4f}, {rng.uniform(-75.5, -66.5):.4f}"
    texto = con_etiqueta(rng, ["Ubicación", "GPS", "Coordenadas"], valor)
    return Plantado("gps", texto, clave_de(valor), "Ubicación")


def gen_ruido(rng) -> Plantado:
    tipo = rng.choice(["monto", "folio", "pedido", "imei", "codigo_postal", "fecha"])
    if tipo == "monto":
        n = rng.randint(1_000, 999_999_999)
        valor = f"${n:,}".replace(",", ".") if rng.random() < 0.5 else str(n)
        texto = f"{rng.choice(['Monto', 'Total', 'Precio'])}: {valor}"
    elif tipo == "folio":
        valor = f"{rng.randint(10_000_000, 99_999_999)}-{rng.choice('0123456789')}"
        texto = f"{rng.choice(['Folio', 'Factura N°', 'Boleta'])} {valor}"
    elif tipo == "pedido":
        valor = digitos(rng, 16)
        texto = f"{rng.choice(['Pedido N°', 'Orden', 'Seguimiento'])} {valor}"
    elif tipo == "imei":
        valor = completar_luhn("35" + digitos(rng, 12))
        texto = f"IMEI {valor}"
    elif tipo == "codigo_postal":
        valor = digitos(rng, 7)
        texto = f"Código postal {valor}"
    else:
        valor = f"{rng.randint(1, 28):02}/{rng.randint(1, 12):02}/{rng.randint(1990, 2026)}"
        texto = f"Fecha: {valor}"
    return Plantado(tipo, texto, clave_de(valor), None)


GENERADORES = [
    (lambda r: gen_rut(r, True), 14),
    (lambda r: gen_rut(r, False), 5),
    (gen_celular, 12),
    (gen_fijo, 5),
    (lambda r: gen_tarjeta(r, True), 14),
    (lambda r: gen_tarjeta(r, False), 5),
    (gen_correo, 10),
    (gen_direccion, 8),
    (gen_nombre, 8),
    (gen_gps, 4),
    (gen_ruido, 15),
]


def generar_registro(rng) -> tuple[str, list[Plantado]]:
    funciones, pesos = zip(*GENERADORES)
    items = [rng.choices(funciones, weights=pesos)[0](rng) for _ in range(rng.randint(1, 4))]
    separador = rng.choice([", ", " | ", "; ", " / "])
    return separador.join(i.texto for i in items), items


# --------------------------- Evaluación ----------------------------------

def emparejar(finding, items: list[Plantado]) -> Plantado | None:
    """Busca qué dato plantado originó el hallazgo."""
    if finding.data_type == DataType.CORREO_ELECTRONICO:
        clave = finding.normalized_value.lower()
    else:
        clave = clave_de(finding.raw_value)
    candidatos = [i for i in items if clave and clave in i.clave]
    categoria = CATEGORIA_POR_TIPO[finding.data_type]
    candidatos.sort(key=lambda i: i.esperado != categoria)  # prioriza el tipo correcto
    return candidatos[0] if candidatos else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registros", type=int, default=10)
    parser.add_argument("--semilla", type=int, default=None)
    parser.add_argument("--con-correo", action="store_true")
    parser.add_argument("--no-guardar", action="store_true")
    args = parser.parse_args()

    semilla = args.semilla if args.semilla is not None else random.randint(1, 999_999)
    rng = random.Random(semilla)

    validators = [RutValidator(), PhoneValidator(), CardValidator()]
    if args.con_correo:
        validators.append(EmailValidator())
    scanner = KSecureScanner(validators)

    todos_findings = []
    todos_items: list[Plantado] = []
    falsos_positivos = []   # (registro, hallazgo, dato que lo originó)
    tipo_tarjeta = Counter()
    riesgo_rut = Counter()
    ejemplos = []

    for n in range(1, args.registros + 1):
        texto, items = generar_registro(rng)
        findings = scanner._scan_text(texto, source=f"rand:{semilla}:registro {n}")
        todos_findings.extend(findings)
        todos_items.extend(items)

        for f in findings:
            item = emparejar(f, items)
            categoria = CATEGORIA_POR_TIPO[f.data_type]
            if item is None or item.esperado != categoria:
                falsos_positivos.append((n, f, item))
                continue
            if item.detectado:
                continue
            item.detectado = True

            if categoria == "Tarjeta":
                detectado = TIPO_TARJETA.get(f.data_type)
                if detectado is None:
                    tipo_tarjeta["no determinado"] += 1
                elif detectado == item.tipo_real:
                    tipo_tarjeta["correcto"] += 1
                else:
                    tipo_tarjeta[f"incorrecto ({item.tipo_real} -> {detectado})"] += 1
            if categoria == "RUT":
                riesgo_rut[(item.categoria, f.risk_level.value)] += 1

        if len(ejemplos) < 10:
            ejemplos.append((n, texto, findings))

    # --------------------------- Reporte ---------------------------------
    print("=" * 90)
    print(f"PRUEBA ALEATORIA K-SECURE — {args.registros} registros, semilla {semilla}"
          f"{' (con EmailValidator)' if args.con_correo else ''}")
    print("=" * 90)

    print("\nEjemplos de registros generados:")
    for n, texto, findings in ejemplos:
        print(f"\n  [{n:03}] {texto}")
        for f in findings:
            print(f"        -> {f.data_type.value} '{f.raw_value}' [{f.risk_level.value}, {f.confidence.value}]")
        if not findings:
            print("        -> (sin hallazgos)")

    print("\n" + "-" * 90)
    print("DATOS SENSIBLES PLANTADOS (¿los encontró?)")
    print(f"  {'categoría':20} {'plantados':>9} {'detectados':>10} {'perdidos':>9} {'recall':>7}")
    por_cat: dict[str, list[Plantado]] = {}
    for i in todos_items:
        por_cat.setdefault(i.categoria, []).append(i)
    for cat, items in sorted(por_cat.items()):
        if items[0].esperado is None:
            continue
        det = sum(i.detectado for i in items)
        print(f"  {cat:20} {len(items):>9} {det:>10} {len(items) - det:>9} {det / len(items):>7.0%}")

    print("\nRUIDO / DATOS QUE NO DEBEN ALERTAR (¿generó falsas alertas?)")
    fp_por_origen = Counter((item.categoria if item else "sin origen") for _, _, item in falsos_positivos)
    for cat, items in sorted(por_cat.items()):
        if items[0].esperado is not None:
            continue
        print(f"  {cat:20} {len(items):>9} plantados -> {fp_por_origen.get(cat, 0)} falsas alertas")

    print("\nPRECISIÓN POR DETECTOR")
    total_det = Counter(CATEGORIA_POR_TIPO[f.data_type] for f in todos_findings)
    fp_det = Counter(CATEGORIA_POR_TIPO[f.data_type] for _, f, _ in falsos_positivos)
    for cat, total in sorted(total_det.items()):
        print(f"  {cat:12} {total:>4} alertas, {fp_det[cat]:>3} falsas -> precisión {(total - fp_det[cat]) / total:.0%}")

    if riesgo_rut:
        print("\nNIVEL DE RIESGO ASIGNADO A RUTs")
        for (cat, riesgo), c in sorted(riesgo_rut.items()):
            print(f"  {cat:12} -> {riesgo:13} {c}")

    if tipo_tarjeta:
        print("\nTIPO DE TARJETA (crédito/débito/prepago) EN TARJETAS DETECTADAS")
        total = sum(tipo_tarjeta.values())
        for k, c in tipo_tarjeta.most_common():
            print(f"  {k:32} {c:>4}  ({c / total:.0%})")

    if falsos_positivos:
        print("\nFALSAS ALERTAS (hasta 12)")
        for n, f, item in falsos_positivos[:12]:
            origen = f"{item.categoria}: '{item.texto}'" if item else "no corresponde a ningún dato plantado"
            print(f"  [{n:03}] {f.data_type.value} '{f.raw_value}' [{f.risk_level.value}] <- {origen}")

    # --------------------------- Persistencia ----------------------------
    if not args.no_guardar:
        print()
        try:
            init_db()
            save_findings_to_db(todos_findings)
            print(f"    (origen 'rand:{semilla}:...' para identificarlos)")
        except Exception as e:
            print(f"ERROR al guardar en PostgreSQL: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
