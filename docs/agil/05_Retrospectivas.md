# Retrospectivas — K-Secure

Al cierre de cada sprint el equipo se reúne y responde tres preguntas: **¿qué salió bien?**, **¿qué salió mal?**
y **¿qué vamos a cambiar?** Cada acción de mejora tiene un responsable y se revisa en la retrospectiva siguiente.

**Equipo:** Camilo Fuenzalida, Emanuel Farías, Martín Campos.

> **Nota:** los sprints 1 a 5 se documentaron el 31/10/2026 a partir del historial del repositorio, las
> autoevaluaciones, los diarios de reflexión y la retroalimentación del docente de cada fase. Desde el sprint 6
> se registran al cierre de cada sprint.

---

## Retrospectiva Sprints 1 y 2 — Fase 1 (14/09)

| ✅ Qué salió bien | ❌ Qué salió mal | 🔧 Qué vamos a cambiar |
|---|---|---|
| Acordamos rápido el problema: datos sensibles chilenos como insumo para un DLP. | La definición del proyecto quedó general: alcance del MVP y stakeholders poco detallados. | Detallar el alcance del MVP en el Product Vision. |
| La carta Gantt dio un orden claro de las actividades. | Los documentos se subieron todos juntos, con nombres que no siguen el formato pedido. | Subir cada entrega con el formato `Apellido_Nombre_...`. |

**Acciones:** detallar el alcance (MC) · revisar los nombres de archivo antes de cada entrega (MC).

---

## Retrospectiva Sprint 3 — Primera versión (28/09)

| ✅ Qué salió bien | ❌ Qué salió mal | 🔧 Qué vamos a cambiar |
|---|---|---|
| Tuvimos una versión funcional: API, base de datos, validadores y pruebas. | La configuración del entorno (PostgreSQL, variables, dependencias) tomó más tiempo del planificado. | Automatizar la instalación con un script (`setup_db.ps1`). |
| Dividir el trabajo por módulos permitió avanzar en paralelo. | FastAPI y SQLAlchemy eran nuevas para el equipo: la curva de aprendizaje retrasó la integración. | Documentar cada paso para que cualquiera pueda levantar el proyecto. |
| | El avance quedó como una sola subida de archivos, sin commits incrementales. | Hacer commits frecuentes y descriptivos. |

**Acciones:** script de instalación (EF) · commits por tarea terminada (todos).

---

## Retrospectiva Sprint 4 — Retroalimentación del docente (12/10)

| ✅ Qué salió bien | ❌ Qué salió mal | 🔧 Qué vamos a cambiar |
|---|---|---|
| Escuchamos la retroalimentación del docente y la tomamos como oportunidad. | El código de la primera versión era difícil de mantener ("código tallarín"). | **Rehacer K-Secure desde cero** siguiendo el diseño de ferret-scan. |
| ferret-scan nos dio una arquitectura probada en la que basarnos. | El `.exe` no escala: una empresa con 1.000 equipos tendría que actualizar los 1.000. | Convertirlo en **aplicación web** publicada en la nube. |
| | Reiniciar el desarrollo retrasa objetivos de la carta Gantt. | Acotar el alcance a la capa de clasificación que alimenta al DLP. |

**Acciones:** nueva arquitectura por capas (CF) · publicar en Render + Neon (CF) · actualizar la Gantt (MC).

---

## Retrospectiva Sprint 5 — Reescritura (26/10)

| ✅ Qué salió bien | ❌ Qué salió mal | 🔧 Qué vamos a cambiar |
|---|---|---|
| En dos semanas la reescritura quedó funcionando y publicada en la nube. | La carga se concentró en una persona (CF), lo que es un riesgo para el equipo. | Repartir mejor: EF toma cuentas y seguridad, MC la documentación formal. |
| El diseño por capas permitió agregar reglas sin tocar el motor. | El repositorio muestra poco aporte de algunos integrantes: subidas por la web y usuarios de GitHub no identificados. | Cada integrante configura `git config user.name` y `user.email` con su nombre real. |
| Las pruebas automáticas (210) dieron confianza para cambiar código. | Login, exportación y bitácora seguían pendientes (RF-13 a RF-17). | Priorizarlos en el sprint 6. |

**Acciones:** login y roles (EF) · bitácora y exportación (EF) · configurar git (todos) · documentación formal (MC).

---

## Retrospectiva Sprint 6 — Cuentas, seguridad y entrega (09/11)

> *Pendiente: se completa en la reunión de cierre del sprint 6.*

| ✅ Qué salió bien | ❌ Qué salió mal | 🔧 Qué vamos a cambiar |
|---|---|---|
| | | |

**Acciones:**
