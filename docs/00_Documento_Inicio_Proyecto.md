# Documento de inicio del proyecto (Acta de constitución) — K-Secure

| | |
|---|---|
| **Proyecto** | K-Secure: Sistema de Clasificación de Datos Sensibles |
| **Asignatura** | Capstone PTY4614 · Portafolio de Título · Ingeniería en Informática |
| **Institución** | Duoc UC, sede Padre Alonso de Ovalle · Sección PTY4614-003 · Equipo 2 |
| **Docente** | Ceferino Aníbal Sotelo |
| **Equipo** | Camilo Fuenzalida · Martín Campos · Emanuel Farías |
| **Metodología** | Scrum adaptado (ver [`agil/00_Metodologia.md`](agil/00_Metodologia.md)) |
| **Repositorio** | https://github.com/Martin1421cl/Capstone (código en `k-secure-web/`) |
| **Versión** | 1.1 · 31/10/2026 (la 1.0 es la Guía 1.5 de la Fase 1) |

Este documento reúne en un solo lugar la definición del proyecto. Parte de la
[Guía 1.5 – Definición del proyecto](<../Fase 1/Grupal/1.5_GuiaEstudiante_Fase1_DefinicionProyecto (1).docx>) entregada en la
Fase 1 y agrega lo decidido durante la Fase 2.

---

## 1. Problema

Las organizaciones almacenan grandes volúmenes de datos **sin saber con certeza qué información sensible contienen
sus propios sistemas**. En Chile esos datos incluyen RUT, celulares, tarjetas de pago, cuentas bancarias y patentes,
repartidos en planillas, documentos y bases de datos.

Esto genera tres problemas concretos:

1. **Riesgo de fuga de información:** no se puede proteger lo que no se sabe que existe.
2. **Los DLP no pueden operar bien:** las soluciones de prevención de fuga de datos (DLP) necesitan una
   **clasificación previa** de la información para saber qué bloquear.
3. **Las herramientas existentes no entienden los datos chilenos:** muchas herramientas de clasificación no reconocen
   identificadores propios de Chile, como el RUT con su dígito verificador.

A esto se suma la **Ley 21.719** de protección de datos personales, que entra en vigencia el 1 de diciembre de 2026
y obliga a las organizaciones a saber qué datos personales tratan y a protegerlos.

## 2. Justificación

- **Relevancia:** el inventario de datos sensibles es el primer paso para cumplir la Ley 21.719 y para que un DLP funcione.
  Hoy se hace a mano o no se hace.
- **Pertinencia con el perfil de egreso:** el proyecto pone en práctica desarrollo de software (motor de escaneo),
  análisis de algoritmos (Módulo 11, Luhn, análisis de contexto), seguridad de la información (cifrado, control de
  acceso) y gestión y gobierno de datos (marco de clasificación).
- **Factibilidad:** el alcance es acotado a la **capa de clasificación**, no a un DLP completo; las técnicas
  (expresiones regulares y validaciones matemáticas) son manejables para un equipo de tres personas; se usan datos
  sintéticos y servicios en la nube gratuitos.
- **Valor diferencial:** se basa en un diseño probado (ferret-scan, de AWS Labs) adaptado a los datos chilenos.
  Ver [`Innovacion.md`](Innovacion.md).

## 3. Objetivos

### Objetivo general

Desarrollar desde cero un sistema de clasificación automática de datos sensibles adaptado al contexto chileno, capaz
de identificar información crítica (como el RUT) mediante expresiones regulares y validación matemática, para generar
reportes que alimenten sistemas DLP.

### Objetivos específicos

