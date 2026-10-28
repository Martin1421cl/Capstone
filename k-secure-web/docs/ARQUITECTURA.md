# K-Secure: arquitectura y cómo se construyó

> Documento de referencia del proyecto. Sirve como base para la presentación y como contexto
> completo para otra persona (o asistente de IA) que vaya a trabajar en el código.
> Estado al 15-10-2026.

---

## 1. Qué es K-Secure

K-Secure es una aplicación web que **encuentra, clasifica y protege datos sensibles chilenos**
(RUT, celulares, tarjetas de pago, cuentas bancarias, patentes, correos, claves de acceso) dentro de
**documentos** y **bases de datos**. Es un insumo para herramientas DLP (prevención de fuga de datos):
le dice a una empresa *dónde* tiene datos sensibles, *de qué tipo* son y *qué tan grave* sería que se filtren.

- **Producción:** https://k-secure-4olk.onrender.com (con usuario y contraseña).
- **Código:** repositorio del equipo https://github.com/Martin1421cl/Capstone, carpeta `k-secure-web/`.
- **Capstone Duoc UC**, equipo: Camilo Fuenzalida, Martin Campos, Emanuel Farías.

### Qué hace, en una frase por función

| Función | Descripción |
|---|---|
| Escanear archivos | Word, Excel (xlsx y xls), PowerPoint, PDF, OpenDocument, CSV, TXT, JSON y bases SQLite (.db) |
| Escanear bases de datos | PostgreSQL, MySQL/MariaDB, SQL Server y Oracle, siempre en **solo lectura** |
| Clasificar | Cada hallazgo tiene **confianza** (HIGH/MEDIUM/LOW) y **riesgo** (Restringido/Confidencial/Interno/Público) |
| Clasificar columnas | "La columna `KNA1.STCD1` es RUT en el 100 % de las filas", aunque su nombre no lo diga |
| Proteger | Todo se muestra **enmascarado** (`**.***.198-5`); el original queda **cifrado** y solo se ve con la clave de auditor |
| Reglas sin programar | Pantalla para crear detectores nuevos a partir de ejemplos del dato |
| Filtrar y ordenar | Por riesgo, tipo, confianza o ubicación |
| Historial | Cada escaneo queda guardado con sus resultados |

---

## 2. Origen del diseño

### La referencia: ferret-scan (AWS Labs)

