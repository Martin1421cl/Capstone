# K-Secure

Detección, clasificación y redacción de datos sensibles chilenos (RUT, celulares, tarjetas...).
El diseño sigue a [ferret-scan](https://github.com/awslabs/ferret-scan) de AWS Labs (Apache 2.0):
validadores con confianza 0-100 (HIGH ≥ 90, MEDIUM ≥ 60, LOW < 60) y análisis de contexto.
K-Secure agrega la clasificación de riesgo Público / Interno / Confidencial / Restringido.

## Estructura

```
ksecure/
├── core/models.py        # Match, ContextInfo, ConfidenceLevel, RiskLevel
└── validators/
    ├── base.py             # Clase base Validator + palabras clave de contexto
    ├── rut.py              # RUT: Módulo 11, RUT de empresa, RUT de ejemplo
    ├── telefono.py         # Celular +56 9 y fijos por código de área
    ├── tarjeta.py          # Luhn + marca + tarjetas de prueba Transbank
    ├── email.py            # Personal vs. casilla de rol (contacto@...)
    ├── cuenta_bancaria.py  # Solo con contexto bancario (BancoEstado, cta cte...)
    ├── patente.py          # PPU nueva (BBCD·12) y antigua (AB·12·34)
    └── secreto.py          # Claves AWS, tokens GitHub, llaves privadas
└── preprocessors/
    ├── __init__.py         # Router: process_file() pasa el archivo por cada preprocesador que lo acepta
    ├── base.py             # ProcessedContent, Section, clase base Preprocessor
    ├── texto.py            # txt, csv, json, código...: detecta UTF-8, UTF-16 y cp1252
    ├── office.py           # docx, xlsx, pptx, odt, ods, odp: texto y metadata (zipfile + XML, como ferret-scan)
    └── pdf.py              # Texto, formularios y metadata (pypdf)
└── web/
    ├── app.py              # FastAPI: /, /scan, /health (como internal/web de ferret-scan)
    └── static/index.html   # Página para subir archivos y ver resultados
tests/
```

## Uso (web)

```bash
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn ksecure.web.app:app --reload
```

Abrir http://localhost:8000, subir uno o más archivos y ver los hallazgos.
La API queda documentada en http://localhost:8000/docs (`POST /scan`, `GET /health`).

## Pruebas

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```
