# K-Secure

Detección y clasificación de datos sensibles chilenos (RUT, celulares, tarjetas, cuentas...) en
documentos y bases de datos, con una web propia. Los datos se muestran siempre enmascarados.

El motor sigue a [ferret-scan](https://github.com/awslabs/ferret-scan) de AWS Labs (Apache 2.0):
validadores con confianza 0-100 (HIGH ≥ 90, MEDIUM ≥ 60, LOW < 60), análisis de contexto y
preprocesadores por tipo de archivo. K-Secure agrega la clasificación de riesgo
Público / Interno / Confidencial / Restringido, el escaneo de bases de datos y la bóveda cifrada.

## Cómo se protegen los datos

- Las bases del cliente se abren en **solo lectura** (K-Secure solo ejecuta `SELECT`).
- La base interna guarda cada hallazgo **enmascarado** (`**.***.198-5`) y el original **cifrado**.
- **Cifrado híbrido**: al crear la clave de auditor se genera un par RSA; la llave privada queda
  cifrada con esa clave. Cada escaneo cifra sus originales con una llave AES propia, guardada
  cifrada con la llave pública. Ver un original exige la clave de auditor (5 intentos fallidos
  bloquean 1 minuto). Detalle en `ksecure/almacenamiento/boveda.py`.

## Reglas sin programar

En la página **Reglas** se crean detectores nuevos (pasaporte, ficha clínica, N° de socio...)
con un patrón, una validación opcional (Módulo 11 o Luhn), palabras de contexto, riesgo,
confianza y cuántos caracteres dejar visibles. Se prueban en vivo con un texto de ejemplo antes
de guardarlas. Los validadores incluidos se pueden apagar o sumarles palabras de contexto.

## Estructura

```
ksecure/
├── core/models.py          # Match, ContextInfo, ConfidenceLevel, RiskLevel
├── validators/             # QUÉ es sensible (uno por tipo de dato, con enmascarado propio)
│   ├── base.py             #   Clase base: contexto, nombre de columna como pista, enmascarado
│   ├── rut.py · telefono.py · tarjeta.py · email.py
│   ├── cuenta_bancaria.py · patente.py · secreto.py
│   └── regla.py            #   Validador genérico para las reglas creadas en pantalla
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

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn ksecure.web.app:app --reload
```

Abrir http://localhost:8000. La primera vez que escanees se pide crear la **clave de auditor**.
La API queda documentada en http://localhost:8000/docs.

## Pruebas

```bash
pytest -v
```
