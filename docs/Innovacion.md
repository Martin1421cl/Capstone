# Innovación e impacto en el mercado — K-Secure

---

## 1. ¿Qué problema resuelve?

Las empresas chilenas guardan datos personales (RUT, celulares, tarjetas, cuentas bancarias) en planillas,
documentos y bases de datos, y en la mayoría de los casos **no saben dónde están**. Eso es un problema porque:

- La **Ley 21.719** de protección de datos personales exige saber qué datos personales se tratan y protegerlos,
  con multas para quien no cumpla.
- No se puede proteger lo que no se conoce: una solución **DLP** (prevención de fuga de datos) necesita saber
  primero qué información es sensible para poder bloquear su salida.
- Revisar a mano miles de archivos y tablas es lento, caro y propenso a errores.

## 2. ¿Qué hace diferente a K-Secure?

| | Herramientas DLP comerciales | Herramientas de código abierto (ej. ferret-scan) | **K-Secure** |
|---|---|---|---|
| Datos chilenos (RUT con Módulo 11, +56, patentes PPU, bancos chilenos) | Parcial o por configuración | No | **Sí, incluidos** |
| Escaneo de bases de datos | Sí, en planes caros | No (solo archivos) | **Sí, 4 motores en solo lectura** |
| Clasificación por columna ("`STCD1` es RUT en el 100 % de las filas") | Algunas | No | **Sí, aunque el nombre no lo diga** |
| Nivel de riesgo (Público / Interno / Confidencial / Restringido) | Sí | No (solo confianza) | **Sí** |
| Datos protegidos dentro de la propia herramienta | Variable | No (muestra los datos) | **Enmascarado + bóveda cifrada** |
| Reglas nuevas sin programar | Requiere expresiones regulares | Requiere programar | **Desde ejemplos del dato** |
| Uso | Instalar agentes | Línea de comandos | **Navegador, en español** |
| Costo | Licencias por usuario | Gratis | **Gratis (código propio + nube gratuita)** |

## 3. Innovaciones concretas

1. **Reglas desde ejemplos (sin expresiones regulares).** El usuario escribe dos ejemplos como `FC-123456` y
   K-Secure arma el patrón ("FC" + guion + 6 números), lo prueba en vivo y lo aplica. Cualquier analista puede
   crear un detector nuevo (ficha clínica, N° de socio, pasaporte) sin saber programar.
2. **Cifrado híbrido con clave de auditor.** Cada escaneo cifra sus originales con una llave AES propia, guardada
   cifrada con RSA. Ni siquiera quien administra el servidor puede ver los datos sin la clave de auditor, y cada
   original revelado queda en una bitácora que no se puede editar.
3. **El nombre de la columna como contexto.** Igual que una persona entiende que la columna `rut_cliente` tiene
   RUT, K-Secure usa el nombre de la columna para ajustar la confianza, y además detecta columnas sensibles con
   nombres crípticos de sistemas como SAP (`STCD1`, `ZZDATA`).
4. **Diseño probado, adaptado a Chile.** En vez de inventar la arquitectura, se replicó el diseño de ferret-scan
   (AWS Labs): validadores con confianza 0–100, análisis de contexto y preprocesadores por tipo de archivo.
   Sobre esa base K-Secure agrega riesgo, bases de datos, bóveda, reglas y web.
5. **Solo lectura por diseño.** K-Secure nunca escribe en la base del cliente: transacciones `READ ONLY` y solo
   `SELECT`. Esto reduce la barrera para que un área de TI autorice su uso.

## 4. Valor que agrega

| Para | Valor |
|---|---|
| **Encargado de seguridad / cumplimiento** | Inventario de datos sensibles en minutos, con evidencia exportable para auditorías y la Ley 21.719 |
| **Área de TI** | Se instala en la nube o con Docker; no toca las bases (solo lectura); no hay que instalar nada en cada equipo |
| **DLP de la empresa** | Recibe la clasificación en JSON, lista para definir qué bloquear |
| **Personas cuyos datos se escanean** | Sus datos no quedan expuestos ni siquiera dentro de la herramienta |

## 5. Impacto en el mercado

K-Secure no compite con la inteligencia artificial ni con los grandes DLP: resuelve un paso previo, concreto y
obligatorio que hoy muchas empresas chilenas hacen a mano o no hacen.

### ¿Por qué ahora?

- La **Ley 21.719** de protección de datos personales se publicó el 13 de diciembre de 2024 y entra en vigencia el
  **1 de diciembre de 2026**. Crea la Agencia de Protección de Datos Personales y multas de hasta **5.000 UTM**
  (leves), **10.000 UTM** (graves) y **20.000 UTM** (gravísimas), que en empresas grandes reincidentes pueden llegar
  a un porcentaje de sus ingresos anuales.
- Para cumplir, la empresa primero tiene que **saber dónde están los datos personales** que trata. Ese inventario es
  justamente lo que entrega K-Secure.

### ¿A quién se le vende?

| Segmento | Por qué le sirve |
|---|---|
| Empresas medianas y grandes con datos de clientes (retail, salud, educación, financieras, cajas de compensación) | Tienen miles de planillas y bases con RUT, tarjetas y cuentas; necesitan el inventario para la ley y para su DLP |
| Consultoras de ciberseguridad y cumplimiento | Usan K-Secure como herramienta en sus diagnósticos y auditorías de datos personales |
| Áreas de TI de instituciones públicas y universidades | Manejan datos de personas y necesitan evidencia de cumplimiento con bajo presupuesto |

### Modelo de negocio posible

| Modalidad | Para quién |
|---|---|
| **Servicio en la nube por suscripción mensual** (lo que hoy está en Render + Neon) | Empresas que no quieren instalar nada |
| **Licencia para instalar en servidor propio** (Docker) | Empresas que no pueden sacar datos de su red |
| **Diagnóstico puntual** (un escaneo + informe para la ley) | Consultoras y empresas que solo necesitan el inventario inicial |

### Ventaja frente a las alternativas

- **Frente a revisar a mano:** lo que a una persona le tomaría semanas, K-Secure lo hace en minutos (100.000 filas
  de una tabla en 32 s) y deja evidencia exportable.
- **Frente a un DLP comercial:** no reemplaza al DLP, lo alimenta. Es más barato, se usa desde el navegador y ya
  entiende los datos chilenos sin configurarlo.
- **Frente a herramientas de código abierto:** estas no reconocen el RUT ni escanean bases de datos, y muestran los
  datos en claro.

### Riesgos

- La adopción depende de que las empresas confíen en una herramienta nueva: por eso el diseño es de **solo lectura**
  y los datos nunca quedan en claro.
- Los proveedores grandes podrían agregar validadores chilenos; la ventaja de K-Secure está en el foco local, el
  costo y la facilidad de uso.

## 6. Indicadores

| Indicador | Resultado |
|---|---|
| Columnas sensibles detectadas en la base demo | 9 de 9, 0 falsos positivos |
| 100.000 filas escaneadas | 32 s |
| Pruebas automáticas | 235, todas pasan |
| Datos originales guardados en claro | 0 |
