# Sprint Backlog — K-Secure

Sprints de **2 semanas**. Al inicio de cada sprint el equipo elige historias del [Product Backlog](02_Product_Backlog.md),
las divide en tareas y se las reparte. Las fechas y el avance se respaldan con el historial de commits del repositorio.

**Integrantes:** CF = Camilo Fuenzalida · EF = Emanuel Farías · MC = Martín Campos
**Estado de las tareas:** ✅ Hecha · 🔄 En curso · ⏳ Por hacer

> **Nota:** los sprints 1 a 5 se documentaron el 31/10/2026 a partir del historial del repositorio, las
> autoevaluaciones, los diarios de reflexión y la retroalimentación del docente de cada fase. Desde el sprint 6
> se registran al cierre de cada sprint.

---

## Resumen de sprints

| Sprint | Fechas | Fase | Objetivo del sprint | Puntos comprometidos | Puntos terminados |
|---|---|---|---|---|---|
| 1 | 18/08 – 31/08 | Fase 1 | Definir el proyecto: problema, objetivos, alcance y plan de trabajo | — (documentación) | — |
| 2 | 01/09 – 14/09 | Fase 1 | Crear el repositorio y entregar la definición del proyecto | — (documentación) | — |
| 3 | 15/09 – 28/09 | Fase 2 | Primera versión: escritorio con FastAPI + HTML local | — (versión descartada) | — |
| 4 | 29/09 – 12/10 | Fase 2 | Incorporar la retroalimentación del docente y empezar la reescritura | 5 | 5 |
| 5 | 13/10 – 26/10 | Fase 2 | Reescritura completa como aplicación web, publicada en la nube | 80 | 80 |
| 6 | 27/10 – 09/11 | Fase 2 → 3 | Cuentas y seguridad, reportes, Docker, pruebas y documentación | 41 | 41 |
| 7 | 10/11 – 23/11 | Fase 3 | Cierre: pendientes, pruebas finales y presentación | 15 | 15 |
| — | 24/11 – 01/12 | Fase 3 | Entrega final (01/12/2026): informe, presentación y demostración | — | — |

> En los sprints 1 a 3 el trabajo fue de definición del proyecto y de una primera versión que luego se descartó,
> por eso no suman puntos del Product Backlog actual.

---

## Sprint 1 — Definición del proyecto (18/08 – 31/08)

**Objetivo:** acordar el problema, los objetivos y el alcance del proyecto.

| Tarea | Responsable | Estado |
|---|---|---|
| Investigar el problema: datos sensibles en empresas chilenas y Ley 21.719 | Todo el equipo | ✅ |
| Investigar soluciones existentes (DLP, ferret-scan) | CF | ✅ |
| Redactar la Guía 1.5 – Definición del proyecto | MC | ✅ |
| Carta Gantt y plan de trabajo | MC | ✅ |
| Autoevaluaciones y diarios de reflexión de la Fase 1 | Cada integrante | ✅ |

## Sprint 2 — Repositorio y entrega Fase 1 (01/09 – 14/09)

**Objetivo:** dejar el repositorio del equipo y la entrega de la Fase 1 listos.

| Tarea | Responsable | Estado |
|---|---|---|
| Crear el repositorio `Martin1421cl/Capstone` y subir los documentos (03/09) | MC | ✅ |
| Informe 1.4 Formativa Fase 1 | Todo el equipo | ✅ |
| Presentación del proyecto Fase 1 | Todo el equipo | ✅ |

## Sprint 3 — Primera versión (15/09 – 28/09)

**Objetivo:** tener una primera versión funcional para mostrar al docente.

| Tarea | Responsable | Estado |
|---|---|---|
| API en FastAPI con conexión a PostgreSQL | EF | ✅ |
| Validadores de RUT, teléfono, correo y tarjeta | EF, CF | ✅ |
| Interfaz HTML local y empaquetado como `.exe` | EF | ✅ |
| Pruebas unitarias con pytest y datos simulados (Faker) | EF | ✅ |
| Subir la primera versión al repositorio (28/09) | EF | ✅ |

## Sprint 4 — Retroalimentación y decisión de rehacer (29/09 – 12/10)

**Objetivo:** incorporar la retroalimentación del docente (parecerse a ferret-scan, descartar el `.exe`).