Sin rúbrica escrita, el profesor pidió que K-Secure se pareciera lo más posible a
[ferret-scan](https://github.com/awslabs/ferret-scan) (Apache 2.0, en Go), adaptado a Chile.
**No se copió código** (ferret-scan está en Go); se replicó su **diseño** en Python:

| De ferret-scan se tomó | K-Secure lo adapta o agrega |
|---|---|
| Validadores con confianza 0–100 y bandas HIGH ≥ 90, MEDIUM ≥ 60, LOW < 60 | Validadores chilenos: RUT con Módulo 11, +56, patentes PPU, bancos chilenos, Transbank |
| Análisis de contexto con palabras clave positivas y negativas | El **nombre de la columna** también cuenta como contexto |
| Preprocesadores por tipo de archivo y un router | Planillas leídas **como tablas** (por columna); `.xls` antiguo; SQLite |
| Lectura de Office como ZIP + XML, sin librerías de Office | Igual, con `zipfile` + `ElementTree` |
| Límites contra "zip bombs" (50 MB por parte, 200 MB de texto) | Los mismos valores |
| Metadata de documentos (autor, empresa, palabras clave) | Igual |
| — | **Clasificación de riesgo** (Público/Interno/Confidencial/Restringido) |
| — | **Escaneo de bases de datos** y clasificación por columna |
| — | **Bóveda cifrada** para ver originales con clave |
| — | **Mantenedor de reglas** sin programar |
| — | Web propia en español |

### Relación con el K-Secure anterior

El equipo tenía una versión previa (programa de escritorio `.exe` con FastAPI + HTML local). El profesor
descartó el `.exe` ("una empresa con 1000 computadores tendría que actualizar los 1000"), así que se
**rehízo desde cero como aplicación web**, reutilizando las mejores ideas de la versión anterior:
conexión a bases en solo lectura, clasificación por columna, enmascarado con desenmascarado por clave
y lectura de planillas como tablas.

---

## 3. Tecnologías

| Capa | Tecnología | Por qué |
|---|---|---|
| Lenguaje | **Python 3.13** | Requisito del equipo; ecosistema de datos |
| API web | **FastAPI** + Uvicorn | Documentación automática en `/docs`, validación con Pydantic |
| Base interna | **SQLAlchemy 2** sobre SQLite (local) o **PostgreSQL en Neon** (nube) | La misma lógica funciona en ambos |
| Cifrado | **cryptography** (RSA-OAEP 2048 + Fernet/AES) | Librería estándar de la industria |
| PDF | **pypdf** (leer) y **reportlab** (generar reportes) | Leer PDFs al escanear; crear el reporte de resultados |
| Excel antiguo | **xlrd** | Único formato que no se lee con la biblioteca estándar |
| Drivers de BD | psycopg 3, PyMySQL, pymssql, oracledb | Uno por motor soportado |
| Frontend | HTML + CSS + JavaScript **sin frameworks** (módulos ES) | Sin compilación, fácil de entender y de desplegar |
| Pruebas | **pytest** (210 tests) | — |
| Nube | **Render** (servidor, gratis) + **Neon** (PostgreSQL, gratis), ambos en Ohio (AWS us-east-2) | Gratis y con despliegue automático desde GitHub |

Tamaño: ~2.700 líneas de Python, ~1.800 de HTML/CSS/JS, ~840 de tests.

---

## 4. Arquitectura

### 4.1 Capas (cada carpeta tiene una sola responsabilidad)

```
k-secure-web/ksecure/
│
├── core/models.py        MODELOS COMUNES: Match, ContextInfo, ConfidenceLevel, RiskLevel
├── core/texto.py         Nombres de los tipos, CSV para Excel sin fórmulas, nombres de archivo
│
├── validators/           QUÉ ES SENSIBLE
│   ├── base.py             Clase base: busca, aplica contexto, calcula confianza, enmascara
│   ├── rut.py telefono.py tarjeta.py email.py cuenta_bancaria.py patente.py secreto.py
│   ├── regla.py            Validador genérico para reglas creadas en pantalla
│   └── patron.py           Arma la expresión regular a partir de ejemplos del dato
│
├── preprocessors/        CÓMO SE LEE CADA ARCHIVO (diseño ferret-scan)
│   ├── __init__.py         Router: process_file() → texto + metadata
│   ├── texto.py            txt, json, código… (detecta UTF-8, UTF-16, cp1252)
│   ├── office.py           docx, xlsx, pptx, odt, ods, odp (texto y metadata)
│   ├── pdf.py              texto (tablas en una línea), formularios, metadata
│   └── tablas.py           csv, tsv, xlsx, xls como TABLAS (encabezados + filas)
│
├── escaneo/              QUÉ SE ESCANEA → ResultadoEscaneo en memoria
│   ├── resultado.py        Hallazgo (match + fuente + columna + posición) y ResultadoEscaneo
│   ├── archivos.py         Decide el camino: documento, planilla o SQLite
│   ├── bases_datos.py      Conexión de solo lectura a 5 motores y escaneo por tabla
│   └── celdas.py           Escaneo celda por celda (común a planillas y bases de datos)
│
├── almacenamiento/       DÓNDE SE GUARDA
│   ├── modelos.py          Tablas de la base interna (SQLAlchemy)
│   ├── db.py               Conexión, creación y actualización automática de tablas
│   ├── boveda.py           Cifrado de originales con la clave de auditor
│   ├── usuarios.py         Cuentas, roles, contraseñas (bcrypt), bloqueo y sesiones
│   ├── bitacora.py         Bitácora: anota eventos, filtra, resume y exporta a CSV
│   ├── repositorio.py      Guardar, listar, resumir, columnas sensibles, ordenar, revelar
│   └── reglas.py           Mantenedor: valida, guarda reglas y arma los validadores activos
│
├── correo.py             Envío de correos por el Apps Script del equipo (código para recuperar la contraseña)
├── exportar.py           Resultados en CSV (Excel), JSON (otros sistemas) y PDF (reporte), siempre enmascarados
├── restablecer.py        Plan B: contraseña temporal desde la terminal, sin entrar a la web
│
└── web/                  CÓMO SE MUESTRA
    ├── app.py              Crea la app FastAPI y monta API + páginas
    ├── sesion.py           Login: exige sesión en toda la web y revisa el rol en cada endpoint
    ├── api/                sesion.py · usuarios.py · escanear.py · resultados.py · auditor.py · reglas.py · bitacora.py · seguridad.py
    └── static/             login, index, archivos, base-datos, resultados, historial, reglas, seguridad, usuarios, bitacora (.html)
                            + css/ksecure.css + js/ (un módulo por página + api.js + ui.js)
```

**Regla de dependencias:** cada capa solo usa las de arriba. Los validadores no saben de bases de
datos ni de la web; el escaneo no sabe dónde se guarda; la web no contiene lógica de detección.

### 4.2 Flujo de un escaneo de archivo

```
Navegador ──POST /api/archivos──► escanear.py
                                     │  guarda el archivo en una carpeta temporal
                                     │  (del nombre del usuario solo usa la extensión)
                                     ▼
                     reglas.validadores_activos(db)   ← validadores incluidos + reglas de pantalla
                                     ▼
                     escaneo/archivos.py
                       ├─ .db/.sqlite      → bases_datos.escanear_bd (como base de datos)
                       ├─ .csv/.xlsx/.xls  → tablas.leer_tablas → celdas.escanear_filas
                       └─ resto            → preprocessors.process_file → validadores sobre el texto
                                     ▼
                     ResultadoEscaneo (en memoria, con los originales)
                                     ▼
                     repositorio.guardar
                       ├─ valor_enmascarado  (lo que se muestra)
                       └─ valor_cifrado      (bóveda: solo con la clave de auditor)
                                     ▼
                     se borra el archivo temporal  →  responde {escaneo_id}
```

### 4.3 Flujo de un escaneo de base de datos

1. **Probar conexión** (`POST /api/bd/probar`): abre la conexión en solo lectura y lista las tablas.
2. **Escanear** (`POST /api/bd/escanear`): por cada tabla elegida lee hasta N filas (por defecto 1.000)
   y pasa **cada celda** por los validadores, usando **el nombre de la columna como contexto**.
3. Con los resultados se calcula, por columna, **qué tipo de dato tiene, su peor riesgo y en qué
   porcentaje de las filas aparece**.
4. La contraseña de la base del cliente **se usa solo durante el escaneo y no se guarda**.

**Solo lectura garantizada por el motor**, no solo por el código:
- SQLite: el archivo se abre con `mode=ro`.
- PostgreSQL: cada transacción es `READ ONLY` (opción `postgresql_readonly` de SQLAlchemy;
  funciona también con agrupadores de conexiones como el de Neon).
- MySQL: `SET SESSION TRANSACTION READ ONLY`.
- SQL Server y Oracle: K-Secure solo ejecuta `SELECT`. Se recomienda al cliente un usuario de solo lectura.

---

## 5. Cómo se detecta un dato (validadores)

### 5.1 Mecanismo común (`validators/base.py`)

1. **Candidatos:** cada validador busca con una expresión regular y aplica su verificación propia.
2. **Confianza base (0–100)** según el formato y la verificación.
3. **Contexto:** se miran 50 caracteres a cada lado, más el nombre de la columna.
   Cada palabra positiva suma **+10** (máximo +20) y cada negativa resta **−20** (máximo −40).
   Las palabras se comparan sin tildes y como palabra completa ("rut" no calza en "Ruta").
4. **Nivel de confianza:** HIGH ≥ 90, MEDIUM ≥ 60, LOW < 60 (igual que ferret-scan).
5. **Riesgo:** cada validador decide según el tipo de dato y la confianza.
6. **Enmascarado:** cada validador define cómo se muestra sin revelar el dato.

**Principio acordado con el equipo:** los datos de prueba o ficticios **también se reportan**, con
menos confianza; nunca se descartan.

### 5.2 Los 7 validadores incluidos

| Validador | Cómo detecta | Riesgo | Enmascarado |
|---|---|---|---|
| **RUT** | Con o sin puntos, guion obligatorio, **Módulo 11**. RUT ≥ 50 millones = empresa (Interno). RUT de ejemplo (12.345.678) o DV inválido = baja confianza. RUT < 1 millón solo con contexto | Restringido | `**.***.198-5` |
| **Teléfono** | Celular `+56 9 XXXX XXXX` y fijos con todos los códigos de área chilenos | Celular: Confidencial · Fijo: Interno | `+56 9 **** 4870` |
| **Tarjeta de pago** | 13–19 dígitos, **Luhn**, rango de marca (Visa, Mastercard, Amex, Redcompra/Maestro…), tarjetas de prueba de Transbank. "0000 0000 0000 0000" con contexto de tarjeta = posible tarjeta | Restringido | `****-****-****-0366` (PCI-DSS) |
| **Correo** | Distingue casillas de área (`contacto@`, `ventas@`) y dominios de ejemplo | Personal: Confidencial · Área: Público | `an****@gmail.com` |
| **Cuenta bancaria** | Sin formato común en Chile: solo con contexto bancario (BancoEstado, cta cte, vista…) | Restringido | `*******6789` |
| **Patente** | PPU nueva (BBCD·12) y antigua (AB·12·34) | Confidencial | `**·**·12` |
| **Clave o token** | Claves AWS, tokens GitHub, llaves privadas | Restringido | `AKIA********` |

### 5.3 Clasificación de riesgo (propia de K-Secure)

Basada en la Política de Duoc UC y el whitepaper OEA/AWS:

| Nivel | Significado |
|---|---|
| **Restringido** | Identifica a una persona o permite un fraude (RUT, tarjetas, cuentas, claves) |
| **Confidencial** | Datos personales de contacto (celulares, correos personales, patentes) |
| **Interno** | Datos dudosos o de empresas (RUT de empresa, fijos, datos de prueba) |
| **Público** | Pensados para publicarse (`contacto@empresa.cl`) |

---

## 6. Cómo se lee cada archivo (preprocesadores)

| Tipo | Cómo | Detalle |
|---|---|---|
| txt, json, código, logs | Detección de codificación UTF-8 / UTF-16 / cp1252 | Archivos sin extensión: se decide mirando el contenido |
| docx, pptx, odt, odp | ZIP + XML (`ElementTree`), sin librerías de Office | Tablas de Word, encabezados y pies, notas del orador, diapositivas maestras |
| xlsx, xls, csv, tsv | **Como tablas**: primera fila = encabezados | Columnas alineadas aunque haya celdas vacías; nombre real de cada hoja |
| pdf | pypdf en modo *layout* | Cada fila de una tabla queda en una línea; formularios; hasta 50 páginas |
| Metadata (Office y PDF) | Autor, empresa, palabras clave, propiedades personalizadas | También se escanea |
| .db / .sqlite | Se abre como base de datos en solo lectura | Igual que una base de un cliente |

Protecciones: límite de 100 MB por archivo, límites contra zip bombs y archivos dañados que no
detienen el escaneo (aparecen en "No se pudo revisar").

---

## 7. Seguridad: enmascarado, cifrado y hasheo

Este punto quedó débil en la presentación anterior. Estas son las tres técnicas y cómo las usa K-Secure:

| Técnica | Qué hace | ¿Reversible? | En K-Secure |
|---|---|---|---|
| **Enmascarado** | Oculta parte del dato para mostrarlo (`**.***.198-5`) | No, desde el valor enmascarado | ✅ Todo lo que se ve en pantalla |
| **Cifrado** | Transforma el dato con una llave | **Sí, con la llave** | ✅ Así se guarda el original |
| **Hasheo** | Huella de una sola vía (SHA-256) | No | ❌ Aún no se usa (ver próximos pasos) |

### 7.1 La bóveda: cifrado híbrido (`almacenamiento/boveda.py`)

Problema: hay que **escanear sin pedir la clave** y **revelar con la clave**. Solución:

```
Crear clave de auditor (una vez):
    par RSA 2048 ──► llave PÚBLICA   → se guarda tal cual
                └──► llave PRIVADA   → se guarda cifrada con la clave del auditor

Cada escaneo:
    llave AES nueva (Fernet) ──► cifra cada original del escaneo
                            └──► se guarda cifrada con la llave PÚBLICA

Revelar un dato (botón 👁):
    clave del auditor → abre la llave privada → abre la llave del escaneo → abre el dato
```

Resultado: **la base interna nunca tiene un original en claro**. Quien la robe ve datos
enmascarados y datos cifrados que no puede abrir sin la clave del auditor.

### 7.2 Por qué no se usa hash para el desenmascarado

- Un hash **no se puede revertir**, así que no sirve para "ver el original".
- **Un SHA-256 de un RUT se rompe en segundos:** hay ~50 millones de RUT posibles, y basta con
  calcular el hash de todos y comparar. Si se hashea un RUT, tiene que ser con **HMAC** (hash con
  llave secreta).
- Uso correcto previsto del hash (HMAC): **supresiones** ("este dato ya lo revisé, no lo muestres
  más") y **detectar el mismo RUT en varias tablas**, sin guardar el RUT. ferret-scan usa hashes
  justamente para sus supresiones.

### 7.3 Otras medidas

| Medida | Dónde |
|---|---|
| Solo lectura en bases del cliente | `escaneo/bases_datos.py` |
| La contraseña de la base del cliente no se guarda | `web/api/escanear.py` |
| Login con roles Admin / Auditor / Visor, sin registro público | `web/sesion.py`, `almacenamiento/usuarios.py` |
| Contraseñas con bcrypt; 5 intentos fallidos bloquean la cuenta 5 minutos | `almacenamiento/usuarios.py` |
| Sesión en cookie HttpOnly + SameSite; vence a los 30 min sin uso o a las 12 h; la base guarda solo el hash del token | `web/sesion.py`, `almacenamiento/usuarios.py` |
| Otra página no puede enviar acciones con la cookie del usuario (revisión del encabezado Origin) | `web/sesion.py` |
| Recuperar la contraseña: código de 6 dígitos al correo, guardado con bcrypt, vence a los 10 min, sirve una vez y se anula tras 5 intentos | `almacenamiento/usuarios.py` |
| "¿Olvidaste tu contraseña?" responde lo mismo exista o no la cuenta (el correo se manda después de responder), así no delata usuarios | `web/api/sesion.py` |
| Máximo 1 código por minuto y 5 por hora por cuenta, y 80 al día en total (cuida el cupo de Gmail) | `almacenamiento/usuarios.py` |
| **Bitácora** de ingresos, cuentas, datos originales vistos, escaneos y reglas, con IP; cada original queda anotado antes de mostrarse | `almacenamiento/bitacora.py`, `web/sesion.py` (`anotar`) |
| La bitácora nunca guarda un original ni una contraseña (del hallazgo anota el valor enmascarado; de un usuario inexistente no anota lo escrito) | `almacenamiento/bitacora.py` |
| La bitácora es solo lectura y solo Admin: la API no tiene cómo editar ni borrar eventos | `web/api/bitacora.py` |
| Los CSV (bitácora y resultados) marcan las celdas que Excel tomaría como fórmula (inyección CSV) | `core/texto.py` |
| Revisión de hallazgos: solo Auditor y Admin marcan; cada marca (con quién y el motivo) queda en la bitácora | `web/api/resultados.py` |
| Exportar resultados: siempre enmascarado (el PDF, el CSV y el JSON solo llevan lo que se ve en pantalla) y anotado en la bitácora | `exportar.py`, `web/api/resultados.py` |
| El servicio de correo exige un secreto compartido; las pruebas nunca mandan correos reales | `correo.py`, `tests/conftest.py` |
| 5 claves de auditor incorrectas seguidas bloquean 1 minuto, por cuenta | `web/api/auditor.py` |
| El dato revelado se vuelve a ocultar a los 20 s | `static/js/resultados.js` |
| El nombre del archivo subido nunca decide una ruta en disco | `web/api/escanear.py` |
| Textos de archivos del usuario se muestran con `textContent`, nunca como HTML (contra XSS) | `static/js/ui.js` |
| Límites contra zip bombs y archivos enormes | `preprocessors/` |
| Primer administrador desde `KSECURE_ACCESO` (solo si la base no tiene cuentas) | `web/app.py` |
| Secretos fuera del repositorio (variables de entorno en Render) | `render.yaml` |

---

## 8. Mantenedor de reglas (pedido del profesor)

El profesor pidió poder **agregar o modificar validadores sin programar**. La página **Reglas** tiene:

**Reglas personalizadas**, con un asistente de 3 pasos:
1. **¿Qué dato?** Nombre en palabras ("Ficha clínica" → tipo `FICHA_CLINICA`) y palabras de contexto.
2. **¿Cómo se ve?** El usuario escribe **ejemplos** (`FC-123456`, `FC-9876543`) y K-Secure arma la
   expresión regular y la explica en palabras: *"«FC» + guion + 6 a 7 números"*
   (`validators/patron.py`). Validación opcional: Módulo 11 o Luhn. La expresión regular queda en
   "Avanzado".
3. **Riesgo y prueba:** riesgo con tarjetas de color, certeza en palabras (Muy seguro / Probable /
   Dudoso), cuántos caracteres mostrar (con vista previa) y **prueba en vivo** sobre un texto.

**Validadores incluidos:** se pueden apagar o sumarles palabras de contexto.

Por dentro: cada regla se guarda en la tabla `reglas` y se convierte en un `ReglaValidator`
(`validators/regla.py`). En cada escaneo, `reglas.validadores_activos()` arma la lista final.
*Estado:* la forma de ingresar ejemplos está en mejora.

---

## 9. Modelo de datos (base interna)

| Tabla | Contenido |
|---|---|
| `configuracion` | Llave pública y llave privada cifrada de la bóveda |
| `escaneos` | Origen (archivo/bd), nombre, fecha, filas revisadas por tabla, errores, llave AES cifrada |
| `hallazgos` | Fuente, columna, posición, número de línea/fila, tipo, riesgo, confianza, contexto, **valor enmascarado**, **valor cifrado**, **revisión** (confirmado / falso positivo, quién, cuándo y motivo) |
| `reglas` | Reglas personalizadas (patrón, ejemplos, validación, palabras, riesgo, confianza, visibles, activa) |
| `ajustes_validadores` | Validadores incluidos: activo/apagado y palabras extra |
| `usuarios` | Cuentas: usuario, nombre, correo, rol, **hash bcrypt** de la contraseña, bloqueo, último ingreso |
| `sesiones` | Sesiones abiertas: **hash SHA-256** del token de la cookie, último uso y vencimiento |
| `codigos_recuperacion` | Códigos para recuperar la contraseña: **hash bcrypt**, vencimiento, intentos, usado |
| `bitacora` | Eventos: fecha, acción, categoría, alerta, quién (copia de usuario y nombre), cuenta afectada, detalle, IP, escaneo |

Las tablas se crean solas al arrancar, y si una versión nueva agrega columnas, `db.py` las suma a una
base existente sin perder datos.

---

## 10. API (FastAPI, documentada automáticamente en `/docs`)

| Método | Ruta | Para qué |
|---|---|---|
| GET | `/api/health` | Estado (lo usa Render; no pide contraseña) |
| GET | `/api/sesion` | Si K-Secure está configurado, quién es el usuario de esta sesión y si el correo está configurado |
| POST | `/api/sesion/ingresar` · `/salir` · `/cambiar-clave` · `/configurar` | Login, salir, cambiar la contraseña, crear el primer administrador |
| POST | `/api/sesion/recuperar` | Mandar un código de 6 dígitos al correo de la cuenta (responde igual aunque no exista) |
| POST | `/api/sesion/recuperar/confirmar` | Con el código, crear la contraseña nueva e iniciar sesión |
| GET / POST / PUT | `/api/usuarios` · `/{id}` · `/{id}/restablecer` | Administrar cuentas (solo Admin) |
| POST | `/api/usuarios/correo-prueba` | Mandar un correo de prueba al administrador (solo Admin) |
| POST | `/api/seguridad/ejemplo` | Ejemplo en vivo para la página Seguridad: enmascara, cifra (llave desechable) y hashea un texto corto; no guarda nada |
| GET | `/api/bitacora` · `/resumen` · `/csv` | Bitácora con filtros y páginas, cifras de 7 días y descarga CSV (solo Admin, solo lectura) |
| GET / POST | `/api/auditor` | Ver si existe la clave de auditor / crearla (una sola vez) |
| POST | `/api/archivos` | Subir y escanear uno o varios archivos |
| GET | `/api/bd/motores` | Motores soportados |
| POST | `/api/bd/probar` | Probar conexión y listar tablas |
| POST | `/api/bd/escanear` | Escanear tablas de una base |
| GET | `/api/escaneos` | Historial |
| GET | `/api/escaneos/{id}` | Resumen: por riesgo, por tipo, columnas sensibles, errores |
| PUT | `/api/escaneos/{id}/hallazgos/{hallazgo}/revision` | Marcar un hallazgo: confirmado, falso positivo (con motivo) o pendiente (Auditor y Admin) |
| POST | `/api/escaneos/{id}/revision` | Marcar de una vez todos los hallazgos que cumplen los filtros (Auditor y Admin) |
| GET | `/api/escaneos/{id}/exportar` | Descargar los hallazgos en CSV, JSON o PDF (`formato`), con los mismos filtros, siempre enmascarados |
| GET | `/api/escaneos/{id}/hallazgos` | Hallazgos enmascarados con filtros (`riesgo`, `tipo`, `buscar`), orden (`orden` = riesgo/tipo/confianza/ubicacion, `invertir`) y paginación |
| DELETE | `/api/escaneos/{id}` | Borrar un escaneo y sus originales cifrados |
| POST | `/api/hallazgos/{id}/revelar` | Ver un original (requiere la clave de auditor) |
| GET / POST | `/api/reglas` | Listar / crear reglas |
| PUT / DELETE | `/api/reglas/{id}` | Editar / borrar una regla |
| PUT | `/api/reglas/incluidas/{nombre}` | Activar o apagar un validador incluido y sus palabras |
| POST | `/api/reglas/patron` | Armar un patrón desde ejemplos |
| POST | `/api/reglas/probar` | Probar una regla sin guardarla |

---

## 11. Interfaz web

Diseño propio con la identidad del logo (negro + cian), fuentes Exo 2 e Inter, animaciones al pasar el
mouse (tarjetas que se elevan, luz que sigue al cursor, radar mientras escanea) y accesible
(teclado, `aria`, respeta "reducir movimiento").

| Página | Contenido |
|---|---|
| **Inicio** | Qué hace K-Secure, accesos directos, cómo funciona, qué detecta, últimos escaneos |
| **Archivos** | Arrastrar y soltar varios archivos |
| **Base de datos** | Asistente: motor → conexión → tablas |
| **Resultados** | Tarjetas por riesgo (filtran al hacer clic), gráfico por tipo, **columnas sensibles** con %, tabla de hallazgos con filtros, **orden por encabezado**, botón 👁, **revisión** (avance, filtro y marcas) y **Exportar** (CSV, JSON, PDF) |
| **Historial** | Escaneos anteriores con barra de riesgo |
| **Reglas** | Mantenedor de reglas y validadores |
| **Seguridad** | Recorrido de un dato, enmascarar vs. cifrar vs. hashear con ejemplo en vivo, por qué el original se cifra y no se hashea, la bóveda y otras protecciones (todos los roles) |
| **Usuarios** | Cuentas y roles, clave de auditor, estado del correo (solo Admin) |
| **Bitácora** | Quién hizo qué y cuándo: cifras de 7 días (alertas, datos vistos, escaneos, ingresos), filtros y CSV (solo Admin) |

---

## 12. Despliegue en la nube

```
GitHub (Capstone, main) ──push──► Render (servidor Python, Ohio) ◄──► Neon (PostgreSQL, Ohio)
                                       │
                                       └── https://k-secure-4olk.onrender.com
```

- `render.yaml` (en la raíz del repositorio) define el servicio: carpeta `k-secure-web`, instalación con
  `pip install -r requirements.txt`, arranque con `uvicorn ksecure.web.app:app --host 0.0.0.0 --port $PORT`.
- Variables de entorno en Render (**no están en el código**):
  - `KSECURE_DB_URL`: connection string de Neon.
  - `KSECURE_ACCESO`: `usuario:contraseña` del primer administrador (se usa solo si la base no tiene cuentas).
  - `KSECURE_CORREO_URL` y `KSECURE_CORREO_SECRETO`: el Apps Script que manda los correos
    (`docs/apps-script-correo.gs`). Render gratis bloquea el SMTP; Apps Script envía por HTTPS desde el
    Gmail del equipo (~100 correos al día).
- **Cada push a `main` se publica solo** (3–5 minutos, sin cortar el servicio). Esto responde el
  argumento de los 1000 computadores: se actualiza en un solo lugar.
- Plan gratis: Render duerme la app tras 15 minutos sin uso; la primera visita tarda ~1 minuto.
  Los datos están en Neon y no se pierden.

---

## 13. Pruebas

**210 tests automáticos** (`pytest`, en `k-secure-web/tests/`):

| Archivo | Tests | Qué cubre |
|---|---|---|
| `test_rut.py` | 22 | Módulo 11, formatos, RUT de empresa, de ejemplo y cortos |
| `test_validadores.py` | 61 | Teléfono, tarjeta, correo, cuenta, patente, secretos, enmascarado, contexto de columna |
| `test_preprocesadores.py` | 16 | Codificaciones, docx, xlsx, pptx, odt, pdf, planillas como tablas |
| `test_reglas.py` | 23 | Reglas personalizadas, patrón desde ejemplos, validadores incluidos, actualización de tablas |
| `test_web.py` | 16 | API completa: bóveda, revelar, bloqueo, SQLite, historial, orden, vista por tipo, primer administrador, URL de Neon |
| `test_sesion.py` | 20 | Login: ninguna ruta abierta, roles, bloqueo, contraseña temporal, vencimiento, cookie, último administrador, plan B |
| `test_bitacora.py` | 13 | Bitácora: qué se anota, sin datos originales ni contraseñas, solo Admin, filtros, CSV |
| `test_revision.py` | 7 | Revisión: marcar uno y varios, deshacer, filtros, permisos, bitácora, exportar, base anterior |
| `test_exportar.py` | 7 | Exportar: CSV para Excel, JSON, PDF, filtros, sin originales, bitácora, sin fórmulas |
| `test_seguridad.py` | 4 | Página Seguridad: enmascarado igual al de los escaneos, cifrado distinto cada vez, hash igual |
| `test_recuperar.py` | 18 | Recuperar por correo: código, vencimiento, intentos, límites, no delatar cuentas, envío por Apps Script |
| `test_cliente_simulado.py` | 3 | Cliente simulado: datos válidos y lo que K-Secure debe encontrar |

Además se verificó con archivos reales del equipo (un `.xls` con 347 RUT, PDFs, bases SQLite de
ejemplo) y recorriendo la interfaz en un navegador automatizado.

---

## 14. Cronología de construcción

| Etapa | Qué se hizo |
|---|---|
| 1. Núcleo y RUT | Modelos comunes, clase base de validadores, RUT con Módulo 11 |
| 2. Validadores chilenos | Teléfono, tarjeta, correo, cuenta bancaria, patente, secretos |
| 3. Preprocesadores | Texto, Office, OpenDocument y PDF como ferret-scan |
| 4. Web y bases de datos | FastAPI, conexión de solo lectura a 5 motores, bóveda cifrada, rediseño propio con 5 páginas |
| 5. Planillas como tablas | csv/xlsx/xls por columna, RUT cortos con contexto |
| 6. Mantenedor de reglas | Reglas sin programar, asistente con patrón desde ejemplos |
| 7. Ordenar resultados | Encabezados ordenables por riesgo, tipo, confianza y ubicación |
| 8. Nube | Render + Neon, candado de acceso, publicación desde el repositorio del equipo |
| 9. Vista por tipo y cliente simulado | Hallazgos en columnas por tipo de dato; base ficticia de una empresa en Neon para las pruebas |
| 10. Login con roles | Cuentas Admin / Auditor / Visor sin registro público, contraseñas bcrypt, sesiones que vencen |
| 11. Recuperar contraseña | Código de 6 dígitos al correo, enviado por Apps Script desde el Gmail del equipo |
| 12. Bitácora | Quién hizo qué y cuándo, con filtros y descarga CSV, solo para Admin |
| 13. Página Seguridad | Enmascarar, cifrar y hashear explicados en la web, con un ejemplo en vivo (pedido del profesor) |
| 14. Exportar resultados | CSV, JSON y PDF con los filtros de la pantalla, siempre enmascarados |
| 15. Revisión de hallazgos | Confirmado / falso positivo con motivo, uno a uno o por filtro, con avance y en la bitácora |

---

## 15. Feedback del profesor y estado

| Pedido | Estado |
|---|---|
| Pasar a aplicación web (no .exe) | ✅ En la nube |
| Filtrar y ordenar resultados | ✅ |
| Mantenedor paramétrico de reglas | ✅ (ingreso de ejemplos en mejora) |
| Explicar enmascarado vs. hasheo | ✅ Página **Seguridad** en la web, con ejemplo en vivo (y sección 7). Pendiente: HMAC para supresiones |

---

## 16. Limitaciones conocidas y próximos pasos

**Limitaciones actuales**
- La bitácora se protege con permisos (solo lectura desde la web), pero quien tenga acceso directo a la
  base podría modificarla; una mejora sería encadenar cada evento con el hash del anterior.
- Desde la nube solo se llega a bases que estén en internet (no a una base dentro de la red de una empresa).
- No detecta: RUT sin guion o sin dígito verificador, texto dentro de imágenes o PDF escaneados (sin OCR),
  comentarios y notas al pie de Word, nombres y direcciones.
- Escaneos grandes se hacen mientras el usuario espera (sin segundo plano).
- PostgreSQL: solo el esquema `public`. MySQL, SQL Server y Oracle no se han probado contra servidores reales.

**Próximos pasos propuestos**
1. **Recordar falsos positivos entre escaneos** (con HMAC, sin guardar el dato): que un falso positivo ya revisado no vuelva a aparecer como pendiente en el siguiente escaneo.
2. **Conector para bases dentro de la empresa:** un programa que se instala en un servidor del cliente,
   escanea ahí mismo y envía solo resultados enmascarados y cifrados (como el *self-hosted integration
   runtime* de Microsoft Purview). La empresa no abre su firewall.
3. **Comparar escaneos** del mismo origen: qué apareció, qué desapareció y qué se mantiene.
4. Escaneos en segundo plano con progreso; RUT sin guion con contexto; comentarios de Office.

---

## 17. Para quien siga trabajando en el código (personas o asistentes de IA)

- **Dónde está:** `C:\K-SECURE` es una copia del repositorio Capstone. El código está en
  `C:\K-SECURE\k-secure-web\`. El entorno virtual está en `C:\K-SECURE\.venv` (excluido de git).
  `main` también tiene informes y autoevaluaciones del equipo: **no borrarlos**.
- **Correr local:** `cd k-secure-web` → `..\.venv\Scripts\activate` → `uvicorn ksecure.web.app:app`
  → http://localhost:8000. **No usar `--reload` en este PC** (en Windows la recarga se queda pegada y
  sigue sirviendo código viejo). La base local queda en `k-secure-web/data/` (excluida de git).
- **Tests:** desde `k-secure-web`, `pytest`.
- **Publicar:** `git pull` y luego `git push` a `main` de Capstone; Render despliega solo.
- **Convenciones:**
  - Código y textos en español. Una responsabilidad por carpeta (ver sección 4.1); no mezclar capas.
  - Los validadores no se tocan para "descartar" datos de prueba: se baja la confianza.
  - El frontend no usa frameworks; los textos del usuario siempre con `textContent`.
  - Nunca guardar un original en claro: enmascarado para mostrar, cifrado con la bóveda para guardar.
  - Atajos conocidos marcados en el código con un comentario `shortcut:`.
- **GitHub bloquea pushes** con textos que parezcan claves reales: en tests usar la clave de ejemplo
  oficial de AWS (`AKIAIOSFODNN7EXAMPLE`) o armar el texto en partes.
- **Nunca** subir connection strings ni contraseñas al repositorio o al chat: van en las variables de
  entorno de Render.
- Al cambiar un modelo de `almacenamiento/modelos.py`, agregar columnas está soportado automáticamente;
  renombrar o borrar columnas requiere una migración (Alembic).
