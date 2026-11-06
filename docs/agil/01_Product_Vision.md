# Product Vision — K-Secure

**Proyecto:** K-Secure · Capstone PTY4614-003 · Equipo 2
**Integrantes:** Camilo Fuenzalida, Emanuel Farías, Martín Campos
**Metodología:** Scrum adaptado (sprints de 2 semanas)

---

## Declaración de visión

> **Para** las empresas chilenas que manejan datos personales de clientes y trabajadores,
> **que** no saben dónde están esos datos dentro de sus documentos y bases de datos,
> **K-Secure** es una aplicación web de **descubrimiento y clasificación de datos sensibles**
> **que** encuentra RUT, celulares, tarjetas, cuentas bancarias, patentes, correos y claves de acceso,
> y los clasifica por nivel de riesgo sin exponer nunca el dato original.
> **A diferencia de** las herramientas DLP comerciales (costosas y pensadas para formatos de otros países)
> o de revisar a mano,
> **nuestro producto** entiende los datos chilenos (RUT con Módulo 11, celulares +56, patentes PPU,
> bancos chilenos), se usa desde el navegador sin instalar nada en cada equipo y permite crear reglas
> nuevas sin programar.

---

## Product Vision Board

| Visión | Grupo objetivo | Necesidades | Producto | Objetivos de negocio |
|---|---|---|---|---|
| Que cualquier empresa chilena sepa **dónde** tiene datos sensibles, **de qué tipo** son y **qué tan grave** sería que se filtren. | Encargados de seguridad de la información, TI y cumplimiento (compliance) de empresas medianas y grandes. Auditores internos. | Cumplir la Ley 21.719 de protección de datos personales. Inventariar datos sensibles antes de aplicar un DLP. No exponer los datos mientras se revisan. Revisar bases de datos sin riesgo de modificarlas. | Aplicación web con escaneo de archivos y bases de datos (solo lectura), clasificación por confianza y riesgo, enmascarado y bóveda cifrada, reglas sin programar, roles, bitácora y reportes exportables. | Reducir el tiempo de inventario de datos sensibles de semanas a minutos. Alimentar a una solución DLP con la clasificación. Dejar trazabilidad de quién vio qué dato (auditoría). |

---

## Usuarios (roles)

| Rol | Quién es | Qué necesita de K-Secure |
|---|---|---|
| **Administrador** | Encargado de TI o de seguridad | Crear cuentas, definir la clave de auditor, ajustar reglas, revisar la bitácora |
| **Auditor** | Analista de seguridad o cumplimiento | Escanear archivos y bases, revisar hallazgos, ver un original cuando sea necesario, exportar reportes |
| **Visor** | Jefatura o área de negocio | Ver los resultados enmascarados y el nivel de riesgo de su información |

---

## Alcance del MVP

**Incluido:**

1. Escaneo de archivos (Office, PDF, OpenDocument, CSV, TXT, JSON, SQLite) y de bases PostgreSQL, MySQL, SQL Server y Oracle en solo lectura.
2. Validadores chilenos con confianza 0–100 y riesgo Público / Interno / Confidencial / Restringido.
3. Clasificación por columna en bases de datos y planillas.
4. Enmascarado de todos los valores y bóveda cifrada para ver originales con la clave de auditor.
5. Reglas personalizadas creadas desde ejemplos del dato.
6. Login con roles, sin registro público, y recuperación de contraseña por correo.
7. Bitácora, revisión de hallazgos (confirmado / falso positivo) y exportación a CSV, JSON y PDF.

**Fuera del alcance:**

- Bloquear o cifrar los datos en el sistema del cliente (eso lo hace el DLP).
- Escaneo continuo en tiempo real de correos o tráfico de red.
- Reconocimiento de datos en imágenes (OCR).

---

## Restricciones

- Equipo de 3 personas y plazos del semestre académico.
- Infraestructura gratuita (Render + Neon).
- El cliente no debe tocar código: la solución debe entregarse lista para usar.
- K-Secure nunca debe modificar ni guardar en claro los datos del cliente.

---

## Indicadores de éxito

| Indicador | Meta | Estado |
|---|---|---|
| Columnas sensibles detectadas en la base demo | 100 % sin falsos positivos | 9 de 9, 0 falsos positivos (RNF-07) |
| Tiempo de escaneo de 100.000 filas | ≤ 60 s | 32 s (RNF-06) |
| Pruebas automáticas que pasan | 100 % | 235 de 235 |
| Datos originales guardados en claro | 0 | 0 (RNF-02) |
