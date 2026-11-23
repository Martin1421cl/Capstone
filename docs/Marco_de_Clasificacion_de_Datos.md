# Marco de clasificación de datos — K-Secure

Documento de la actividad **"Documentar marco de clasificación de datos"** del plan de trabajo (Guía 1.5) y del
objetivo específico OE5: definir los niveles de clasificación que usa K-Secure, qué dato cae en cada nivel y qué
política de manejo corresponde.

**Versión:** 1.1 · 23/11/2026 (sección 6: alineación con la política de Duoc UC) · Las reglas de este documento son las que aplica el código en
`k-secure-web/ksecure/validators/` y `ksecure/core/models.py`.

---

## 1. Referencias

- **OEA y AWS (2019).** *Clasificación de Datos*, serie de white papers, edición 6. Organización de los Estados
  Americanos y Amazon Web Services. https://www.oas.org/ClasificacionDeDatos
- **Duoc UC (2024).** *Política de Clasificación de Datos e Información*, versión 1, aprobada el 16/10/2024. Dirección
  de Gobierno de Datos y Análisis Institucional y Dirección General de Servicios Digitales. Entregada por el docente
  como referencia.
- **Ley 21.719** de protección de datos personales (Chile, publicada el 13/12/2024). Su vigencia estaba fijada para el
  01/12/2026; en noviembre de 2026 el Congreso aprobó postergarla hasta octubre de 2027.
- **PCI DSS** (Payment Card Industry Data Security Standard), para el tratamiento del número de tarjeta.
- **ferret-scan** (AWS Labs, Apache 2.0), para las bandas de confianza. https://github.com/awslabs/ferret-scan

### Lo que se tomó del white paper OEA/AWS

- **No hay un número único de niveles:** cada organización debe elegir la cantidad que le sirva. Demasiados niveles
  complican la gestión, y muy pocos llevan a sobreclasificar o subclasificar la información.
- Los esquemas de **tres niveles de protección** suelen cumplir con los estándares de seguridad y las exigencias legales.
- La clasificación de un activo se decide por su **valor más alto** en confidencialidad, integridad y disponibilidad.

**Decisión de K-Secure:** usar **cuatro niveles**: tres niveles de protección (Interno, Confidencial, Restringido)
más un nivel **Público** para lo que puede divulgarse. Así, el inventario también muestra qué hallazgos no requieren
acción. Siguiendo el criterio del valor más alto, un archivo, tabla o columna toma el nivel del dato más sensible
que contiene.

---

## 2. Niveles de clasificación

| Nivel | Definición | Impacto si se filtra | Ejemplos en K-Secure |
|---|---|---|---|
| **Público** | Información que la organización publica o que puede divulgarse sin daño | Ninguno | Correos de rol (`contacto@`, `ventas@`) |
| **Interno** | Información de uso interno que no identifica directamente a una persona, o un hallazgo dudoso | Bajo | Teléfono fijo, RUT de empresa, hallazgos con confianza LOW |
| **Confidencial** | Datos personales que identifican o permiten contactar a una persona | Moderado: afecta la privacidad de personas | Celular, correo personal, patente de vehículo |
| **Restringido** | Datos cuya filtración permite fraude, suplantación o acceso no autorizado | Grave: daño económico, legal o de seguridad | RUT de persona, número de tarjeta, cuenta bancaria, claves de acceso |

## 3. Nivel de confianza

Cada hallazgo tiene además una **confianza de 0 a 100** (como ferret-scan), que dice qué tan seguro está K-Secure de
que el valor sea realmente ese dato:

| Confianza | Rango | Significado |
|---|---|---|
| **HIGH** | 90–100 | Formato correcto, validación matemática aprobada y palabras de contexto que lo confirman |
| **MEDIUM** | 60–89 | Formato y validación correctos, pero sin contexto suficiente |
| **LOW** | 0–59 | Posible dato, con indicios en contra (dígito verificador inválido, tarjeta de prueba, palabras negativas) |

Un hallazgo con confianza **LOW** baja de nivel de riesgo (normalmente a Interno), porque probablemente no es un dato
real y no debe inflar el inventario.

---

## 4. Clasificación por tipo de dato

