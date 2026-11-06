# Matriz de trazabilidad — K-Secure

Relaciona cada **requisito** de la ERS con su **caso de uso**, su **historia de usuario**, el **código** que lo
implementa y las **pruebas** que lo verifican. Sirve para comprobar que todo lo comprometido está construido y probado,
y para saber qué revisar si un requisito cambia.

Fuentes: `03 - Especificación de Requerimientos de Software (ERS).docx`, `04 - Especificación de Casos de Uso.docx`,
[Product Backlog](agil/02_Product_Backlog.md), código en `k-secure-web/ksecure/` y pruebas en `k-secure-web/tests/`.

**Estado:** ✅ implementado y probado · 🔄 en curso · ⏳ pendiente

---

## 1. Requisitos funcionales

| Req. | Requisito | CU | HU | Código | Pruebas | Estado |
|---|---|---|---|---|---|---|
| RF-01 | Escanear archivos subidos (Office, PDF, CSV, TXT, SQLite), varios a la vez, hasta 100 MB | CU-01 | HU-06 | `escaneo/archivos.py`, `preprocessors/`, `web/api/escanear.py` | `test_preprocesadores.py`, `test_web.py`, `seguridad/test_seguridad_api.py` | ✅ |
| RF-02 | Conectarse a PostgreSQL, MySQL, SQL Server u Oracle, probar la conexión y listar tablas | CU-02 | HU-08 | `escaneo/bases_datos.py`, `web/api/escanear.py` | `test_web.py`, `test_cliente_simulado.py` | ✅ |
| RF-03 | Escanear tablas con límite de 1.000, 10.000 o 100.000 filas | CU-02 | HU-08 | `escaneo/bases_datos.py`, `escaneo/celdas.py` | `test_web.py`, `test_cliente_simulado.py` | ✅ |
| RF-04 | Clasificar con tipo, confianza (HIGH/MEDIUM/LOW) y riesgo | CU-01, CU-02 | HU-01 a HU-04 | `validators/`, `core/models.py` | `test_validadores.py`, `test_rut.py` | ✅ |
| RF-05 | Usar el nombre de la columna y las palabras cercanas como contexto | CU-01, CU-02 | HU-05 | `validators/base.py`, `escaneo/celdas.py` | `test_validadores.py`, `test_rut.py` | ✅ |
| RF-06 | Mostrar totales por riesgo y tipo, columnas sensibles y hallazgos con filtros y orden | CU-03 | HU-07, HU-13 | `almacenamiento/repositorio.py`, `web/api/resultados.py` | `test_web.py` | ✅ |
| RF-07 | Mostrar siempre los valores enmascarados | CU-03 | HU-10 | `validators/*.mask()`, `almacenamiento/repositorio.py` | `test_web.py`, `integracion/test_flujo_completo.py` | ✅ |
| RF-08 | Clave de auditor; revelar originales solo con ella; bloqueo tras 5 intentos | CU-04, CU-05 | HU-11, HU-12 | `almacenamiento/boveda.py`, `web/api/auditor.py` | `test_web.py`, `seguridad/test_seguridad_api.py`, `integracion/test_flujo_completo.py` | ✅ |
| RF-09 | Historial de escaneos y borrado con sus hallazgos | CU-07 | HU-14 | `almacenamiento/repositorio.py`, `web/api/resultados.py` | `test_web.py`, `integracion/test_flujo_completo.py` | ✅ |
| RF-10 | Reglas personalizadas creadas desde ejemplos, probadas en vivo | CU-06 | HU-18 | `validators/patron.py`, `validators/regla.py`, `almacenamiento/reglas.py` | `test_reglas.py`, `integracion/test_flujo_completo.py` | ✅ |
| RF-11 | Apagar validadores incluidos y agregarles palabras de contexto | CU-06 | HU-19 | `almacenamiento/reglas.py`, `web/api/reglas.py` | `test_reglas.py` | ✅ |
| RF-12 | Proteger el acceso a la web con usuario y contraseña | CU-08 | HU-20 | `web/sesion.py`, `almacenamiento/usuarios.py` | `test_sesion.py`, `seguridad/test_seguridad_api.py` | ✅ |
| RF-13 | Cuentas individuales con roles Admin, Auditor y Visor; sin registro público | CU-08, CU-10 | HU-20, HU-21 | `almacenamiento/usuarios.py`, `web/api/usuarios.py`, `web/api/dependencias.py` | `test_sesion.py`, `seguridad/test_seguridad_api.py`, `integracion/test_flujo_completo.py` | ✅ |
| RF-14 | Recuperar la contraseña con un código de 6 dígitos al correo (10 min) | CU-09 | HU-22 | `almacenamiento/usuarios.py`, `correo.py`, `web/api/sesion.py` | `test_recuperar.py` | ✅ |
| RF-15 | Exportar a PDF, CSV y JSON | CU-11 | HU-15 | `exportar.py`, `web/api/resultados.py` | `test_exportar.py`, `integracion/test_flujo_completo.py`, `seguridad/test_seguridad_api.py` | ✅ |
| RF-16 | Confirmar o descartar hallazgos dudosos con un motivo | CU-12 | HU-16 | `almacenamiento/repositorio.py`, `web/api/resultados.py` | `test_revision.py`, `integracion/test_flujo_completo.py` | ✅ |
| RF-17 | Bitácora de quién escaneó, reveló datos o cambió reglas | CU-13 | HU-23 | `almacenamiento/bitacora.py`, `web/api/bitacora.py` | `test_bitacora.py`, `seguridad/test_seguridad_api.py` | ✅ |
| RF-18 | Comparar dos escaneos de la misma fuente | CU-13 | HU-17 | — | — | ⏳ Sprint 7 |

