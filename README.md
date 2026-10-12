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
    ├── base.py           # Clase base Validator + palabras clave de contexto
    └── rut.py            # RUT: patrón + Módulo 11 + contexto
tests/
```

## Pruebas

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```
