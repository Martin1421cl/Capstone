# K-Secure

Detección y clasificación de datos sensibles chilenos (RUT, celulares, tarjetas, cuentas...) en
documentos y bases de datos, con una web propia. Los datos se muestran siempre enmascarados.

El motor sigue a [ferret-scan](https://github.com/awslabs/ferret-scan) de AWS Labs (Apache 2.0):
validadores con confianza 0-100 (HIGH ≥ 90, MEDIUM ≥ 60, LOW < 60), análisis de contexto y
preprocesadores por tipo de archivo. K-Secure agrega la clasificación de riesgo
Público / Interno / Confidencial / Restringido, el escaneo de bases de datos y la bóveda cifrada.

Arquitectura completa, decisiones de diseño y cómo se construyó: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md).

## Cómo se protegen los datos

- Las bases del cliente se abren en **solo lectura** (K-Secure solo ejecuta `SELECT`).
- La base interna guarda cada hallazgo **enmascarado** (`**.***.198-5`) y el original **cifrado**.
- **Cifrado híbrido**: al crear la clave de auditor se genera un par RSA; la llave privada queda
  cifrada con esa clave. Cada escaneo cifra sus originales con una llave AES propia, guardada
  cifrada con la llave pública. Ver un original exige la clave de auditor (5 intentos fallidos
  bloquean 1 minuto). Detalle en `ksecure/almacenamiento/boveda.py`.

## Reglas sin programar

En la página **Reglas** un asistente de 3 pasos crea detectores nuevos (pasaporte, ficha clínica,
N° de socio...) sin saber expresiones regulares: basta escribir un par de **ejemplos del dato** y
K-Secure arma el patrón (`validators/patron.py`: "FC-123456" → «FC» + guion + 6 números).
Riesgo, certeza y enmascarado se eligen en palabras, y la regla se prueba en vivo antes de guardarla.
Los validadores incluidos se pueden apagar o sumarles palabras de contexto.

## Estructura

```
ksecure/
├── core/models.py          # Match, ContextInfo, ConfidenceLevel, RiskLevel
├── validators/             # QUÉ es sensible (uno por tipo de dato, con enmascarado propio)
│   ├── base.py             #   Clase base: contexto, nombre de columna como pista, enmascarado
│   ├── rut.py · telefono.py · tarjeta.py · email.py
│   ├── cuenta_bancaria.py · patente.py · secreto.py
│   ├── regla.py            #   Validador genérico para las reglas creadas en pantalla
│   └── patron.py           #   Arma el patrón de una regla a partir de ejemplos del dato
├── preprocessors/          # CÓMO se lee cada archivo (como ferret-scan)
│   ├── __init__.py         #   Router: process_file()
│   ├── texto.py            #   txt, csv, json, código... (UTF-8, UTF-16, cp1252)
│   ├── tablas.py           #   csv, xlsx, xls como tablas (encabezados + filas)
│   ├── office.py           #   docx, xlsx, pptx, odt, ods, odp: texto y metadata
│   └── pdf.py              #   texto (tablas en una línea), formularios y metadata
├── escaneo/                # QUÉ se escanea → ResultadoEscaneo en memoria
│   ├── archivos.py         #   documentos, planillas (por columna) y bases SQLite subidas
│   ├── celdas.py           #   escaneo celda a celda con el nombre de la columna como contexto
│   └── bases_datos.py      #   PostgreSQL, MySQL, SQL Server, Oracle, SQLite (solo lectura)
├── almacenamiento/         # DÓNDE se guarda
│   ├── modelos.py · db.py  #   tablas de la base interna (SQLite local o KSECURE_DB_URL)
│   ├── boveda.py           #   cifrado de originales con la clave de auditor
│   ├── repositorio.py      #   guardar, listar, resumir, columnas sensibles, revelar
│   └── reglas.py           #   mantenedor de reglas: guarda reglas y arma los validadores activos
└── web/                    # CÓMO se muestra
    ├── app.py              #   FastAPI: monta la API y las páginas
    ├── api/                #   escanear.py · resultados.py · auditor.py · reglas.py
    └── static/             #   index, archivos, base-datos, resultados, historial, reglas (+ css, js, img)
tests/
```

## Uso

El proyecto vive en la carpeta `k-secure-web/` del repositorio Capstone.

```bash
cd k-secure-web
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn ksecure.web.app:app
```

Abrir http://localhost:8000. La primera vez que escanees se pide crear la **clave de auditor**.
La API queda documentada en http://localhost:8000/docs.

## Publicar en la nube (gratis: Render + Neon)

1. **Neon** (https://neon.tech): crear un proyecto y copiar la *connection string* (`postgresql://...`).
2. **Render** (https://render.com): *New → Blueprint* → elegir el repositorio Capstone. Render lee `render.yaml` (en la raíz)
   y pide dos variables:
   - `KSECURE_DB_URL`: la connection string de Neon.
   - `KSECURE_ACCESO`: `usuario:contraseña` para entrar a la web (candado mientras no haya login).
3. Abrir la URL que entrega Render y **crear de inmediato la clave de auditor**.

El plan gratis de Render "duerme" la app tras 15 minutos sin uso: la primera visita tarda ~1 minuto.

## Demo: base de un cliente ficticio

`demo/cliente_demo.sql` crea 4 tablas con datos chilenos sintéticos (clientes estilo SAP con el RUT
en `STCD1`, tarjetas de prueba en `ZZDATA`, RRHH con cuentas y patentes, ventas a empresas).
En Neon: crear la base `cliente_demo`, abrir el *SQL Editor* sobre ella, pegar el archivo y ejecutar.
Luego en K-Secure: **Base de datos → PostgreSQL** con los datos de conexión de Neon.

## Pruebas

```bash
pytest -v
```