| Tipo | Cómo se detecta | Riesgo (confianza HIGH o MEDIUM) | Riesgo (LOW) | Enmascarado | Fundamento |
|---|---|---|---|---|---|
| `RUT` | Formato chileno + dígito verificador con Módulo 11 + contexto | **Restringido** si es persona natural · **Interno** si es empresa (RUT desde 50.000.000) | Interno | `**.***.678-5` | El RUT de una persona la identifica de forma única; el de una empresa aparece en cada factura |
| `TELEFONO` | Formato +56, celular o fijo | **Confidencial** si es celular · **Interno** si es fijo | Interno | `+56 9 **** 4870` | Un celular es de una persona; un fijo suele ser de una oficina |
| `TARJETA_PAGO` | Algoritmo de Luhn + prefijo de la marca (Visa, Mastercard...); las tarjetas de prueba conocidas bajan la confianza | **Restringido** | Confidencial | `****-****-****-1234` | El número de tarjeta (PAN) es dato del titular según PCI DSS, que solo permite mostrar los últimos 4 dígitos |
| `EMAIL` | Formato de correo | **Confidencial** si es personal · **Público** si es una cuenta de rol | Interno | `an****@gmail.com` | El correo personal identifica a una persona; el dominio queda visible porque indica la organización |
| `CUENTA_BANCARIA` | Número de 7 a 14 dígitos **solo si hay palabras bancarias cerca** ("cuenta corriente", "BancoEstado") | **Restringido** | Interno | últimos 4 dígitos | Permite fraudes y transferencias no autorizadas |
| `PATENTE` | Formato PPU chileno (antiguo y nuevo) | **Confidencial** | Interno | `**·**·34` | Con la patente se obtiene el nombre y RUT del dueño en el Registro de Vehículos |
| `SECRETO` | Llaves de AWS, tokens de GitHub, llaves privadas | **Restringido** | Confidencial | primeros 4 caracteres + `********` | Da acceso directo a sistemas |
| Reglas personalizadas | Patrón creado desde ejemplos en la pantalla Reglas | El que elige el Admin | Interno | últimos N caracteres (configurable) | Lo define la organización |

---

## 5. Política de manejo por nivel

Cómo debe tratar la organización cliente la información de cada nivel, y cómo lo aplica K-Secure dentro de la herramienta.

| Aspecto | Público | Interno | Confidencial | Restringido |
|---|---|---|---|---|
| **Quién accede** | Cualquiera | Personal de la organización | Solo quien lo necesita por su función | Solo personas autorizadas expresamente, con registro de cada acceso |
| **Almacenamiento** | Sin requisito | Sistemas de la organización | Sistemas con control de acceso | Cifrado en reposo y control de acceso |
| **Envío y transmisión** | Libre | Canales internos | Canales cifrados; no por correo personal | Solo canales cifrados y aprobados; nunca en planillas sueltas |
| **Al mostrarse** | Completo | Completo | Enmascarado por defecto | Siempre enmascarado |
| **Eliminación** | Sin requisito | Al terminar su uso | Borrado seguro | Borrado seguro y verificado |
| **Acción sugerida al encontrarlo** | Ninguna | Revisar si debe estar ahí | Restringir el acceso y evaluar si es necesario | Prioridad 1: mover a un lugar protegido, cifrar o eliminar; alertar al DLP |

### Cómo aplica K-Secure esta política a su propia información

- **Todo hallazgo se muestra enmascarado**, sin importar su nivel, porque el inventario no necesita el dato original.
- El **original se guarda cifrado** (AES por escaneo, con la llave protegida con RSA-2048) y solo un rol **Auditor**
  con la **clave de auditor** puede verlo. Cada vez que se revela un original queda registrado en la bitácora.
- Las **exportaciones** (CSV, JSON, PDF) llevan solo valores enmascarados.
- Las **bases del cliente se leen en solo lectura**: K-Secure informa, no modifica.

---

## 6. Relación con la política de clasificación de Duoc UC

La Guía 1.5 compromete alinear este marco con la **Política de Clasificación de Datos e Información de Duoc UC**
(versión 1, octubre de 2024). Esta sección registra esa alineación.

### 6.1 Qué define la política de Duoc UC

La política responde a los controles 5.12 (clasificación) y 5.13 (etiquetado) de la ISO/IEC 27001 y clasifica la
información en tres dimensiones (sección 8 de la política):

| Dimensión | Niveles |
|---|---|
| **Confidencialidad** (8.1) | Pública · Interna · Confidencial · Reservada |
| **Integridad** (8.2) | Baja · Media · Alta |
| **Disponibilidad** (8.3) | Baja (hasta 48 h sin acceso) · Media (24 h) · Alta (6 h) |

En confidencialidad, la política pone los **datos personales** (nombre, número de cédula, domicilio, teléfono, firma,
correo electrónico, datos bancarios y dirección IP, entre otros) en **Confidencial**, y los **datos personales
sensibles** (salud, origen racial, ideología, creencias, orientación sexual, identidad de género, datos genéticos y
biomédicos, entre otros) en **Reservada**, junto con la información de la alta dirección.