| N.º | Objetivo específico (Guía 1.5) | Cómo se cumple | Estado |
|---|---|---|---|
| OE1 | Diseñar la arquitectura del motor de escaneo de forma escalable a distintos orígenes de datos | Arquitectura por capas basada en ferret-scan: preprocesadores por tipo de archivo y conectores a 4 motores de bases de datos ([`diagramas/`](diagramas/)) | ✅ |
| OE2 | Implementar la lógica de detección combinando expresiones regulares y Módulo 11 para reducir falsos positivos | 7 validadores con confianza 0–100 y análisis de contexto | ✅ |
| OE3 | Desarrollar un módulo de reportes clasificados por nivel de riesgo | Resultados por riesgo y tipo; exportación CSV, JSON y PDF | ✅ |
| OE4 | Probar el sistema con pruebas iterativas y distintos conjuntos de datos | 235 pruebas automáticas y base de cliente simulado ([`Plan_de_Pruebas.md`](Plan_de_Pruebas.md)) | ✅ |
| OE5 | Documentar los niveles de clasificación y políticas de manejo (whitepaper OEA/AWS y política de Duoc UC) | [`Marco_de_Clasificacion_de_Datos.md`](Marco_de_Clasificacion_de_Datos.md) | 🔄 |
| OE6 | Integrar el motor y los reportes en un flujo único de extremo a extremo | Aplicación web: subir o conectar → escanear → revisar → exportar | ✅ |
| OE7 | Planificar y controlar el avance con checkpoints periódicos | Sprints de 2 semanas, Sprint Backlog y retrospectivas ([`agil/`](agil/)) | ✅ |

## 4. Stakeholders (interesados)

| Interesado | Rol en el proyecto | Interés / necesidad | Influencia |
|---|---|---|---|
| **Encargado de seguridad de la información o cumplimiento** (empresa cliente) | Usuario principal (rol Auditor o Admin) | Inventario de datos sensibles y evidencia para auditorías y la Ley 21.719 | Alta |
| **Área de TI del cliente** | Instala la herramienta y autoriza el acceso de lectura a las bases | Que K-Secure no modifique datos ni afecte sus sistemas | Alta |
| **Auditores internos** | Revisan hallazgos y ven originales con autorización (rol Auditor) | Trazabilidad de quién vio qué dato | Media |
| **Jefaturas y áreas de negocio** | Consultan resultados (rol Visor) | Saber el nivel de riesgo de su información | Media |
| **Titulares de los datos** (clientes y trabajadores de la empresa) | Afectados indirectos | Que sus datos no queden expuestos | Media |
| **Docente guía de Capstone** | Valida alcance, metodología y entregas | Proyecto con impacto en el mercado y bien documentado | Alta |
| **Equipo de desarrollo** | Construye y documenta K-Secure | Cumplir los objetivos y aprobar la asignatura | Alta |

## 5. Alcance del MVP

### Incluido

1. Escaneo de **archivos**: Word, Excel (xlsx y xls), PowerPoint, PDF, OpenDocument, CSV, TXT, JSON y bases SQLite.
2. Escaneo de **bases de datos** PostgreSQL, MySQL/MariaDB, SQL Server y Oracle, siempre en **solo lectura**.
3. **Validadores chilenos:** RUT (Módulo 11), celulares y fijos (+56), tarjetas (Luhn), correos, cuentas bancarias,
   patentes y claves de acceso.
4. **Clasificación** por confianza (HIGH / MEDIUM / LOW) y por riesgo (Público / Interno / Confidencial / Restringido),
   también por columna.
5. **Protección:** valores siempre enmascarados; originales cifrados que solo se ven con la clave de auditor.
6. **Reglas sin programar** creadas a partir de ejemplos del dato.
7. **Cuentas con roles** (Admin, Auditor, Visor), sin registro público, con recuperación de contraseña por correo.
8. **Reportes** exportables (CSV, JSON y PDF), revisión de hallazgos y bitácora de auditoría.
9. Despliegue en la **nube** (Render + Neon) y en **servidor propio** (Docker).

### Fuera del alcance

- Construir un DLP completo: bloquear, cifrar o borrar datos en los sistemas del cliente.
- Monitoreo continuo en tiempo real de correos, endpoints o tráfico de red.
- Reconocimiento de datos dentro de imágenes o documentos escaneados (OCR).
- Aplicación de escritorio (`.exe`): se reemplazó por la versión web (ver decisión D4).

## 6. Restricciones

| Tipo | Restricción |
|---|---|
| Tiempo | Plazos del semestre y de las tres fases de la asignatura; entrega final el 01/12/2026 |
| Equipo | 3 integrantes, que comparten el proyecto con otras asignaturas |
| Costo | Sin presupuesto: herramientas de código abierto y planes gratuitos (Render, Neon) |
| Datos | Solo datos **sintéticos** para probar; nunca datos reales de personas |
| Seguridad | K-Secure no puede modificar las bases del cliente ni guardar datos originales en claro |
| Uso | El cliente no debe tocar código: la herramienta se entrega lista para usar |
| Infraestructura | El plan gratis de Render tiene 512 MB de RAM (ver [`Requisitos_No_Funcionales.md`](Requisitos_No_Funcionales.md)) |

