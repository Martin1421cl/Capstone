# Requisitos no funcionales e infraestructura — K-Secure

Complementa la sección de requisitos no funcionales (RNF-01 a RNF-12) de
`03 - Especificación de Requerimientos de Software (ERS).docx` con los requisitos de **infraestructura**:
qué servidor se necesita, qué hay que instalar y con qué se desarrolló.

**Versión:** 1.0 · 31/10/2026 · Las cifras de memoria y tiempo se midieron en el entorno de desarrollo.

---

## 1. Requisitos de servidor

K-Secure **no usa GPU ni modelos de inteligencia artificial**: la detección se hace con expresiones regulares,
validaciones matemáticas (Módulo 11 para el RUT, Luhn para tarjetas) y análisis de palabras de contexto. Por eso
corre en servidores modestos. Lo que más pesa es la **memoria al escanear archivos grandes**.

| Recurso | Mínimo (demo y archivos pequeños) | Recomendado (uso en empresa) |
|---|---|---|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 4 GB |
| Disco | 2 GB (app + dependencias + base SQLite) | 20 GB (base interna con historial de escaneos) |
| GPU | No requiere | No requiere |
| Sistema operativo | Cualquiera con Python 3.11+ o Docker (Linux, Windows, macOS) | Linux con Docker |
| Red | Puerto 8000 (o 443 detrás de un proxy HTTPS) | HTTPS obligatorio en producción |

### Consumo medido al escanear un CSV subido por la web

| Tamaño del archivo | Filas | Tiempo | Memoria máxima del proceso | Base interna después |
|---|---|---|---|---|
| — (app en reposo) | — | — | ~95 MB | — |
| 0,2 MB | 2.000 | ~1 s | — | — |
| 1,0 MB | 10.000 | ~8 s | ~300 MB | — |
| 5,4 MB | 50.000 | ~41 s | ~1,1 GB | — |
| 10,7 MB | 100.000 | ~78 s | ~2,2 GB | ~130 MB acumulado* |

\* Cada hallazgo guarda su valor enmascarado y cifrado; 100.000 filas con 3 datos sensibles cada una generan
~300.000 hallazgos.

Para tablas de bases de datos (escaneo por columnas con límite de filas), la ERS registra 100.000 filas en 32 s (RNF-06).

> **Limitación conocida (D-03):** el plan gratis de Render tiene **512 MB de RAM**, suficiente para la demo y para
> archivos de hasta ~10.000 filas. Para archivos más grandes se debe usar un plan con más memoria o la instalación con
> Docker en un servidor propio. Optimizar la memoria del escaneo de archivos grandes está en el backlog (HU-29).

---

## 2. Software que hay que instalar

### Opción Docker (recomendada)

| Software | Versión |
|---|---|
| Docker Engine / Docker Desktop | 24 o superior |
| Docker Compose | v2 |

Las imágenes ya traen todo lo demás: `python:3.13-slim` y `postgres:16-alpine`.

### Opción sin Docker

| Software | Versión | Para qué |
|---|---|---|
| Python | 3.11 o superior (desarrollado con 3.13) | Ejecutar K-Secure |
| pip | incluido con Python | Instalar dependencias (`requirements.txt`) |
| Git | cualquiera reciente | Descargar el repositorio |
| PostgreSQL | 14 o superior (opcional) | Base interna en producción; sin él se usa SQLite |

No requiere clientes de base de datos instalados: los drivers de PostgreSQL, MySQL, SQL Server y Oracle se instalan
con `pip` (Oracle en modo *thin*, sin Oracle Client).

### Dependencias de Python (`k-secure-web/requirements.txt`)

| Paquete | Uso |
|---|---|
| fastapi, uvicorn, python-multipart | API REST y servidor web |
| sqlalchemy | Base interna (SQLite / PostgreSQL) |
| cryptography | Cifrado RSA-2048 + AES (bóveda) |
| bcrypt | Hash de contraseñas |
| pypdf, xlrd | Lectura de PDF y Excel antiguo |
| reportlab | Reporte PDF |
| psycopg, pymysql, pymssql, oracledb | Conexión a las bases del cliente |
| pytest, httpx | Pruebas automáticas |

---

## 3. Entorno de desarrollo

| Elemento | Herramienta |
|---|---|
| Lenguaje | Python 3.13 |
| Framework web | FastAPI |
| Frontend | HTML, CSS y JavaScript sin frameworks |
| Control de versiones | Git + GitHub (`Martin1421cl/Capstone`) |
| Pruebas | pytest (235 pruebas automáticas) |
| Base de datos de pruebas | SQLite en memoria; PostgreSQL en Neon y en Docker para la demo |
| Despliegue | Render (app) + Neon (PostgreSQL), región AWS us-east-2; Docker Compose para servidor propio |
| Diagramas | Mermaid (en el repositorio) |

---

## 4. Navegadores (cliente)

Chrome, Edge, Firefox y Safari en versiones actuales. No se instala nada en el equipo del usuario.

---

## 5. Requisitos no funcionales por atributo de calidad

Resumen de los RNF de la ERS más los de infraestructura de este documento.

| ID | Atributo | Requisito | Cómo se verifica | Estado |
|---|---|---|---|---|
| RNF-01 | Seguridad | Solo lectura en las bases del cliente | Prueba `test_base_del_cliente_se_abre_en_solo_lectura` | ✅ |
| RNF-02 | Seguridad | El dato original nunca se guarda en claro (enmascarado + cifrado RSA/AES) | Revisión de la base interna y pruebas de integración | ✅ |
| RNF-03 | Seguridad | Las credenciales de la base del cliente no se guardan | Revisión de la base interna | ✅ |
| RNF-04 | Seguridad | Archivos de máximo 100 MB; el nombre no decide la ruta en disco | Pruebas de seguridad | ✅ |
| RNF-05 | Rendimiento | 1.000 filas de una tabla en 1 s o menos | Medido: 0,3 s | ✅ |
| RNF-06 | Rendimiento | 100.000 filas de una tabla en 60 s o menos | Medido: 32 s | ✅ |
| RNF-07 | Exactitud | Todas las columnas sensibles de la base demo, sin falsos positivos | 9 de 9, 0 falsos positivos | ✅ |
| RNF-08 | Determinismo | Mismo escaneo, mismo resultado | Falta `ORDER BY` (HU-27) | ⏳ |
| RNF-09 | Usabilidad | Interfaz en español; reglas sin expresiones regulares | Prueba con usuario | ✅ |
| RNF-10 | Portabilidad | Corre en cualquier sistema con Python 3.11+ o Docker | Render, Docker y local | ✅ |
| RNF-11 | Mantenibilidad | Pruebas automáticas que cubren el sistema | 235 pruebas, todas pasan | ✅ |
| RNF-12 | Seguridad | Contraseñas con bcrypt y sesiones que expiran | 30 min de inactividad, 12 h máximo | ✅ |
| RNF-13 | Capacidad | Servidor mínimo 1 vCPU / 1 GB RAM; recomendado 2 vCPU / 4 GB | Medición de memoria (sección 1) | ✅ |
| RNF-14 | Capacidad | Escanear un archivo de 100.000 filas sin superar 1 GB de RAM | Medido: ~2,2 GB (D-03) | ⏳ |
| RNF-15 | Disponibilidad | La app informa su estado en `/api/health` (healthcheck de Docker y Render) | `docker compose ps` muestra `healthy` | ✅ |
| RNF-16 | Seguridad | En producción, acceso solo por HTTPS; cookie de sesión `HttpOnly` y `Secure` | Render entrega HTTPS; revisión de `web/sesion.py` | ✅ |