## 2. Requisitos no funcionales

| Req. | Atributo | Requisito | HU | Cómo se verifica | Estado |
|---|---|---|---|---|---|
| RNF-01 | Seguridad | Solo lectura en las bases del cliente | HU-09 | `seguridad/test_seguridad_api.py::test_base_del_cliente_se_abre_en_solo_lectura` | ✅ |
| RNF-02 | Seguridad | El original nunca se guarda en claro | HU-10, HU-11 | `integracion/test_flujo_completo.py`, `test_web.py` | ✅ |
| RNF-03 | Seguridad | Las credenciales del cliente no se guardan | HU-09 | Revisión de `almacenamiento/modelos.py` (no hay tabla de conexiones) | ✅ |
| RNF-04 | Seguridad | Archivos de máximo 100 MB; el nombre no decide la ruta | HU-06 | `seguridad/test_seguridad_api.py` | ✅ |
| RNF-05 | Rendimiento | 1.000 filas de una tabla en ≤ 1 s | — | Medido en la ERS: 0,3 s · `rendimiento/test_rendimiento.py` | ✅ |
| RNF-06 | Rendimiento | 100.000 filas de una tabla en ≤ 60 s | — | Medido en la ERS: 32 s | ✅ |
| RNF-07 | Exactitud | Columnas sensibles de la base demo sin falsos positivos | — | `test_cliente_simulado.py` | ✅ |
| RNF-08 | Determinismo | Mismo escaneo, mismo resultado | HU-27 | Falta `ORDER BY` | ⏳ Sprint 7 |
| RNF-09 | Usabilidad | Interfaz en español; reglas sin expresiones regulares | HU-18 | Prueba con usuario (Plan de pruebas PR-24 a PR-26) | ✅ |
| RNF-10 | Portabilidad | Python 3.11+ en local, nube o Docker | HU-24, HU-25 | Render, Docker Compose y local | ✅ |
| RNF-11 | Mantenibilidad | Pruebas automáticas | HU-26 | 235 pruebas con pytest | ✅ |
| RNF-12 | Seguridad | Contraseñas con bcrypt; sesiones que expiran | HU-20 | `test_sesion.py` | ✅ |
| RNF-13 | Capacidad | Servidor mínimo 1 vCPU / 1 GB; recomendado 2 vCPU / 4 GB | — | [`Requisitos_No_Funcionales.md`](Requisitos_No_Funcionales.md) | ✅ |
| RNF-14 | Capacidad | Archivo de 100.000 filas con menos de 1 GB de RAM | HU-29 | Medido: ~2,2 GB (defecto D-03) | ⏳ Sprint 7 |
| RNF-15 | Disponibilidad | Estado en `/api/health` | HU-25 | `test_web.py::test_paginas_y_health`, healthcheck de Docker | ✅ |
| RNF-16 | Seguridad | HTTPS en producción; cookie `HttpOnly` y `Secure` | HU-20 | Revisión de `web/sesion.py`; Render entrega HTTPS | ✅ |

## 3. Objetivos específicos → requisitos

| Objetivo (Guía 1.5) | Requisitos que lo cumplen |
|---|---|
| OE1 Arquitectura escalable a distintos orígenes de datos | RF-01, RF-02, RNF-10 · [diagramas](diagramas/) |
| OE2 Detección con expresiones regulares y Módulo 11 | RF-04, RF-05, RNF-07 |
| OE3 Reportes por nivel de riesgo | RF-06, RF-15 |
| OE4 Pruebas iterativas con distintos datos | RNF-07, RNF-11 · [Plan de pruebas](Plan_de_Pruebas.md) |
| OE5 Marco de clasificación de datos | RF-04 · [Marco de clasificación](Marco_de_Clasificacion_de_Datos.md) |
| OE6 Flujo integrado de extremo a extremo | RF-01 a RF-09, RF-15 |
| OE7 Planificación y control del avance | [Metodología](agil/00_Metodologia.md), [Sprint Backlog](agil/03_Sprint_Backlog.md) |

## 4. Cobertura

| | Total | ✅ | ⏳ |
|---|---|---|---|
| Requisitos funcionales | 18 | 17 | 1 (RF-18, prioridad baja) |
| Requisitos no funcionales | 16 | 14 | 2 (RNF-08, RNF-14) |
