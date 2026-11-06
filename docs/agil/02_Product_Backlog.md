# Product Backlog — K-Secure

Historias de usuario priorizadas con **MoSCoW** (M = debe tener, S = debería, C = podría, W = no en esta versión)
y estimadas en **puntos de historia** (escala Fibonacci: 1, 2, 3, 5, 8, 13).
Cada historia se relaciona con su requisito de la ERS (`03 - Especificación de Requerimientos de Software (ERS).docx`)
y su caso de uso (`04 - Especificación de Casos de Uso.docx`).

**Estado:** ✅ Terminada (cumple la [Definition of Done](04_Definition_of_Done.md)) · 🔄 En curso · ⏳ Pendiente

---

## Épicas

| ID | Épica | Historias |
|---|---|---|
| E1 | Motor de detección y clasificación | HU-01 a HU-05 |
| E2 | Escaneo de fuentes | HU-06 a HU-09 |
| E3 | Protección de los datos | HU-10 a HU-12 |
| E4 | Resultados y reportes | HU-13 a HU-17 |
| E5 | Reglas sin programar | HU-18, HU-19 |
| E6 | Cuentas y acceso | HU-20 a HU-23 |
| E7 | Entrega y operación | HU-24 a HU-29 |

---

## Historias de usuario

| ID | Épica | Historia de usuario | Criterios de aceptación | Req. | Prioridad | Pts | Sprint | Estado |
|---|---|---|---|---|---|---|---|---|
| HU-01 | E1 | Como **auditor**, quiero que K-Secure detecte RUT chilenos válidos, para no revisar a mano miles de registros. | Valida dígito verificador con Módulo 11; acepta con y sin puntos; rechaza RUT con DV incorrecto. | RF-04 | M | 5 | 4 | ✅ |
| HU-02 | E1 | Como **auditor**, quiero detectar celulares, correos, tarjetas (Luhn), cuentas bancarias, patentes y claves de acceso, para tener el inventario completo. | Un validador por tipo; tarjetas validadas con Luhn; tarjetas de prueba conocidas con menor confianza. | RF-04 | M | 8 | 5 | ✅ |
| HU-03 | E1 | Como **auditor**, quiero que cada hallazgo tenga una confianza (HIGH / MEDIUM / LOW), para priorizar la revisión. | Confianza 0–100; HIGH ≥ 90, MEDIUM ≥ 60, LOW < 60 (como ferret-scan). | RF-04 | M | 3 | 5 | ✅ |
| HU-04 | E1 | Como **auditor**, quiero que cada hallazgo tenga un nivel de riesgo, para saber qué tan grave sería una filtración. | Riesgo Público / Interno / Confidencial / Restringido según el tipo de dato. | RF-04 | M | 3 | 5 | ✅ |
| HU-05 | E1 | Como **auditor**, quiero que el nombre de la columna y las palabras cercanas ajusten la confianza, para reducir falsos positivos. | Palabras positivas suben la confianza y negativas la bajan; la columna `rut_cliente` cuenta como contexto. | RF-05 | M | 5 | 5 | ✅ |
| HU-06 | E2 | Como **auditor**, quiero subir varios archivos (Office, PDF, CSV, TXT, JSON) a la vez, para escanearlos en un solo paso. | Hasta 100 MB por archivo; los archivos no soportados se informan como error sin detener el escaneo. | RF-01 | M | 8 | 5 | ✅ |
| HU-07 | E2 | Como **auditor**, quiero que las planillas se lean como tablas, para saber qué columnas son sensibles. | CSV, XLSX y XLS por columna; resultado "columna X es RUT en el N % de las filas". | RF-06 | M | 5 | 5 | ✅ |
| HU-08 | E2 | Como **auditor**, quiero conectarme a PostgreSQL, MySQL, SQL Server u Oracle y elegir tablas, para escanear las bases de la empresa. | Prueba de conexión; lista de tablas; límite de 1.000, 10.000 o 100.000 filas. | RF-02, RF-03 | M | 8 | 5 | ✅ |
| HU-09 | E2 | Como **administrador de la base del cliente**, quiero que K-Secure solo lea, para estar seguro de que no modificará mis datos. | Solo `SELECT`; transacciones READ ONLY; las credenciales no se guardan. | RNF-01, RNF-03 | M | 3 | 5 | ✅ |
| HU-10 | E3 | Como **visor**, quiero ver siempre los datos enmascarados, para revisar resultados sin exponer información. | Ningún endpoint devuelve el original sin clave (`**.***.198-5`). | RF-07 | M | 3 | 5 | ✅ |
| HU-11 | E3 | Como **administrador**, quiero crear una clave de auditor, para que los originales queden cifrados. | Cifrado híbrido RSA-2048 + AES; sin clave no se puede escanear. | RF-08, RNF-02 | M | 8 | 5 | ✅ |
| HU-12 | E3 | Como **auditor**, quiero ver un dato original con la clave de auditor, para confirmar un hallazgo. | Requiere clave; 5 intentos fallidos bloquean 1 minuto; queda en la bitácora. | RF-08 | M | 3 | 5 | ✅ |
| HU-13 | E4 | Como **auditor**, quiero ver totales por riesgo y tipo y la lista de hallazgos con filtros y orden, para analizar el resultado. | Paginación; filtros por riesgo, tipo y texto; orden por cualquier columna. | RF-06 | M | 5 | 5 | ✅ |
| HU-14 | E4 | Como **auditor**, quiero un historial de escaneos y poder borrar uno, para mantener ordenada la información. | Lista con fecha y origen; borrar elimina sus hallazgos. | RF-09 | S | 2 | 5 | ✅ |
| HU-15 | E4 | Como **auditor**, quiero exportar los resultados a CSV, JSON y PDF, para entregarlos al DLP o a jefatura. | Siempre enmascarados; respetan los filtros; quedan en la bitácora; CSV sin fórmulas. | RF-15 | M | 5 | 6 | ✅ |
| HU-16 | E4 | Como **auditor**, quiero marcar hallazgos como confirmados o falsos positivos con un motivo, para depurar el resultado. | Marca uno a uno o por filtro; exportar sin falsos positivos. | RF-16 | S | 5 | 6 | ✅ |
| HU-17 | E4 | Como **auditor**, quiero comparar dos escaneos de la misma fuente, para ver si los datos sensibles aumentaron o disminuyeron. | Diferencias por tipo y riesgo entre dos fechas. | RF-18 | C | 8 | 7 | ⏳ |
| HU-18 | E5 | Como **administrador**, quiero crear reglas nuevas escribiendo ejemplos del dato, sin saber expresiones regulares. | Asistente de 3 pasos; "FC-123456" → patrón; prueba en vivo antes de guardar. | RF-10 | S | 8 | 5 | ✅ |
| HU-19 | E5 | Como **administrador**, quiero apagar validadores incluidos o sumarles palabras de contexto, para adaptarlos a mi empresa. | Se aplica en el siguiente escaneo. | RF-11 | S | 3 | 5 | ✅ |
| HU-20 | E6 | Como **empresa**, quiero que solo personas autorizadas entren a K-Secure, sin registro público. | Cuentas creadas por el admin; contraseña temporal que se cambia al primer ingreso. | RF-12, RF-13 | M | 5 | 6 | ✅ |
| HU-21 | E6 | Como **administrador**, quiero asignar roles Admin, Auditor y Visor, para limitar lo que cada persona puede hacer. | Cada endpoint revisa el rol; Visor no escanea ni revela. | RF-13 | M | 5 | 6 | ✅ |
| HU-22 | E6 | Como **usuario**, quiero recuperar mi contraseña con un código al correo, para no depender del administrador. | Código de 6 dígitos, vence en 10 minutos, se anula tras 5 intentos. | RF-14 | S | 5 | 6 | ✅ |
| HU-23 | E6 | Como **administrador**, quiero una bitácora de quién hizo qué y cuándo, para auditar el uso. | Registra ingresos, escaneos, originales vistos y cambios de reglas; no se edita ni se borra; sin datos originales. | RF-17, RNF-12 | S | 5 | 6 | ✅ |
| HU-24 | E7 | Como **cliente**, quiero usar K-Secure sin instalar ni configurar nada, porque no voy a tocar código. | Publicado en la nube (Render + Neon) con URL y login. | RNF-10 | M | 5 | 5 | ✅ |
| HU-25 | E7 | Como **equipo de TI**, quiero levantar K-Secure con Docker, para instalarlo en un servidor propio. | `docker compose up` levanta app + PostgreSQL; `.env.example` documentado. | RNF-10 | S | 3 | 6 | 🔄 |
| HU-26 | E7 | Como **equipo**, queremos pruebas de integración, seguridad y rendimiento, para asegurar la calidad antes de entregar. | Plan de pruebas documentado; pruebas automáticas que pasan. | RNF-11 | M | 5 | 6 | 🔄 |
| HU-27 | E7 | Como **auditor**, quiero que el mismo escaneo repetido dé el mismo resultado, para comparar en el tiempo. | Lectura de tablas con `ORDER BY` por llave primaria. | RNF-08 | S | 2 | 7 | ⏳ |
| HU-28 | E7 | Como **equipo de TI del cliente**, quiero un manual técnico, para instalar y operar K-Secure. | Instalación local, Docker y nube; variables de entorno; solución de problemas. | — | S | 3 | 6 | 🔄 |
| HU-29 | E7 | Como **auditor**, quiero escanear archivos de 100.000 filas sin que el servidor se quede sin memoria, para usar K-Secure en el plan de nube disponible. | Archivo de 100.000 filas con menos de 1 GB de RAM (hoy ~2,2 GB); procesar y guardar los hallazgos por lotes. | RNF-14 | S | 5 | 7 | ⏳ |

---

## Resumen

| Estado | Historias | Puntos |
|---|---|---|
| ✅ Terminadas | 23 | 115 |
| 🔄 En curso | 3 | 11 |
| ⏳ Pendientes | 3 | 15 |
| **Total** | **29** | **141** |
