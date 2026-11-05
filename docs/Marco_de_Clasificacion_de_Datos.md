# Marco de clasificación de datos — K-Secure

Documento de la actividad **"Documentar marco de clasificación de datos"** del plan de trabajo (Guía 1.5) y del
objetivo específico OE5: definir los niveles de clasificación que usa K-Secure, qué dato cae en cada nivel y qué
política de manejo corresponde.

**Versión:** 1.0 · 31/10/2026 · Las reglas de este documento son las que aplica el código en
`k-secure-web/ksecure/validators/` y `ksecure/core/models.py`.

---

## 1. Referencias

- **OEA y AWS (2019).** *Clasificación de Datos*, serie de white papers, edición 6. Organización de los Estados
  Americanos y Amazon Web Services. https://www.oas.org/ClasificacionDeDatos
- **Política de Clasificación de Datos e Información de Duoc UC**, entregada por el docente como referencia.
- **Ley 21.719** de protección de datos personales (Chile, publicada el 13/12/2024, vigente desde el 01/12/2026).
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

La política de clasificación de datos de Duoc UC fue entregada por el docente como referencia para este marco.
Los cuatro niveles de K-Secure deben revisarse contra los niveles de esa política antes del informe final, para
indicar a qué nivel de la política corresponde cada uno:

| Nivel K-Secure | Nivel equivalente en la política de Duoc UC |
|---|---|
| Público | *(completar con el documento entregado por el docente)* |
| Interno | *(completar)* |
| Confidencial | *(completar)* |
| Restringido | *(completar)* |

---

## 7. Mantención del marco

- Un **tipo de dato nuevo** se agrega como validador en el código o como regla personalizada desde la pantalla
  **Reglas** (rol Admin), eligiendo su nivel de riesgo.
- Un **validador incluido** se puede apagar o ajustar con palabras de contexto propias de la organización.
- Los cambios de reglas quedan registrados en la bitácora.
