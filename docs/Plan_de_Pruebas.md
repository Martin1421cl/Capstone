# Plan de pruebas — K-Secure

**Proyecto:** K-Secure · Capstone PTY4614-003 · Equipo 2
**Versión del documento:** 1.0 · 31/10/2026
**Responsables:** Camilo Fuenzalida, Emanuel Farías, Martín Campos

---

## 1. Objetivo

Verificar que K-Secure **detecta y clasifica correctamente** los datos sensibles chilenos, que **nunca expone un dato
original** sin autorización y que funciona de punta a punta con un rendimiento aceptable, antes de cada entrega y de
la versión final.

## 2. Alcance

| Incluido | Excluido |
|---|---|
| Validadores, preprocesadores y motor de escaneo | Rendimiento del plan gratis de Render (depende del proveedor) |
| API REST, sesión, roles y bitácora | Pruebas de carga con muchos usuarios simultáneos |
| Bóveda de cifrado y enmascarado | Auditoría de seguridad externa (pentest profesional) |
| Escaneo de bases de datos en solo lectura | Navegadores antiguos (Internet Explorer) |
| Exportación CSV, JSON y PDF | |

## 3. Tipos de prueba

| Tipo | Qué verifica | Herramienta | Dónde está | N.º de pruebas |
|---|---|---|---|---|
| **Unitarias** | Cada validador (RUT con Módulo 11, Luhn, teléfonos, patentes...), preprocesadores, reglas, enmascarado | pytest | `tests/test_*.py` | 210 |
| **Integración** | Flujos completos por la API: Admin → Auditor → Visor, escaneo → revisión → exportación, reglas nuevas | pytest + TestClient (httpx) | `tests/integracion/` | 4 |
| **Seguridad** | Control de acceso por rol, fuerza bruta, inyección SQL, inyección de fórmulas CSV, *path traversal*, tamaño de archivos, solo lectura en la base del cliente, fuga de datos | pytest + TestClient | `tests/seguridad/` | 18 |
| **Rendimiento** | Tiempos de escaneo con volúmenes realistas | pytest + `time.perf_counter` | `tests/rendimiento/` | 3 |
| **Aceptación (manual)** | El usuario cumple sus tareas en la web | Navegador + casos PR-24 a PR-26 | Este documento | 3 |
| **Total automatizadas** | | | | **235** |

Las pruebas de seguridad se basan en el **OWASP Top 10**: A01 control de acceso roto, A03 inyección,
A07 fallas de autenticación y A09 fallas de registro y monitoreo.

## 4. Entorno de pruebas

| Elemento | Detalle |
|---|---|
| Sistema | Windows 11 / Linux, Python 3.13 |
| Base interna | SQLite en memoria (`sqlite://`), creada desde cero en cada prueba |
| Bases del cliente | SQLite generado en la prueba y base demo `cliente_demo.sql` en PostgreSQL (Neon o Docker) |
| Datos | **Sintéticos**: RUT generados con Módulo 11, tarjetas de prueba, datos de `Faker`. Nunca datos reales |
| Correo | Desactivado en las pruebas (no se envían correos de verdad) |

## 5. Cómo ejecutar

```bash
cd k-secure-web
pip install -r requirements.txt

pytest -v                       # todas
pytest tests/integracion -v     # integración
pytest tests/seguridad -v       # seguridad
pytest tests/rendimiento -v -s  # rendimiento (muestra los tiempos)
```

En un PC lento, los umbrales de rendimiento se pueden relajar con `KSECURE_FACTOR_TIEMPO=2`.

## 6. Casos de prueba

> Los IDs **PR-xx** son de este plan. Los casos **CP-xx** que cita la ERS se mantienen en ese documento.

### 6.1 Funcionales

| ID | Caso | Requisito | Pasos | Resultado esperado | Tipo | Estado |
|---|---|---|---|---|---|---|
| PR-01 | RUT válido con puntos y contexto | RF-04 | Escanear "RUT del trabajador: 15.432.198-5" | 1 hallazgo RUT, confianza HIGH, riesgo Restringido | Automática | ✅ |
| PR-02 | RUT con dígito verificador incorrecto | RF-04 | Escanear un RUT con DV inválido | Hallazgo con confianza LOW (posible error de tipeo) | Automática | ✅ |
| PR-03 | Archivo no soportado junto a uno válido | RF-01 | Subir un `.bin` y un `.csv` en el mismo escaneo | Error claro para el `.bin`; el `.csv` se escanea | Automática | ✅ |
| PR-04 | Planilla por columnas | RF-06 | Subir CSV con columna `rut` | "La columna rut es RUT en el 100 % de las filas" | Automática | ✅ |
| PR-05 | Tarjetas: Luhn, tarjeta de prueba y relleno | RF-04 | Escanear una tarjeta válida, una de prueba de Transbank y un número de relleno | La válida se detecta con su marca; la de prueba queda LOW; el relleno solo se reporta con contexto | Automática | ✅ |
| PR-06 | Regla creada desde ejemplos | RF-10 | Crear regla con "FC-123456" y escanear "FC-777888" | Se detecta como FICHA_CLINICA | Integración | ✅ |
| PR-07 | Exportar sin falsos positivos | RF-15, RF-16 | Marcar un falso positivo y exportar confirmados | El archivo no trae el falso positivo ni originales | Integración | ✅ |
| PR-08 | Borrar escaneo | RF-09 | Borrar un escaneo | Sus hallazgos desaparecen (cascada) | Integración | ✅ |
| PR-09 | Recuperar contraseña | RF-14 | Pedir código y usarlo | Cambia la contraseña; el código vence a los 10 min | Automática | ✅ |
| PR-10 | Mismo escaneo dos veces | RNF-08 | Escanear dos veces una tabla mayor al límite | Mismo resultado | Manual | ⏳ (falta `ORDER BY`) |

