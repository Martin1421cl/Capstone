# Documento de diseño — K-Secure

**Proyecto:** K-Secure · Capstone PTY4614-003 · Equipo 2
**Versión:** 1.0 · 16/11/2026

Este documento reúne en un solo lugar el diseño de K-Secure: arquitectura, componentes, comunicación entre servicios,
modelo de datos, diagramas UML, diseño Docker y las **decisiones técnicas** con su justificación. Cada sección resume y
enlaza el documento que tiene el detalle.

| Tema | Detalle en |
|---|---|
| Arquitectura 4+1 | [`Fase 2/Grupal/05 - Documento de Arquitectura de Software (SAD 4+1).docx`](<../Fase 2/Grupal/05 - Documento de Arquitectura de Software (SAD 4+1).docx>) |
| Cómo se construyó y por qué | [`k-secure-web/docs/ARQUITECTURA.md`](../k-secure-web/docs/ARQUITECTURA.md) |
| Diagramas (ER y UML) | [`docs/diagramas/`](diagramas/) |
| Instalación y despliegue | [`docs/Manual_Tecnico.md`](Manual_Tecnico.md) |
| Requisitos no funcionales | [`docs/Requisitos_No_Funcionales.md`](Requisitos_No_Funcionales.md) |

---

## 1. Arquitectura

