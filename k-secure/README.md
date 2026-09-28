# K-Secure — Sistema de Clasificación de Datos Sensibles

Prototipo inicial (Fase 1 → avance para Fase 2) del motor de escaneo
K-Secure, adaptado al contexto chileno: detecta **RUT** y **teléfonos
móviles (+56 9)** dentro de fuentes de datos, valida el RUT con el
algoritmo **Módulo 11**, y genera reportes de clasificación por nivel
de riesgo (Público / Interno / Confidencial / Restringido) pensados
como insumo de entrada para una herramienta DLP.

Construido desde cero en Python, sin depender de librerías de
clasificación de terceros. La estructura de validadores (regex +
reglas de validación + scoring por contexto) toma como referencia
conceptual el proyecto open source [FerretScan](https://github.com/awslabs/ferret-scan)
de AWS Labs — no se reutiliza su código, que está en Go y orientado a
identificadores de EE.UU. (SSN, etc.), sino su enfoque de diseño.

## Estructura del proyecto

```
k-secure/
├── ksecure/
│   ├── models.py              # Finding, RiskLevel, DataType, Confidence
│   ├── scanner.py             # KSecureScanner: orquesta los validadores
│   ├── report.py              # ClassificationReport: genera el reporte
│   └── validators/
│       ├── base.py            # Interfaz BaseValidator + scoring por contexto
│       ├── rut.py             # Regex + Módulo 11 para RUT chileno
│       └── phone.py           # Regex para celular chileno (+56 9)
├── tests/
│   ├── test_rut.py
│   └── test_phone.py
├── examples/
│   └── sample_data.csv        # Datos simulados (columnas con nombres "raros")
├── demo.py                    # Corre el flujo completo end-to-end
└── requirements.txt
```

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Correr la demo

```bash
python demo.py
```

Esto escanea `examples/sample_data.csv` (simula una tabla exportada
de una base de datos, con una columna llamada `H14510` que en
realidad contiene un RUT — el mismo caso mencionado en el informe
como ejemplo de un campo cuyo nombre no refleja su contenido) e
imprime en pantalla un reporte clasificado por riesgo. También deja
los reportes guardados en `output/reporte.json` y `output/reporte.csv`.

## Correr las pruebas unitarias

```bash
pytest -v
```

## Próximos pasos (siguientes semanas del Plan de Trabajo)

- [ ] Conectar `KSecureScanner` directamente a PostgreSQL (agregar un
      método `scan_postgres(connection, tabla)` que reutilice
      `_scan_text` por celda, igual que hace `scan_csv`).
- [ ] Ampliar el set de pruebas con más casos límite (RUTs de empresa,
      formatos con espacios, números de teléfono fijo para descartar).
- [ ] Afinar las palabras clave positivas/negativas con datos de
      prueba reales del curso, midiendo falsos positivos/negativos.
- [ ] Documentar formalmente el marco de niveles de clasificación
      (Público/Interno/Confidencial/Restringido) citando el whitepaper
      OEA/AWS y la Política de Duoc UC — este código ya usa esos
      cuatro niveles, falta el documento formal.