### 6.2 Alcance de la alineación

K-Secure clasifica **confidencialidad**: su objetivo es decir qué datos son sensibles para que un DLP los proteja. La
integridad y la disponibilidad dependen de cómo la organización usa cada sistema, no del contenido que se escanea, y
quedan en manos del dueño de dominio, como indica la política (sección 5.3). Por eso la alineación se hace con los
niveles de confidencialidad.

### 6.3 Tabla de equivalencia

| Nivel K-Secure | Nivel de la política de Duoc UC | Criterio común | Tipos de dato |
|---|---|---|---|
| **Público** | **Pública** (8.1.1) | Puede conocerla cualquier persona | Correos de rol (`contacto@`, `ventas@`) |
| **Interno** | **Interna** (8.1.2) | Uso interno; filtración con impacto leve | Teléfono fijo de oficina, RUT de empresa, hallazgos con confianza LOW |
| **Confidencial** | **Confidencial** (8.1.3) | Datos personales: solo quien los necesita para su trabajo | Celular, correo personal, patente |
| **Restringido** | **Confidencial** (8.1.3), con un control más estricto | Datos personales cuya filtración permite fraude o suplantación | RUT de persona, tarjeta, cuenta bancaria |
| **Restringido** | **Reservada** (8.1.4) | Filtración con impacto grave; acceso de un grupo muy reducido | Claves y tokens de acceso; reglas propias de datos sensibles, como la ficha clínica |

**Decisión:** K-Secure mantiene sus **cuatro niveles**. Ningún tipo de dato queda con menos protección que la que
exige la política, así que **no fue necesario cambiar el riesgo de ningún validador** (paso 4 del plan). La diferencia
es intencional: la política agrupa todos los datos personales en Confidencial, mientras que K-Secure separa en
Restringido los que permiten fraude o suplantación (RUT de persona, tarjeta y cuenta bancaria), siguiendo el criterio
de impacto del white paper OEA/AWS y de PCI DSS. Para quien use la política de Duoc UC, todo hallazgo Restringido
debe tratarse **al menos** como Confidencial, y como Reservado cuando se trate de claves de acceso o datos sensibles.

### 6.4 Brechas encontradas

La política nombra datos personales que K-Secure **no detecta hoy** con sus validadores incluidos:

| Dato según la política | Nivel en la política | Situación en K-Secure | Cómo cubrirlo |
|---|---|---|---|
| Nombre y domicilio | Confidencial | No se detectan: no tienen un formato verificable | Regla propia con palabras de contexto, o revisión del dueño de dominio |
| Dirección IP | Confidencial | No se detecta; en el cliente simulado, una columna de IP es una «trampa» que no se marca | Regla propia de nivel Confidencial si la organización la considera dato personal |
| Datos personales sensibles (salud, creencias, etc.) | Reservada | Solo con reglas propias (la plantilla «Ficha clínica» ya viene con nivel Restringido) | Reglas propias de nivel Restringido |

### 6.5 Etiquetado y manejo (secciones 9 y 10 de la política)

| Exigencia de la política | Cómo la apoya K-Secure |
|---|---|
| Clasificar y etiquetar los activos al incorporarlos al inventario (9) | Cada escaneo deja un inventario con el nivel de cada archivo, tabla y columna, que el dueño de dominio usa para etiquetar |
| Revisión periódica de la clasificación (9) | El historial y la comparación de escaneos muestran qué cambió entre una revisión y la siguiente |
| Restricciones de acceso coherentes con la clasificación (10.1) | Roles Admin, Auditor y Visor; el Visor solo ve valores enmascarados |
| Registro de quienes acceden (10.2) | Bitácora: cada vez que alguien ve un original queda registrado quién, cuándo y desde qué IP |
| Copias con la misma clasificación que el original (10.6) | Las exportaciones (CSV, JSON y PDF) solo llevan valores enmascarados |

| | |
|---|---|
| **Estado** | Terminado (23/11/2026) |
| **Responsable** | Emanuel Farías |
| **Resultado** | Tabla de equivalencia K-Secure ↔ política de Duoc UC (6.3), brechas (6.4) y relación con el etiquetado y manejo (6.5) |

---

## 7. Mantención del marco

- Un **tipo de dato nuevo** se agrega como validador en el código o como regla personalizada desde la pantalla
  **Reglas** (rol Admin), eligiendo su nivel de riesgo.
- Un **validador incluido** se puede apagar o ajustar con palabras de contexto propias de la organización.
- Los cambios de reglas quedan registrados en la bitácora.
