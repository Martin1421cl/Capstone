# Manual técnico — K-Secure

Guía de instalación, configuración, despliegue y operación de K-Secure.
Está dirigido al equipo de TI que instala la herramienta. El uso diario (escanear y revisar resultados) se hace
desde la web y no requiere este manual.

**Versión:** 1.0 · 31/10/2026

---

## Índice

1. [Requisitos](#1-requisitos)
2. [Opción A: instalación local](#2-opción-a-instalación-local)
3. [Opción B: Docker](#3-opción-b-docker)
4. [Opción C: nube (Render + Neon)](#4-opción-c-nube-render--neon)
5. [Variables de entorno](#5-variables-de-entorno)
6. [Primer uso](#6-primer-uso)
7. [Correo para recuperar contraseñas](#7-correo-para-recuperar-contraseñas)
8. [Escanear la base de un cliente](#8-escanear-la-base-de-un-cliente)
9. [Respaldo y restauración](#9-respaldo-y-restauración)
10. [Actualizar K-Secure](#10-actualizar-k-secure)
11. [Pruebas](#11-pruebas)
12. [Solución de problemas](#12-solución-de-problemas)

---

## 1. Requisitos

| Opción | Requisitos |
|---|---|
| Local | Python 3.11 o superior (recomendado 3.13), Git, 500 MB libres |
| Docker | Docker Desktop (Windows/Mac) o Docker Engine + Compose (Linux) |
| Nube | Cuenta gratuita en [Render](https://render.com) y en [Neon](https://neon.tech) y acceso al repositorio en GitHub |

Navegadores soportados: Chrome, Edge, Firefox y Safari en versiones actuales.

Puertos: **8000** (K-Secure). Con Docker también **5433** (base del cliente ficticio).

---

## 2. Opción A: instalación local

Ideal para desarrollar o para una demo en un notebook. Usa SQLite como base interna, sin instalar nada más.

```bash
git clone https://github.com/Martin1421cl/Capstone.git
cd Capstone/k-secure-web

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / Mac
source .venv/bin/activate

pip install -r requirements.txt
uvicorn ksecure.web.app:app
```

Abrir http://localhost:8000. La base interna queda en `k-secure-web/data/ksecure.db`.

Para que otros equipos de la red local entren: `uvicorn ksecure.web.app:app --host 0.0.0.0 --port 8000`
y abrir `http://<IP-del-PC>:8000`.

---

## 3. Opción B: Docker

Levanta K-Secure con **PostgreSQL** como base interna. Recomendado para instalarlo en un servidor de la empresa.

```bash
cd Capstone/k-secure-web
cp .env.example .env          # Windows: copy .env.example .env
```

Editar `.env` y cambiar **todas** las contraseñas (`KSECURE_ACCESO`, `POSTGRES_PASSWORD`, `CLIENTE_DB_PASSWORD`).
Luego:

```bash
docker compose up -d --build              # K-Secure + PostgreSQL
docker compose --profile demo up -d       # además, la base del cliente ficticio
```

| Comando | Para qué |
|---|---|
| `docker compose ps` | Ver si los contenedores están arriba y sanos (`healthy`) |
| `docker compose logs -f app` | Ver los registros de K-Secure (aquí aparece el código de recuperación si no hay correo configurado) |
| `docker compose down` | Detener (los datos se conservan en el volumen `ksecure-datos`) |
| `docker compose down -v` | Detener y **borrar** la base interna |

Contenedores:

| Contenedor | Imagen | Función |
|---|---|---|
| `ksecure-app` | construida desde `Dockerfile` (python:3.13-slim) | La aplicación, con usuario sin privilegios y *healthcheck* en `/api/health` |
| `ksecure-db` | postgres:16-alpine | Base interna, con volumen persistente |
| `ksecure-cliente-demo` | postgres:16-alpine | Base de una empresa ficticia (solo con `--profile demo`) |

---

## 4. Opción C: nube (Render + Neon)

Es la forma en que se entrega al cliente: **no instala nada**, solo entra a una URL.

1. **Neon:** crear un proyecto en la región *AWS US East 2 (Ohio)* y copiar la *connection string* (`postgresql://...`).
2. **Render:** *New → Blueprint* → elegir el repositorio Capstone. Render lee `render.yaml` (en la raíz del
   repositorio) y pide dos variables:
   - `KSECURE_DB_URL`: la connection string de Neon.
   - `KSECURE_ACCESO`: `usuario:contraseña` del primer administrador.
3. Esperar el despliegue y abrir la URL que entrega Render.
4. Cada `git push` a `main` vuelve a desplegar automáticamente.

> El plan gratis de Render "duerme" la app tras 15 minutos sin uso: la primera visita tarda cerca de 1 minuto.

---

## 5. Variables de entorno

Todas son opcionales en un PC local. Ver `k-secure-web/.env.example`.

| Variable | Ejemplo | Para qué |
|---|---|---|
| `KSECURE_DB_URL` | `postgresql://user:clave@host/ksecure?sslmode=require` | Base interna. Sin ella se usa SQLite en `data/` |
| `KSECURE_ACCESO` | `K-SECURE:una-clave-larga` | Crea el primer administrador al arrancar, solo si la base no tiene cuentas |
| `KSECURE_CORREO_URL` | `https://script.google.com/macros/s/.../exec` | Envío de correos para recuperar contraseñas |
| `KSECURE_CORREO_SECRETO` | valor al azar | Secreto compartido con el Apps Script |

> Nunca subir el archivo `.env` al repositorio. Está incluido en `.gitignore`.

---

## 6. Primer uso

1. Entrar con la cuenta de administrador (la de `KSECURE_ACCESO`, o crearla en la primera visita en un PC local).
2. Cambiar la contraseña temporal y registrar un correo.
3. En **Usuarios**, crear la **clave de auditor** (mínimo de largo indicado en pantalla).
   **Guardarla en un lugar seguro: si se pierde, los originales cifrados no se pueden recuperar.**
4. Crear las cuentas del equipo con su rol:

| Rol | Puede |
|---|---|
| Visor | Ver resultados enmascarados y exportarlos |
| Auditor | Además, escanear, revisar hallazgos, borrar escaneos y ver originales con la clave de auditor |
| Admin | Además, administrar cuentas, reglas, la clave de auditor y ver la bitácora |

---

## 7. Correo para recuperar contraseñas

Render (plan gratis) bloquea SMTP, así que los correos salen por un Apps Script de Gmail:

1. En https://script.google.com, crear un proyecto y pegar `k-secure-web/docs/apps-script-correo.gs`.
2. *Configuración del proyecto → Propiedades del script*: agregar `SECRETO` con una clave larga al azar.
3. Ejecutar la función `probar` una vez (pide permisos).
4. *Implementar → Nueva implementación → Aplicación web*, ejecutar como **Yo**, acceso **Cualquier usuario**.
5. Copiar la URL `/exec` en `KSECURE_CORREO_URL` y el secreto en `KSECURE_CORREO_SECRETO`.
6. En K-Secure → **Usuarios → Enviar correo de prueba**.

Sin estas variables, el código de recuperación aparece en la consola (o en `docker compose logs app`).

**Si nadie puede entrar como administrador:**

```bash
python -m ksecure.restablecer                          # lista las cuentas
python -m ksecure.restablecer admin                    # contraseña temporal para "admin"
python -m ksecure.restablecer admin --url "postgresql://..."   # en la base de la nube
# Con Docker:
docker compose exec app python -m ksecure.restablecer admin
```

---

## 8. Escanear la base de un cliente

K-Secure se conecta en **solo lectura** (solo ejecuta `SELECT`) y no guarda las credenciales.

**Recomendación de seguridad:** crear en la base del cliente un usuario exclusivo para K-Secure, solo con permiso
de lectura. Ejemplo en PostgreSQL:

```sql
CREATE USER ksecure_lector WITH PASSWORD 'una-clave-larga';
GRANT CONNECT ON DATABASE empresa TO ksecure_lector;
GRANT USAGE ON SCHEMA public TO ksecure_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ksecure_lector;
```

En K-Secure: **Base de datos** → motor → servidor, puerto, base, usuario y contraseña → **Probar conexión** →
elegir tablas y límite de filas → **Escanear**.

| Motor | Puerto por defecto | Driver |
|---|---|---|
| PostgreSQL | 5432 | psycopg 3 |
| MySQL / MariaDB | 3306 | PyMySQL |
| SQL Server | 1433 | pymssql |
| Oracle | 1521 | oracledb (modo *thin*, sin cliente Oracle) |

**Base de demostración:** con Docker (`--profile demo`) usar servidor `cliente-demo`, puerto `5432`, base
`cliente_demo` y las credenciales `CLIENTE_DB_*` del `.env`. En Neon: crear la base `cliente_demo`, abrir el
*SQL Editor* y ejecutar `demo/cliente_demo.sql`.

---

## 9. Respaldo y restauración

Lo único que hay que respaldar es la **base interna** y la **clave de auditor** (esta última fuera del sistema).

```bash
# PostgreSQL (Docker)
docker compose exec db pg_dump -U ksecure ksecure > respaldo_ksecure.sql
docker compose exec -T db psql -U ksecure ksecure < respaldo_ksecure.sql

# PostgreSQL (Neon)
pg_dump "postgresql://..." > respaldo_ksecure.sql

# SQLite (local)
copiar el archivo k-secure-web/data/ksecure.db
```

---

## 10. Actualizar K-Secure

```bash
git pull
# Local
pip install -r requirements.txt
# Docker
docker compose up -d --build
```

Las columnas nuevas de la base interna se agregan solas al arrancar; no hay que migrar a mano.

---

## 11. Pruebas

```bash
cd k-secure-web
pytest -v
```

Detalle de los tipos de prueba y casos: [`Plan_de_Pruebas.md`](Plan_de_Pruebas.md).

---

## 12. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError` al iniciar | Dependencias sin instalar o entorno virtual sin activar | Activar `.venv` y `pip install -r requirements.txt` |
| "Primero crea la clave de auditor" al escanear | No hay clave de auditor | Crearla en **Usuarios** (rol Admin) |
| La primera visita en Render tarda ~1 minuto | El plan gratis "duerme" la app | Es normal; las visitas siguientes son rápidas |
| Errores al azar con Neon (*prepared statement*) | Agrupador de conexiones de Neon | Ya resuelto en `db.py`; usar la URL tal como la entrega Neon |
| No llega el correo de recuperación | Variables de correo sin configurar o Apps Script sin publicar | Revisar la sección 7; mientras, el código sale en la consola |
| "Cuenta bloqueada" | 5 contraseñas incorrectas | Esperar 5 minutos o usar `python -m ksecure.restablecer` |
| No conecta a la base del cliente | Firewall, puerto o credenciales | Probar con `psql`/cliente del motor desde el mismo servidor; revisar que el puerto esté abierto |
| `docker compose up` falla con "variable is not set" | Falta el archivo `.env` | `cp .env.example .env` |
| Se perdió la clave de auditor | — | Los originales de escaneos anteriores no se pueden recuperar (es intencional). Respaldar la base y volver a escanear |
