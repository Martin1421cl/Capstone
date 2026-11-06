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
| 6 | 27/10 – 09/11 | Fase 2 → 3 | Cuentas y seguridad, reportes, Docker, pruebas y documentación | 41 | 30 (en curso) |
| 7 | 10/11 – 23/11 | Fase 3 | Cierre: pendientes, pruebas finales y presentación | 15 | — |
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

## Sprint 6 — Cuentas, seguridad y entrega (27/10 – 09/11) · *sprint actual*

**Objetivo:** cerrar los requisitos de seguridad pendientes y dejar el proyecto listo para instalar, probar y evaluar.

| Historia | Tareas | Responsable | Pts | Estado |
|---|---|---|---|---|
| HU-20, HU-21 | Login con roles Admin, Auditor y Visor, sin registro público (28/10) | EF | 10 | ✅ |
| HU-22 | Recuperar contraseña por correo y restablecer desde la terminal (28/10) | EF | 5 | ✅ |
| HU-23 | Bitácora de auditoría (28/10) | EF | 5 | ✅ |
| HU-15, HU-16 | Exportar CSV/JSON/PDF y revisión de hallazgos (28/10) | EF | 10 | ✅ |
| — | Documentos de la Fase 2 (2.1, 2.3, 2.4, 2.6) y autoevaluaciones (30/10) | MC | — | ✅ |
| HU-25 | Dockerfile, docker-compose y `.env.example` | CF | 3 | 🔄 |
| HU-26 | Plan de pruebas y pruebas de integración, seguridad y rendimiento | CF, EF | 5 | 🔄 |
| HU-28 | Manual técnico | MC | 3 | 🔄 |
| — | README en la raíz, artefactos ágiles, modelo ER y diagramas UML | MC, CF | — | 🔄 |
| | | **Total** | **41** | |

## Sprint 7 — Cierre (10/11 – 23/11) · *planificado*

**Objetivo:** terminar los pendientes y preparar la presentación final.

| Historia | Tareas | Responsable | Pts | Estado |
|---|---|---|---|---|
| HU-27 | `ORDER BY` por llave primaria al leer tablas | CF | 2 | ⏳ |
| HU-17 | Comparar dos escaneos de la misma fuente | EF | 8 | ⏳ |
| HU-29 | Escaneo de archivos grandes por lotes (menos memoria) | CF | 5 | ⏳ |
| — | Prueba con la base del cliente simulado en Neon | EF | — | ⏳ |
| — | Informe final, presentación y ensayo | Todo el equipo | — | ⏳ |

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

### Commits por sprint e integrante

| Sprint | CF | EF | MC | Total |
|---|---|---|---|---|
| 2 | 0 | 0 | 2 | 2 |
| 3 | 0 | 1 | 0 | 1 |
| 4 | 3 | 1 | 0 | 4 |
| 5 | 20 | 2 | 0 | 22 |
| 6 | 0 | 3 | 2 | 5 |
| **Total** | **23** | **7** | **4** | **34** |

> Varias entregas se subieron desde la web de GitHub (*Add files via upload*) y la primera versión se subió en
> bloque, por eso hay sprints con pocos commits. Desde el sprint 6 el equipo acordó hacer commits por tarea terminada
> con su propio usuario (ver [Retrospectivas](05_Retrospectivas.md)).