| Historia / tarea | Responsable | Estado |
|---|---|---|
| Ajustes a la primera versión y subida (08/10) | EF | ✅ |
| Analizar ferret-scan (AWS Labs) y definir la nueva arquitectura | CF | ✅ |
| **HU-01** Núcleo del motor y validador de RUT con Módulo 11 (12/10) | CF | ✅ |
| Validadores chilenos: primera parte (12/10) | CF | ✅ |

## Sprint 5 — Reescritura como aplicación web (13/10 – 26/10)

**Objetivo:** reemplazar la primera versión por una aplicación web basada en ferret-scan y publicarla en la nube.

| Historia | Tareas | Responsable | Pts | Estado |
|---|---|---|---|---|
| HU-02, HU-03, HU-04, HU-05 | Validadores chilenos, confianza, riesgo y contexto | CF | 19 | ✅ |
| HU-06 | Preprocesadores: texto, Office, OpenDocument, PDF (14/10) | CF | 8 | ✅ |
| HU-07 | Planillas como tablas con clasificación por columna (14/10) | CF | 5 | ✅ |
| HU-08, HU-09 | Bases de datos en solo lectura (14/10–15/10) | CF | 11 | ✅ |
| HU-10, HU-11, HU-12 | Enmascarado y bóveda con originales cifrados (14/10) | CF | 14 | ✅ |
| HU-13, HU-14 | Web: inicio, archivos, resultados, historial, orden por columnas (14/10–15/10) | CF | 7 | ✅ |
| HU-18, HU-19 | Mantenedor de reglas con asistente de 3 pasos (15/10) | CF | 11 | ✅ |
| HU-24 | Publicación en Render + Neon (15/10) | CF | 5 | ✅ |
| — | Documento de arquitectura (15/10) | CF | — | ✅ |
| — | Documentación de la 2.ª entrega: ERS, casos de uso, SAD 4+1 (16/10) | EF, MC | — | ✅ |
| — | Vista por tipo de dato y cliente simulado (26/10) | EF | — | ✅ |
| | | **Total** | **80** | |

## Sprint 6 — Cuentas, seguridad y entrega (27/10 – 09/11) · *cerrado*

**Objetivo:** cerrar los requisitos de seguridad pendientes y dejar el proyecto listo para instalar, probar y evaluar.

| Historia | Tareas | Responsable | Pts | Estado |
|---|---|---|---|---|
| HU-20, HU-21 | Login con roles Admin, Auditor y Visor, sin registro público (28/10) | EF | 10 | ✅ |
| HU-22 | Recuperar contraseña por correo y restablecer desde la terminal (28/10) | EF | 5 | ✅ |
| HU-23 | Bitácora de auditoría (28/10) | EF | 5 | ✅ |
| HU-15, HU-16 | Exportar CSV/JSON/PDF y revisión de hallazgos (28/10) | EF | 10 | ✅ |
| — | Documentos de la Fase 2 (2.1, 2.3, 2.4, 2.6) y autoevaluaciones (30/10) | MC | — | ✅ |
| HU-25 | Dockerfile, docker-compose y `.env.example`, probado con Docker Desktop (05/11 – 06/11) | CF | 3 | ✅ |
| HU-26 | Plan de pruebas y pruebas de integración, seguridad y rendimiento (05/11 – 06/11) | CF, EF | 5 | ✅ |
| HU-28 | Manual técnico (06/11) | CF | 3 | ✅ |
| — | README en la raíz, artefactos ágiles, modelo ER y diagramas UML (06/11) | MC, CF | — | ✅ |
| — | Marco de clasificación de datos (OE5) y entregas ordenadas por fase (05/11 – 06/11) | EF | — | ✅ |
| | | **Total** | **41** | |

## Sprint 7 — Cierre (10/11 – 23/11)

**Objetivo:** terminar los pendientes y preparar la presentación final.

