# Requisitos no funcionales e infraestructura — K-Secure

Complementa la sección de requisitos no funcionales (RNF-01 a RNF-12) de
`03 - Especificación de Requerimientos de Software (ERS).docx` con los requisitos de **infraestructura**:
qué servidor se necesita, qué hay que instalar y con qué se desarrolló.

**Versión:** 1.2 · 18/11/2026 (HU-29: memoria por lotes, RNF-14 y RNF-18 cumplidos; antes 1.1 · 16/11/2026, sección 6) · Las cifras de memoria y tiempo se midieron en el entorno de desarrollo.

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

Medido el 18/11/2026 en el mismo equipo, antes y después de HU-29 (guardar los hallazgos por lotes):

| Tamaño del archivo | Filas | Tiempo antes → ahora | Memoria máxima antes → ahora | Base interna después |
|---|---|---|---|---|
| — (app en reposo) | — | — | ~85–95 MB | — |
| 0,2 MB | 2.000 | ~1 s | — | — |
| 1,0 MB | 10.000 | ~5 s → **~3 s** | ~300 MB → **~120 MB** | — |
| 5,4 MB | 50.000 | ~24 s → **~14 s** | ~1,1 GB → **~185 MB** | — |
| 10,7 MB | 100.000 | ~52 s → **~28 s** | ~2,1 GB → **~265 MB** | ~130 MB acumulado* |

\* Cada hallazgo guarda su valor enmascarado y cifrado; 100.000 filas con 3 datos sensibles cada una generan
~300.000 hallazgos. En la primera medición (31/10, otro PC) el CSV de 100.000 filas tardó ~78 s con ~2,2 GB.

Qué cambió (HU-29): antes se juntaban los 300.000 hallazgos en memoria y se guardaban al final como objetos del ORM;
ahora se guardan en la base de a 2.000 mientras se escanea, y el archivo subido se copia al disco de a 1 MB.

Para tablas de bases de datos (escaneo por columnas con límite de filas), la ERS registra 100.000 filas en 32 s (RNF-06).

> **D-03 resuelto (HU-29):** el plan gratis de Render tiene **512 MB de RAM**. Antes alcanzaba para archivos de hasta
> ~10.000 filas; ahora un CSV de 100.000 filas usa ~265 MB, así que cabe con margen.

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
| Pruebas | pytest (257 pruebas automáticas) |
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
| RNF-08 | Determinismo | Mismo escaneo, mismo resultado | `ORDER BY` por llave primaria al leer tablas (HU-27) | ✅ |
| RNF-09 | Usabilidad | Interfaz en español; reglas sin expresiones regulares | Prueba con usuario | ✅ |
| RNF-10 | Portabilidad | Corre en cualquier sistema con Python 3.11+ o Docker | Render, Docker y local | ✅ |
| RNF-11 | Mantenibilidad | Pruebas automáticas que cubren el sistema | 257 pruebas, todas pasan | ✅ |
| RNF-12 | Seguridad | Contraseñas con bcrypt y sesiones que expiran | 30 min de inactividad, 12 h máximo | ✅ |
| RNF-13 | Capacidad | Servidor mínimo 1 vCPU / 1 GB RAM; recomendado 2 vCPU / 4 GB | Medición de memoria (sección 1) | ✅ |
| RNF-14 | Capacidad | Escanear un archivo de 100.000 filas sin superar 1 GB de RAM | Medido: ~265 MB (HU-29, sección 1) | ✅ |
| RNF-15 | Disponibilidad | La app informa su estado en `/api/health` (healthcheck de Docker y Render) | `docker compose ps` muestra `healthy` | ✅ |
| RNF-16 | Seguridad | En producción, acceso solo por HTTPS; cookie de sesión `HttpOnly` y `Secure` | Render entrega HTTPS; revisión de `web/sesion.py` | ✅ |
| RNF-17 | Escalabilidad | La app no guarda estado en memoria: puede correr en varias instancias contra la misma base PostgreSQL | Revisión del diseño (sección 6) | ✅ |
| RNF-18 | Escalabilidad | Un escaneo largo no debe bloquear al resto de los usuarios | El escaneo de archivos subidos corre en un hilo aparte; prueba automática `tests/test_concurrencia.py` | ✅ |

---

## 6. Escalabilidad

Cómo crece K-Secure cuando aumentan los usuarios, los escaneos o el tamaño de los datos.

### Lo que el diseño ya permite

| Aspecto | Diseño actual | Qué permite |
|---|---|---|
| **Estado de la aplicación** | Sesiones, cuentas, reglas, llaves de la bóveda y bitácora se guardan en la base de datos, no en la memoria del servidor | Correr **varias instancias** de la app detrás de un balanceador de carga, todas contra la misma base PostgreSQL, y reiniciar la app sin cerrar sesiones |
| **Base de datos** | PostgreSQL (Neon en la nube o el contenedor `db` en Docker), con índices en `hallazgos.tipo`, `hallazgos.riesgo`, `hallazgos.revision` y `bitacora.fecha` | Filtros rápidos con miles de hallazgos; Neon permite subir de plan sin cambiar código |
| **Tamaño de cada escaneo** | Límite de 100 MB por archivo y de 1.000, 10.000 o 100.000 filas por tabla | Un escaneo no puede consumir recursos sin límite |
| **Nuevos tipos de dato** | Cada tipo es un validador independiente; las reglas se crean desde la pantalla | Crecer en cobertura sin tocar el motor |
| **Despliegue** | Imagen Docker configurada por variables de entorno | Levantar más instancias en cualquier servidor u orquestador |
| **Memoria por escaneo** (HU-29) | Los hallazgos se guardan en la base de a 2.000 mientras se escanea | La memoria no crece con la cantidad de hallazgos: ~265 MB para 100.000 filas |
| **Escaneos en hilos aparte** (RNF-18) | Archivos y bases de datos se escanean fuera del hilo que atiende las peticiones; cada lote se confirma por separado | Mientras alguien escanea, los demás usuarios siguen navegando y la base no queda bloqueada |

> Para correr más de una instancia hay que usar **PostgreSQL**: SQLite es un archivo local y no se comparte entre
> servidores.

### Límites actuales

| Límite | Efecto | Cómo se resuelve |
|---|---|---|
| El servidor arranca con **un solo proceso** de Uvicorn. Los escaneos ya corren en hilos aparte (RNF-18), pero el análisis de Python usa un núcleo a la vez | Varios escaneos grandes al mismo tiempo se reparten la misma CPU y tardan más | `uvicorn --workers N` o varias instancias con PostgreSQL. A futuro: escaneos en segundo plano con progreso en pantalla |
| Un escaneo muy largo mantiene abierta la petición del navegador | Si se corta la conexión, el escaneo en curso se descarta (no queda a medias: se borra) | Escaneos en segundo plano con una cola de trabajos |
| Plan gratis de Render: 512 MB de RAM y la app "duerme" tras 15 min | Pensado para la demo, no para uso en empresa | Plan pagado o instalación con Docker en un servidor propio |

