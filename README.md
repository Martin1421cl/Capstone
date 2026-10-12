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
tests/
```

## Pruebas

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```