| Historia | Tareas | Responsable | Pts | Estado |
|---|---|---|---|---|
| HU-27 | `ORDER BY` por llave primaria al leer tablas, con 5 pruebas nuevas (17/11) | MC | 2 | ✅ |
| HU-29 | Guardar los hallazgos por lotes: un CSV de 100.000 filas baja de ~2,1 GB a ~265 MB de RAM, con 7 pruebas (18/11) | CF | 5 | ✅ |
| HU-17 | Comparar dos escaneos: API, página `comparar.html` y enlace desde el historial, con 9 pruebas (18/11) | EF | 8 | ✅ |
| — | RNF-18: el escaneo de archivos corre en un hilo aparte y no bloquea a los demás usuarios (18/11) | EF | — | ✅ |
| — | Documento de diseño, escalabilidad y pruebas por sprint (16/11) | MC, EF | — | ✅ |
| — | Retrospectiva del sprint 6 (18/11) | MC | — | ✅ |
| — | Presentación del examen final (15 min), guion por integrante y datos de la demo (22/11) | Todo el equipo | — | ✅ |
| — | Retrospectiva del sprint 7 (23/11) | Todo el equipo | — | ✅ |
| — | Prueba con la base del cliente simulado en Neon | EF | — | ⏳ → entrega final |
| — | Alinear el marco de clasificación con la política de Duoc UC (OE5) | EF | — | ⏳ → entrega final |
| — | Pruebas de aceptación con un usuario externo (PR-24 a PR-26) | Todo el equipo | — | ⏳ → entrega final |
| — | Informe final | Todo el equipo | — | 🔄 → entrega final |

Las 15 historias planificadas para el sprint quedaron terminadas. Las tareas sin historia que no se alcanzaron pasan
a la semana de entrega final.

## Entrega final (24/11 – 01/12)

**Objetivo:** cerrar los pendientes del sprint 7 y entregar el proyecto.

| Tarea | Responsable | Estado |
|---|---|---|
| Prueba con la base del cliente simulado en Neon (antes del ensayo) | EF | ⏳ |
| Escaneo de bases de datos siempre completo: todas las tablas y todas las filas, leídas de a 2.000; se quita el tope de filas de la pantalla | CF | ✅ |
| Optimizar la velocidad del motor: misma detección, ~5 veces más rápido en bases de datos (cliente simulado: 6,1 s → 1,2 s; PR-23: 32 s → 11 s) | CF | ✅ |
| Alinear el marco de clasificación con la política de Duoc UC: tabla de equivalencia de niveles (OE5, 23/11) | EF | ✅ |
| Pruebas de aceptación con un usuario externo (PR-24 a PR-26) | Todo el equipo | ⏳ |
| Informe final (`Fase 3/Grupal/`) | Todo el equipo | 🔄 |
| Presentación final en `.pptx` (`Fase 3/Grupal/`) y ensayo con cronómetro | Todo el equipo | ⏳ |
| Diario de reflexión y autoevaluación de la Fase 3 (`Fase 3/Individual/`) | Cada integrante | ⏳ |

---

## Anexo: evidencia en el repositorio

Commits de la rama `main` (sin *merges*) agrupados por sprint, con la historia del Product Backlog a la que aportan.
Se obtienen con `git log --no-merges --date=short --format="%ad %an %s"`. Con el archivo `.mailmap` de la raíz, los
usuarios de GitHub de cada integrante (Fruna1, Emanuel2234, Martin1421cl) aparecen con su nombre real.

### Sprint 2 (01/09 – 14/09)

| Fecha | Integrante | Commit | Historia / aporte |
|---|---|---|---|
| 03/09 | MC | `eeaab34` Add files via upload | Entrega Fase 1 |
| 03/09 | MC | `1307cb7` Agregando carpetas de Google Drive | Entrega Fase 1 |

### Sprint 3 (15/09 – 28/09)

| Fecha | Integrante | Commit | Historia / aporte |
|---|---|---|---|
| 28/09 | EF | `aad06e9` Add files via upload | Primera versión |

### Sprint 4 (29/09 – 12/10)

| Fecha | Integrante | Commit | Historia / aporte |
|---|---|---|---|
| 08/10 | EF | `357105f` últimos cambios | Primera versión |
| 08/10 | CF | `95d4514` Add files via upload | Primera versión (respaldo .zip) |
| 12/10 | CF | `08924a7` Parte 1: núcleo y validador de RUT | HU-01 |
| 12/10 | CF | `4505ad6` Parte 2: validadores chilenos | HU-02, HU-03, HU-04 |

### Sprint 5 (13/10 – 26/10)

