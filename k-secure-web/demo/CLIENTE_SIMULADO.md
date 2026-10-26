# Cliente simulado: Comercial Austral Demo SpA

Base de datos de una empresa **ficticia** para probar K-Secure como si fuera la de un cliente real.
Todos los datos son sintéticos: los RUT tienen dígito verificador correcto pero son al azar, las
tarjetas pasan Luhn pero no existen, las claves y tokens tienen la forma real pero son inventados.

El script `demo/cliente_simulado.py` la crea en **Neon** (PostgreSQL en la nube) o en un archivo
**SQLite**. Siempre genera los mismos datos, así dos escaneos se pueden comparar.

## Las 11 tablas (~18.000 filas)

| Tabla | Qué simula | Datos sensibles | Trampas (no son datos personales) |
|---|---|---|---|
| `cli_maestro` | Clientes personas y empresas | RUT en `id_tri`, teléfono en `fon_1`, correo en `eml_1` (nombres crípticos); celulares y RUT escritos en `obs_cli` | — |
| `rh_pers` | Personal | RUN sin puntos, cuenta bancaria, correos, celulares | — |
| `rem_liquidaciones` | Remuneraciones de un sistema antiguo | RUT **partido** en `rut_num` + `rut_dv`, cuenta de depósito | Montos |
| `fi_pagos` | Pagos | Número de tarjeta completo en `ref_pago` | Referencias de transferencia, `cod_aut` |
| `vt_docs` | Boletas y facturas | RUT de empresa en facturas | `folio` de 7 dígitos, montos |
| `prov_maestro` | Proveedores | RUT de empresa, cuenta corriente | Casillas `ventas@`, `contacto@` (públicas) |
| `sop_tickets` | Mesa de ayuda | RUT, correo, tarjeta, cuenta, celular y patente dentro del texto | "tarjeta terminada en 1234", N° de pedido |
| `flota` | Vehículos | Patentes nuevas y antiguas en `ppu` | `nro_motor` |
| `sys_integraciones` | Credenciales de sistemas | Claves AWS y token de GitHub | — |
| `log_accesos` | Registro de accesos | IP (K-Secure aún no las detecta) | Todo lo demás |
| `inv_productos` | Inventario | — | `cod_barras` de 13 dígitos |

## Paso a paso en Neon

1. En tu proyecto de Neon crea una base de datos nueva llamada `cliente_simulado`.
   Así queda separada de la base interna de K-Secure.
2. Pulsa **Connect**, elige la base `cliente_simulado` y copia la *connection string*.
3. Desde la carpeta `k-secure-web`, con el entorno virtual activado, carga los datos y crea el
   usuario de solo lectura (la clave necesita 12 caracteres o más, con mayúsculas, minúsculas,
   números y símbolos):

   ```powershell
   python demo/cliente_simulado.py --url "PEGA-AQUI-LA-CONNECTION-STRING" --lector-clave "Lector-K-Secure-2026"
   ```

4. En K-Secure: **Base de datos → PostgreSQL**:

   | Campo | Valor |
   |---|---|
   | Servidor | el host de la connection string (lo que va entre `@` y `/`, ej. `ep-xxx.sa-east-1.aws.neon.tech`) |
   | Puerto | 5432 |
   | Base | `cliente_simulado` |
   | Usuario | `ksecure_lector` |
   | Contraseña | la que pusiste en `--lector-clave` |

   Con **Probar conexión** deben aparecer las 11 tablas. Para revisarlas completas elige 10.000 filas por tabla.

`ksecure_lector` es el mismo tipo de usuario que se le pide a un cliente real: solo puede hacer `SELECT`.
Si intenta escribir, PostgreSQL responde "permission denied".

**Otras opciones**

- Recargar desde cero: corre el mismo comando de nuevo. Borra y crea solo sus 11 tablas, y le
  devuelve el permiso de lectura a `ksecure_lector` aunque no pongas `--lector-clave`.
- Más volumen: `--escala 5` genera ~90.000 filas.
- Sin internet: `python demo/cliente_simulado.py --sqlite cliente_simulado.db` y sube el archivo
  en **Archivos**. No subas ese `.db` al repo: trae tokens falsos con forma real y GitHub podría
  bloquear el push (ya está en `.gitignore`).

## Qué debería encontrar K-Secure

Medido el 26 de octubre de 2026 con `--escala 1`, PostgreSQL y 100.000 filas por tabla:
**15.304 hallazgos en 21 columnas, en unos 5 segundos**.

| Columna | Resultado |
|---|---|
| `cli_maestro.id_tri` | RUT en 2.000 de 2.000 filas (personas Restringido, empresas Interno) |
| `cli_maestro.fon_1` / `eml_1` | Teléfono 2.000 de 2.000 · correo 1.833 (las casillas de área quedan como Público) |
| `cli_maestro.obs_cli` | 568 filas con celular o RUT dentro del texto |
| `rh_pers.run` | RUT en 250 de 250, confianza MEDIUM (viene sin puntos) |
| `rh_pers.nro_cta`, `prov_maestro.cta_cte`, `rem_liquidaciones.cta_dep` | Cuenta bancaria en todas las filas |
| `fi_pagos.ref_pago` | Tarjeta en las 2.788 filas que la tienen, ninguna se escapa |
| `vt_docs.rut_rec` | RUT de empresa en las 1.836 facturas (Interno) |
| `sop_tickets.detalle` | 447 tickets con RUT, correo, tarjeta, cuenta, celular o patente |
| `flota.ppu` | Patente en 60 de 60 (las antiguas con confianza LOW) |
| `sys_integraciones` | Las 4 credenciales y las 2 claves secretas de AWS en `notas` |
| Trampas | Sin hallazgos en folios, códigos de autorización, códigos de barra, N° de motor ni en `log_accesos` |

### Lo que la simulación muestra que falta mejorar

1. **RUT partido en dos columnas** (`rem_liquidaciones.rut_num` + `rut_dv`): no se detecta.
2. **Cuentas de 9 dígitos marcadas también como teléfono** (falso positivo): 13 en `prov_maestro`,
   25 en `rh_pers`, 150 en `rem_liquidaciones` y 9 en tickets. "cuenta" o "cta" en la columna
   podrían restar confianza al teléfono.
3. **Celular junto a "boleta folio"**: en 89 tickets el celular baja a LOW / Interno por las palabras
   negativas de la misma frase.
4. **Sin validador**: nombres, direcciones, fechas de nacimiento, sueldos, AFP/salud e IP.

Ojo con clientes reales: K-Secure hoy revisa solo las tablas del esquema por defecto (`public` en
PostgreSQL). Si el cliente usa otros esquemas, sus tablas no aparecen.