K-Secure es una **aplicación web en capas**. Un solo servidor (FastAPI) entrega las páginas y la API REST; el navegador
solo muestra datos. El motor de detección sigue el diseño de [ferret-scan](https://github.com/awslabs/ferret-scan)
(AWS Labs): los **preprocesadores** convierten cada archivo en texto o tabla y los **validadores** deciden qué es sensible
y con qué confianza. K-Secure agrega la clasificación de riesgo, el almacenamiento cifrado, las cuentas con roles y la web.

![Arquitectura general](diagramas/img/arquitectura_general.png)

| Capa | Paquete | Responsabilidad |
|---|---|---|
| Presentación | `ksecure/web/static/` | Páginas HTML, CSS y JavaScript (módulos ES, sin frameworks) |
| API | `ksecure/web/` | Endpoints REST, sesión y permisos por rol |
| Escaneo | `ksecure/escaneo/` | Qué se escanea: archivos subidos y tablas de bases de datos |
| Detección | `ksecure/preprocessors/`, `ksecure/validators/` | Cómo se lee cada formato y qué es sensible |
| Dominio | `ksecure/core/` | `Match`, niveles de confianza y de riesgo |
| Persistencia | `ksecure/almacenamiento/` | Base interna, bóveda de cifrado, usuarios, reglas y bitácora |

---

## 2. Componentes

![Componentes](diagramas/img/componentes.png)

Las dependencias van en un solo sentido (web → escaneo → detección → dominio) y el dominio no depende de nadie. Así,
agregar un tipo de dato nuevo es agregar un validador, sin tocar el motor. Detalle de cada componente y su interfaz en
[`diagramas/04_UML_Diagrama_de_Componentes.md`](diagramas/04_UML_Diagrama_de_Componentes.md).

---

## 3. Comunicación entre servicios

K-Secure se comunica con cinco servicios externos. Ninguno recibe un dato sensible en claro.

| Desde → hacia | Protocolo y formato | Autenticación | Seguridad y detalles |
|---|---|---|---|
| **Navegador → K-Secure** | HTTPS (HTTP en local) · JSON por `fetch` a `/api/...`; archivos como `multipart/form-data` | Cookie de sesión con un token al azar; en la base solo se guarda su hash | Cookie `HttpOnly`, `SameSite=Lax` y `Secure` en HTTPS. Las peticiones que modifican datos se rechazan si vienen de otro origen (protección CSRF). Cada endpoint revisa el rol mínimo |
| **K-Secure → base interna** | SQLAlchemy · SQLite (archivo local) o PostgreSQL con psycopg 3 | Usuario y contraseña en `KSECURE_DB_URL` | En Neon la conexión va cifrada (la URL que entrega Neon trae `sslmode=require`) y sin consultas preparadas, para funcionar con su agrupador de conexiones. En Docker: servicio `db`, puerto 5432 dentro de la red interna |
| **K-Secure → bases del cliente** | PostgreSQL (psycopg 3), MySQL/MariaDB (PyMySQL), SQL Server (pymssql), Oracle (oracledb, modo *thin*) | Credenciales que el auditor escribe en pantalla; **no se guardan** | Solo se ejecuta `SELECT`. Además: transacción `READ ONLY` en PostgreSQL, `SET SESSION TRANSACTION READ ONLY` en MySQL y modo `ro` en SQLite. Tiempo máximo de conexión: 10 s. Límite de filas por tabla: 1.000, 10.000 o 100.000 |
| **K-Secure → Apps Script de Gmail** | HTTPS · `POST` JSON (`para`, `asunto`, `texto`) | Secreto compartido (`KSECURE_CORREO_SECRETO`) en el cuerpo | Solo para el código de recuperación de contraseña. Espera máxima: 20 s. Sin configuración, el código se muestra en la consola del servidor |
| **GitHub → Render** | Webhook de Render | Integración de la cuenta | Cada `git push` a `main` vuelve a desplegar la app con `render.yaml` |

El flujo completo de las tres operaciones principales (escanear archivos, revelar un dato original e iniciar sesión)
está en [`diagramas/03_UML_Diagrama_de_Secuencia.md`](diagramas/03_UML_Diagrama_de_Secuencia.md).

---

## 4. Modelo de datos

La base interna tiene 9 tablas. Las principales son `escaneos` y `hallazgos` (1 a N), y `usuarios` con sus `sesiones` y
`codigos_recuperacion`. La `bitacora` no tiene llaves foráneas a propósito, para que un evento se conserve aunque se borre
el escaneo o la cuenta.

**Regla de diseño:** el dato original nunca se guarda en claro. Cada hallazgo tiene `valor_enmascarado` (para mostrar) y
`valor_cifrado` (para el auditor con su clave).

![Modelo entidad-relación](diagramas/img/er_base_interna.png)

Detalle de cada tabla, sus campos y la base del cliente simulado en
[`diagramas/01_Modelo_Entidad_Relacion.md`](diagramas/01_Modelo_Entidad_Relacion.md).

---

## 5. Diagramas UML

| Diagrama | Dónde está |
|---|---|
| Casos de uso | [`Fase 2/Grupal/04 - Especificación de Casos de Uso.docx`](<../Fase 2/Grupal/04 - Especificación de Casos de Uso.docx>) (CU-01 a CU-13) |
| Clases | [`diagramas/02_UML_Diagrama_de_Clases.md`](diagramas/02_UML_Diagrama_de_Clases.md) |
| Secuencia (escanear archivos, revelar un dato, iniciar sesión) | [`diagramas/03_UML_Diagrama_de_Secuencia.md`](diagramas/03_UML_Diagrama_de_Secuencia.md) |
| Componentes y despliegue | [`diagramas/04_UML_Diagrama_de_Componentes.md`](diagramas/04_UML_Diagrama_de_Componentes.md) |

---

## 6. Diseño Docker

![Despliegue](diagramas/img/despliegue.png)

`k-secure-web/docker-compose.yml` levanta tres servicios en una red interna:

| Servicio | Imagen | Puerto | Datos | Salud |
|---|---|---|---|---|
| `app` (`ksecure-app`) | Construida con `k-secure-web/Dockerfile` sobre `python:3.13-slim` | 8000 | — | `GET /api/health` cada 30 s |
| `db` (`ksecure-db`) | `postgres:16-alpine` | Solo red interna | Volumen `ksecure-datos` (persiste entre reinicios) | `pg_isready` cada 5 s |
| `cliente-demo` (perfil `demo`) | `postgres:16-alpine` | 5433 | Se carga con `demo/cliente_demo.sql` al crearse | — |

Decisiones del diseño Docker:

- **`app` espera a que `db` esté sana** (`depends_on: condition: service_healthy`): K-Secure no arranca sin su base.
- **Usuario sin privilegios** dentro del contenedor: si alguien vulnerara la app, no tendría permisos de root.
- **Dependencias en una capa propia**: `requirements.txt` se instala antes de copiar el código, así Docker reutiliza esa
  capa mientras no cambien las dependencias.
- **Configuración por variables de entorno** (`.env`, que no se sube; ver `.env.example`): la misma imagen sirve para
  cualquier servidor.
- **`.dockerignore`** deja fuera las pruebas, la documentación, el entorno virtual y cualquier `.env`.
- **Base del cliente en un perfil aparte** (`--profile demo`): no se levanta en producción.

Cómo levantarlo: sección *Ejecución local* del [README](../README.md) y sección 3 del
[manual técnico](Manual_Tecnico.md). Se probó el 05/11/2026 en Docker Desktop: los tres contenedores levantaron, `app` y
`db` quedaron *healthy* y `/api/health` respondió `{"status":"ok"}`.

---

## 7. Seguridad por diseño

| Riesgo | Cómo lo resuelve el diseño |
|---|---|
| Ver datos sensibles en pantalla | Todo se muestra **enmascarado** (`**.***.198-5`) |
| Robo de la base interna | Los originales se guardan **cifrados**: una llave AES por escaneo, protegida con RSA-2048; la llave privada solo se abre con la clave de auditor |
| Acceso no autorizado | Login sin registro público, roles Admin / Auditor / Visor, bloqueo tras 5 intentos, sesiones que vencen |
| Modificar la base del cliente | Conexión de **solo lectura** (sección 3) |
| Trazabilidad | **Bitácora** de solo agregar filas: quién escaneó, quién vio un original, quién cambió reglas o cuentas |
| Fórmulas maliciosas al exportar | El CSV neutraliza celdas que empiezan con `=`, `+`, `-` o `@` |

---

## 8. Decisiones técnicas

| N.º | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| DT-01 | **Python 3.13 + FastAPI** | Django, Flask | FastAPI valida los datos con Pydantic y genera la documentación de la API sola (`/docs`); Python tiene las librerías de lectura de documentos y de cifrado que el proyecto necesita |
| DT-02 | **Diseño de ferret-scan** (preprocesadores + validadores con confianza 0–100) | Diseño propio desde cero | Lo pidió el docente; es un diseño probado de AWS Labs. Se replicó el diseño, no el código (ferret-scan está en Go) |
| DT-03 | **Aplicación web** | Programa de escritorio `.exe` | Con un `.exe`, una empresa con 1.000 computadores tendría que actualizar los 1.000; la web se actualiza en un solo lugar |
| DT-04 | **SQLAlchemy con SQLite o PostgreSQL** | Solo PostgreSQL | El mismo código corre en un notebook sin instalar nada (SQLite) y en producción (PostgreSQL) |
| DT-05 | **Frontend sin frameworks** (HTML, CSS y JS con módulos ES) | React, Vue | No necesita compilación ni Node.js; el servidor entrega archivos estáticos y el equipo lo mantiene sin aprender otra herramienta |
| DT-06 | **Cifrado híbrido RSA-2048 + AES** con clave de auditor | Guardar el original en claro; cifrar todo con una sola llave | Ni quien administra el servidor puede ver los originales sin la clave de auditor; cada escaneo tiene su propia llave |
| DT-07 | **bcrypt** para contraseñas y códigos; **SHA-256** para tokens de sesión | Guardar contraseñas reversibles | Un robo de la base no expone contraseñas ni sesiones utilizables |
| DT-08 | **Sesiones guardadas en la base de datos** | Sesiones en memoria del servidor | Permite reiniciar la app sin cerrar sesiones y correr varias instancias contra la misma base (ver escalabilidad en [RNF](Requisitos_No_Funcionales.md)) |
| DT-09 | **Solo lectura en las bases del cliente** | Permisos de escritura | K-Secure informa, no modifica: baja la barrera para que el área de TI del cliente lo autorice |
| DT-10 | **Render + Neon** (planes gratuitos, AWS us-east-2) | Servidor propio, AWS pagado | Costo cero y despliegue automático desde GitHub; app y base en la misma región |
| DT-11 | **Correos por Apps Script de Gmail** | SMTP directo | El plan gratis de Render bloquea SMTP |
| DT-12 | **Docker Compose** para servidor propio | Instalar a mano | No depende del sistema operativo; app y base levantan con un comando |
| DT-13 | **Reglas nuevas desde ejemplos del dato** | Pedir expresiones regulares | Cualquier analista puede crear un detector sin saber programar |

Las decisiones de alcance del proyecto (construir solo la capa de clasificación, rehacer el sistema desde cero, login
sin registro público, cliente simulado) están en el
[documento de inicio](00_Documento_Inicio_Proyecto.md#10-registro-de-decisiones-del-proyecto).

---

## 9. Limitaciones conocidas del diseño

| Limitación | Efecto | Plan |
|---|---|---|
| El escaneo de **archivos subidos** corre en el hilo principal del servidor | Mientras dura un escaneo grande, las demás peticiones esperan | Moverlo a un hilo aparte o a escaneos en segundo plano (el de bases de datos ya corre en un hilo aparte) |
| Memoria al escanear archivos grandes (~2,2 GB para 100.000 filas) | Supera los 512 MB del plan gratis de Render | HU-29 (procesar por lotes) |