| Fecha | Integrante | Commit | Historia / aporte |
|---|---|---|---|
| 14/10 | CF | `525796f` Parte 3: preprocesadores como ferret-scan (texto, Office, OpenDocument, PDF) | HU-06 |
| 14/10 | CF | `b8e8248` Comando python -m ksecure para escanear archivos y carpetas | HU-06 |
| 14/10 | CF | `bc08a73` README: corrige rutas de ejemplo | Documentación |
| 14/10 | CF | `dbe33ea` Web con FastAPI: subir archivos y ver hallazgos (reemplaza el comando de consola) | HU-06, HU-13 |
| 14/10 | CF | `4c812c6` Validadores: enmascarado, nombre de columna como contexto, tarjetas de relleno y tablas PDF en una línea | HU-05, HU-10 |
| 14/10 | CF | `62fea29` Bases de datos en solo lectura, base interna con originales cifrados y API por módulos | HU-08, HU-09, HU-11 |
| 14/10 | CF | `4b91834` Web nueva con diseño propio: inicio, archivos, asistente de base de datos, resultados y historial | HU-13, HU-14 |
| 14/10 | CF | `95e4536` Planillas (csv, xlsx, xls) como tablas con clasificación por columna y RUT cortos con contexto | HU-07 |
| 15/10 | CF | `4e4cbb2` Mantenedor de reglas: crear reglas sin programar, probarlas en vivo y ajustar los validadores incluidos | HU-18, HU-19 |
| 15/10 | CF | `1e97ce9` README: mantenedor de reglas | Documentación |
| 15/10 | CF | `082f17f` Reglas más simples: asistente de 3 pasos que arma el patrón desde ejemplos, opciones en palabras y prueba e… | HU-18 |
| 15/10 | CF | `8e10e3f` Ordenar hallazgos por riesgo, tipo, confianza o ubicación desde los encabezados de la tabla | HU-13 |
| 15/10 | CF | `738f68d` Preparado para la nube: render.yaml, conexión a Neon y candado de acceso mientras no haya login | HU-24 |
| 15/10 | CF | `cbd198a` render.yaml: región Ohio, junto a la base de Neon | HU-24 |
| 15/10 | CF | `eba8c14` Neon: sin consultas preparadas, para funcionar con su agrupador de conexiones | HU-24 |
| 15/10 | CF | `1799246` Delete k-secure directory | Reorganización del repositorio |
| 15/10 | CF | `030c96f` Mover el proyecto a k-secure-web/ para publicarlo en el repositorio Capstone del equipo | Reorganización del repositorio |
| 15/10 | CF | `0473ddf` README: rutas dentro de k-secure-web | Documentación |
| 15/10 | CF | `3e6a758` Demo de base de un cliente ficticio y PostgreSQL en solo lectura compatible con Neon | HU-08, HU-09 |
| 15/10 | CF | `75af039` Documento de arquitectura: cómo se construyó K-Secure, para la presentación y para continuar el trabajo | Documentación |
| 16/10 | EF | `66cda67` documentación de la 2da entrega | Entrega Fase 2 |
| 26/10 | EF | `ce88693` K-Secure: vista por tipo de dato, cliente simulado, logos transparentes y diálogos propios | HU-13 |

### Sprint 6 (27/10 – 09/11)

| Fecha | Integrante | Commit | Historia / aporte |
|---|---|---|---|
| 28/10 | EF | `62c21e0` K-Secure: login con roles Admin, Auditor y Visor | HU-20, HU-21 |
| 28/10 | EF | `0d4370b` K-Secure: recuperar contraseña por correo y restablecer desde la terminal | HU-22 |
| 28/10 | EF | `691127d` K-Secure: bitácora, página Seguridad, exportar resultados y revisión de hallazgos | HU-15, HU-16, HU-23 |
| 30/10 | MC | `3301956` Delete Entrega 2 Documentacion directory | Entrega Fase 2 |
| 30/10 | MC | `74861c6` Add files via upload | Entrega Fase 2 |
| 05/11 | EF | `40b3cc8` Diario 2.1 y entregas Fase 1 con el formato de nombre pedido | Entregas Fase 1 y 2 |
| 05/11 | EF | `4070e80` ERS: login, recuperación, exportación, revisión y bitácora implementados | Documentación |
| 05/11 | EF | `cddab00` Plan de pruebas, requisitos no funcionales y pruebas de integración y seguridad | HU-26 |
| 05/11 | EF | `8a58a9e` Marco de clasificación de datos (OE5) | Documentación (OE5) |
| 06/11 | MC | `c12c65b` Diario 2.1 individual y entregas Fase 1 con el formato de nombre pedido | Entregas Fase 1 y 2 |
| 06/11 | MC | `10458e5` Presentación del proyecto Fase 1 | Entrega Fase 1 |
| 06/11 | MC | `7510fde` Presentación del proyecto Fase 2 | Entrega Fase 2 |
| 06/11 | MC | `fcd35bd` Documento de inicio, metodología Scrum, artefactos ágiles, trazabilidad e innovación | Documentación |
| 06/11 | MC | `c50d9de` README con índice de evidencias | Documentación |
| 06/11 | CF | `5bc45d6` Diario 2.1 y entregas Fase 1 con el formato de nombre pedido | Entregas Fase 1 y 2 |
| 06/11 | CF | `eec08e9` Docker (app + PostgreSQL + cliente demo) y pruebas de rendimiento | HU-25, HU-26 |
| 06/11 | CF | `ef45ec3` Modelo entidad-relación, diagramas UML, manual técnico y .mailmap | HU-28, documentación |
| 06/11 | EF | `7c4c7d1` Organizar entregas de la Fase 1 en la carpeta Fase 1 | Entregas por fase |
| 06/11 | EF | `a3552a6` Organizar entregas de la Fase 2 en la carpeta Fase 2 | Entregas por fase |
| 06/11 | EF | `122ae94` Marco de clasificación: plan de alineación con la política de Duoc UC | Documentación (OE5) |