### 6.2 Seguridad

| ID | Caso | Requisito / OWASP | Resultado esperado | Estado |
|---|---|---|---|---|
| PR-11 | Endpoints sin sesión | RF-13 · A01 | 401 en todos los endpoints de datos | ✅ |
| PR-12 | Visor intenta crear cuentas, escanear o revelar | RF-13 · A01 | 403 | ✅ |
| PR-13 | 5 contraseñas incorrectas | RNF-12 · A07 | Cuenta bloqueada 5 min, aunque luego se use la correcta | ✅ |
| PR-14 | Escribir en la base del cliente | RNF-01 | `INSERT` y `DROP` fallan; la base queda igual | ✅ |
| PR-15 | Inyección SQL en el login (`' OR '1'='1`) | A03 | No ingresa; la tabla de usuarios sigue intacta | ✅ |
| PR-16 | Archivo con nombre `../../etc/passwd.txt` | RNF-04 | Se escanea el contenido subido; no se toca el disco del servidor | ✅ |
| PR-16b | Archivo sobre el límite de 100 MB | RNF-04 | Rechazado con 413 | ✅ |
| PR-17 | Valor que empieza con `=` al exportar CSV | A03 | La celda no llega como fórmula a Excel | ✅ |
| PR-18 | 5 claves de auditor incorrectas | RF-08 · A07 | Bloqueo de 1 minuto y alerta en la bitácora | ✅ |
| PR-19 | Revisar la API de usuarios y la bitácora | RNF-02 · A09 | Sin hashes, contraseñas ni datos originales | ✅ |

### 6.3 Rendimiento

| ID | Caso | Requisito | Meta | Medido* | Estado |
|---|---|---|---|---|---|
| PR-20 | CSV de 2.000 filas (12.000 celdas) por la API | RNF-05 | < 30 s | 1,1 s (≈ 1.800 filas/s) | ✅ |
| PR-21 | Texto de 1,4 MB sin datos sensibles | — | < 15 s y 0 falsos positivos | 0,2 s, 0 hallazgos | ✅ |
| PR-22 | 5.000 RUT con el validador | RNF-05 | < 10 s | 0,4 s | ✅ |
| PR-23 | Tabla de 100.000 filas | RNF-06 | ≤ 60 s | 32 s (ERS) | ✅ |

\* Medido el 31/10/2026 en el entorno de desarrollo.

### 6.4 Aceptación (manual, con un usuario)

| ID | Tarea para el usuario | Resultado esperado | Estado |
|---|---|---|---|
| PR-24 | Primer ingreso como Admin: crear clave de auditor y una cuenta Auditor | Lo logra sin ayuda en menos de 5 minutos | ⏳ |
| PR-25 | Como Auditor, escanear la base demo en Neon | Identifica las 9 columnas sensibles | ⏳ |
| PR-26 | Crear una regla para "N° de socio" solo con ejemplos | La regla funciona sin escribir expresiones regulares | ⏳ |

## 7. Criterios de aceptación de la versión

- El **100 %** de las pruebas automáticas pasan.
- **0** datos originales expuestos en respuestas de la API, exportaciones o bitácora.
- Todos los casos de seguridad (PR-11 a PR-19) aprobados.
- Casos de aceptación PR-24 a PR-26 aprobados con al menos un usuario externo al equipo.

## 8. Registro de defectos

| ID | Encontrado en | Descripción | Severidad | Estado |
|---|---|---|---|---|
| D-01 | RNF-08 | Una tabla mayor al límite de filas puede devolver filas distintas en cada escaneo (falta `ORDER BY`) | Media | Abierto (sprint 7) |
| D-02 | Pruebas | `test_bd_servidor_inalcanzable_da_error_claro` falla si no está instalado `psycopg` | Baja | Se resuelve con `pip install -r requirements.txt` |
| D-03 | Medición de capacidad | Un CSV de 100.000 filas usa ~2,2 GB de RAM al escanearse; supera los 512 MB del plan gratis de Render (ver [Requisitos no funcionales](Requisitos_No_Funcionales.md)) | Alta en la nube, baja con Docker | Abierto (HU-29, sprint 7) |
