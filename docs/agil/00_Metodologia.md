# Metodología de trabajo — K-Secure

**Metodología declarada: Scrum adaptado** a un equipo de tres personas y a los plazos del semestre.

En la Guía 1.5 (Fase 1, sección 5) el equipo declaró un **enfoque de desarrollo ágil** en cinco etapas. Este documento
precisa el marco concreto con el que se aplica ese enfoque: **Scrum**, con sprints de dos semanas.

---

## 1. Justificación: ¿por qué Scrum?

| Criterio del proyecto | Cascada | Kanban | **Scrum** |
|---|---|---|---|
| Requisitos que cambian con la retroalimentación del docente | Obliga a rehacer el análisis completo | Se adapta, pero sin cortes de revisión | **Se incorporan en el sprint siguiente** |
| Entregas en fechas fijas (fases de la asignatura) | Una entrega al final | Flujo continuo, sin hitos | **Un incremento funcional por sprint, alineado con las fases** |
| Equipo pequeño que trabaja por módulos | Etapas secuenciales | Adecuado | **Adecuado: cada uno toma historias de su módulo** |
| Necesidad de validar supuestos técnicos temprano (¿Módulo 11 reduce falsos positivos?) | Se valida tarde, en la etapa de pruebas | Posible | **Se valida en cada sprint con pruebas automáticas** |
| Aprendizaje del equipo (FastAPI, SQLAlchemy, cifrado) | Sin instancia formal | Sin instancia formal | **Retrospectiva al cierre de cada sprint** |

**Conclusión:** el alcance de K-Secure **cambió durante el proyecto** (el docente pidió seguir el diseño de ferret-scan,
se descartó el `.exe` y se rehízo el sistema como aplicación web). Con cascada ese cambio habría obligado a rehacer el
análisis y el diseño completos; con Scrum se incorporó en el sprint 4 y en el sprint 5 ya había una versión web
publicada. Se descartó Kanban porque la asignatura exige entregas en fechas fijas y revisiones formales, que Scrum
ordena con sus sprints y ceremonias.

---

## 2. Roles

| Rol Scrum | Responsable | Responsabilidades |
|---|---|---|
| **Product Owner** | Martín Campos | Mantiene y prioriza el Product Backlog; representa al cliente y recoge las observaciones del docente |
| **Scrum Master** | Camilo Fuenzalida | Facilita las ceremonias, controla el avance (rol de "planificar y controlar el proyecto" de la Guía 1.5) y elimina bloqueos |
| **Equipo de desarrollo** | Camilo Fuenzalida, Emanuel Farías, Martín Campos | Construyen, prueban y documentan cada historia hasta cumplir la Definition of Done |
| **Stakeholder principal** | Docente Ceferino Aníbal Sotelo | Revisa cada incremento y valida el alcance |

---

## 3. Ceremonias

| Ceremonia | Cuándo | Duración | Resultado |
|---|---|---|---|
| **Planificación del sprint** | Primer día del sprint | 1 hora | Objetivo del sprint e historias elegidas, divididas en tareas ([Sprint Backlog](03_Sprint_Backlog.md)) |
| **Seguimiento semanal** (*daily* adaptado) | Una vez por semana, más mensajes en el grupo del equipo | 15–30 min | Qué hice, qué haré, qué me bloquea |
| **Revisión del sprint** | Último día del sprint, idealmente con el docente en clase | 30 min | Demostración del incremento; historias marcadas ✅ en el [Product Backlog](02_Product_Backlog.md) |
| **Retrospectiva** | Después de la revisión | 30 min | Qué salió bien, qué salió mal y qué vamos a cambiar ([Retrospectivas](05_Retrospectivas.md)) |

El seguimiento es semanal y no diario porque el equipo comparte el proyecto con otras asignaturas.

---

## 4. Artefactos

| Artefacto | Documento |
|---|---|
| Visión del producto | [`01_Product_Vision.md`](01_Product_Vision.md) |
| Product Backlog (historias de usuario, prioridad MoSCoW, puntos) | [`02_Product_Backlog.md`](02_Product_Backlog.md) |
| Sprint Backlog (tareas, responsables, fechas y commits) | [`03_Sprint_Backlog.md`](03_Sprint_Backlog.md) |
| Definition of Done y criterios de aceptación | [`04_Definition_of_Done.md`](04_Definition_of_Done.md) |
| Retrospectivas | [`05_Retrospectivas.md`](05_Retrospectivas.md) |
| Incremento | Código en `k-secure-web/`, publicado en Render en cada `git push` a `main` |

---

## 5. Cadencia: sprints y fases de la asignatura

| Sprint | Fechas | Fase | Etapa de la Guía 1.5 |
|---|---|---|---|
| 1 | 18/08 – 31/08 | Fase 1 | (1) Definición de la arquitectura y del modelo de datos |
| 2 | 01/09 – 14/09 | Fase 1 | (1) Definición, repositorio y entrega de la Fase 1 |
| 3 | 15/09 – 28/09 | Fase 2 | (2) Diseño de la validación y (3) primera construcción |
| 4 | 29/09 – 12/10 | Fase 2 | (1) Rediseño de la arquitectura según ferret-scan y (2) validación del RUT |
| 5 | 13/10 – 26/10 | Fase 2 | (3) Construcción del motor y de los reportes |
| 6 | 27/10 – 09/11 | Fase 2 → 3 | (3) Cuentas y seguridad, (4) pruebas y (5) documentación |
| 7 | 10/11 – 23/11 | Fase 3 | (4) Pruebas finales, (5) documentación y cierre |
| — | 24/11 – 01/12 | Fase 3 | Entrega final (01/12) y presentación |

---

## 6. Estimación y priorización

- **Historias de usuario** con el formato *Como [rol], quiero [acción], para [beneficio]* y criterios de aceptación.
- **Prioridad MoSCoW:** M (debe tener), S (debería), C (podría), W (no en esta versión).
- **Estimación** en puntos de historia con la escala de Fibonacci (1, 2, 3, 5, 8, 13), acordada en la planificación.
- **Velocidad:** se compara lo comprometido con lo terminado en cada sprint (resumen en el Sprint Backlog).

---

## 7. Herramientas

| Uso | Herramienta |
|---|---|
| Código, versiones y evidencia del avance | Git + GitHub (`Martin1421cl/Capstone`) |
| Backlog y documentación | Archivos Markdown en `docs/` (versionados junto al código) |
| Pruebas automáticas | pytest |
| Despliegue continuo | Render (despliega cada `git push` a `main`) |
| Planificación general | Carta Gantt de la Guía 1.5 |