### Sprint 7 (10/11 – 23/11)

| Fecha | Integrante | Commit | Historia / aporte |
|---|---|---|---|
| 13/11 | MC | `7f7cd2a` README e índice de evidencias con la estructura por fases | Documentación |
| 16/11 | EF | `83294d1` Plan de pruebas: evidencia de pruebas por sprint | HU-26 |
| 16/11 | MC | `21ce3a3` Documento de diseño: arquitectura, comunicación entre servicios, Docker y decisiones técnicas | Documentación |
| 16/11 | MC | `b2ccc6f` Requisitos no funcionales: escalabilidad | RNF-17, RNF-18 |
| 18/11 | MC | `4c9defe` HU-27: lectura determinista de tablas (ORDER BY por llave primaria) y sus pruebas | HU-27 |
| 18/11 | MC | `abff88e` Documentación: HU-27 terminada (RNF-08 cumplido, 240 pruebas) | HU-27 |
| 18/11 | MC | `f176be6` HU-27: lectura determinista de tablas (ORDER BY por llave primaria) y sus pruebas | HU-27 (subida corregida) |
| 18/11 | MC | `2c95508` Documentación: HU-27 terminada (RNF-08 cumplido, 240 pruebas) | HU-27 (subida corregida) |
| 18/11 | MC | `a009985` HU-27: mover el código, las pruebas y la documentación a su lugar | HU-27 |
| 18/11 | MC | `0b7d22e` Retrospectiva del sprint 6 | Retrospectiva |
| 18/11 | CF | `a5634f4` HU-29: guardar los hallazgos por lotes para escanear archivos grandes con poca memoria | HU-29 |
| 18/11 | EF | `6c18b2b` RNF-18: escanear archivos en un hilo aparte para no bloquear a los demás usuarios | RNF-18 |
| 18/11 | EF | `1798bea` HU-17: comparar dos escaneos (API y pruebas) | HU-17 |
| 18/11 | EF | `1a154ab` HU-17: página para comparar escaneos y enlace desde el historial | HU-17 |
| 18/11 | EF | `beff3da` Documentación del sprint 7: HU-17, HU-29 y RNF-18 terminadas, backlogs al día y 257 pruebas | Documentación |

> HU-27 aparece dos veces porque la primera subida quedó dentro de la carpeta del zip; se volvió a subir y se movió
> a su lugar (`a009985`), como se registra en la retrospectiva del sprint 7. Los commits de cierre del sprint
> (retrospectiva y backlogs, 23/11) se suman en la entrega final.

### Commits por sprint e integrante

| Sprint | CF | EF | MC | Total |
|---|---|---|---|---|
| 2 | 0 | 0 | 2 | 2 |
| 3 | 0 | 1 | 0 | 1 |
| 4 | 3 | 1 | 0 | 4 |
| 5 | 20 | 2 | 0 | 22 |
| 6 | 3 | 10 | 7 | 20 |
| 7 | 1 | 5 | 9 | 15 |
| **Total** | **27** | **19** | **18** | **64** |

> Varias entregas se subieron desde la web de GitHub (*Add files via upload*) y la primera versión se subió en
> bloque, por eso hay sprints con pocos commits. Desde el sprint 6 el equipo acordó hacer commits por tarea terminada
> con su propio usuario (ver [Retrospectivas](05_Retrospectivas.md)).