## 7. Supuestos

- La empresa cliente entrega un usuario de solo lectura para sus bases de datos.
- Los usuarios acceden con un navegador actual y conexión a internet (o a la red donde esté instalado).
- El docente valida el alcance en cada entrega y sus observaciones se incorporan al Product Backlog.

## 8. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Falsos positivos o negativos en la detección | Media | Alto | Validación matemática (Módulo 11, Luhn), análisis de contexto, revisión de hallazgos y pruebas con datos sintéticos |
| Retraso por cambios de alcance (como la reescritura de la Fase 2) | Media | Alto | Sprints cortos y backlog priorizado (MoSCoW) |
| Carga de trabajo concentrada en un integrante | Alta | Medio | Repartir historias por módulo en cada planificación de sprint (ver retrospectivas) |
| Memoria insuficiente en la nube al escanear archivos grandes | Alta | Medio | Límite práctico en la demo; Docker en servidor propio; optimización en HU-29 |
| Dependencia de servicios gratuitos (Render, Neon, Apps Script) | Media | Medio | Instalación alternativa con Docker y base SQLite local |
| Pérdida de la clave de auditor | Baja | Alto | Documentado en el manual técnico; los originales no se pueden recuperar por diseño |
| Fuga de datos desde la propia herramienta | Baja | Alto | Enmascarado, cifrado RSA + AES, roles, bloqueo por intentos y bitácora |

## 9. Entregables e hitos

| Hito | Fecha | Entregables |
|---|---|---|
| Fase 1 – Definición | 03/09/2026 | Guía 1.5, informe 1.4, presentación, autoevaluaciones 1.1–1.3 |
| Primera versión | 28/09/2026 | Prototipo con FastAPI, validadores y pruebas (luego reemplazado) |
| Reescritura publicada | 15/10/2026 | K-Secure web en Render + Neon |
| Fase 2 – Avance | 16/10/2026 – 30/10/2026 | Informe 2.3, guías 2.4 y 2.6, diario 2.1, ERS, casos de uso, SAD 4+1 |
| Cuentas y seguridad | 28/10/2026 | Login con roles, recuperación, bitácora, exportación, revisión |
| Documentación y Docker | Sprint 6 (hasta 09/11/2026) | Artefactos ágiles, diagramas, plan de pruebas, manual técnico, Docker |
| Cierre del desarrollo | Sprint 7 (hasta 23/11/2026) | Pendientes (HU-17, HU-27, HU-29), pruebas de aceptación y ensayo |
| **Fase 3 – Entrega final** | **01/12/2026** | Informe final, presentación y demostración en vivo |

## 10. Registro de decisiones del proyecto

| N.º | Fecha | Decisión | Motivo |
|---|---|---|---|
| D1 | Fase 1 | Construir solo la **capa de clasificación**, no un DLP completo | Alcance factible para 3 personas en un semestre |
| D2 | Oct. 2026 | Seguir el **diseño de ferret-scan** (AWS Labs), adaptado a Chile | Indicación del docente; arquitectura probada |
| D3 | Oct. 2026 | **Rehacer K-Secure desde cero** | El código de la primera versión era difícil de mantener |
| D4 | Oct. 2026 | **Aplicación web** en vez de `.exe` | El cliente no debe tocar código ni actualizar cada equipo |
| D5 | Oct. 2026 | **Login con roles, sin registro público**; recuperación con código al correo | Las cuentas las controla la empresa; acceso solo de personas autorizadas |
| D6 | Oct. 2026 | **Render + Neon** (gratis), ambos en AWS us-east-2 | Sin costo y con despliegue automático desde GitHub |
| D7 | Oct. 2026 | Correos por **Apps Script de Gmail** | El plan gratis de Render bloquea SMTP |
| D8 | Oct. 2026 | Probar con una **base de cliente simulado** (empresa ficticia, datos sintéticos) | Validar la conexión a bases de clientes sin usar datos reales |
| D9 | Oct. 2026 | **Docker** como forma de instalación en servidor propio | No depender del sistema operativo ni de un proveedor de nube |

## 11. Aprobación

| Rol | Nombre | Fecha |
|---|---|---|
| Equipo | Camilo Fuenzalida, Martín Campos, Emanuel Farías | |
| Docente | Ceferino Aníbal Sotelo | |
