# Modelo de datos (diagrama entidad-relación) — K-Secure

K-Secure tiene **dos tipos de base de datos**:

1. **Base interna**: la de K-Secure. Guarda escaneos, hallazgos, reglas, cuentas y bitácora. Es SQLite en un PC
   y PostgreSQL (Neon) en la nube; las tablas se definen con SQLAlchemy en
   `k-secure-web/ksecure/almacenamiento/modelos.py`.
2. **Base del cliente**: la que se escanea, siempre en solo lectura. Para la demo se usa
   `k-secure-web/demo/cliente_demo.sql` (empresa ficticia con datos sintéticos).

> **Regla de oro del modelo:** el dato original **nunca** se guarda en claro. Cada hallazgo tiene
> `valor_enmascarado` (para mostrar) y `valor_cifrado` (para el auditor con la clave).

---

## 1. Base interna de K-Secure

```mermaid
erDiagram
    ESCANEOS ||--o{ HALLAZGOS : "contiene"
    USUARIOS ||--o{ SESIONES : "abre"
    USUARIOS ||--o{ CODIGOS_RECUPERACION : "solicita"
    USUARIOS |o..o{ BITACORA : "registra (sin FK)"
    ESCANEOS |o..o{ BITACORA : "referencia (sin FK)"

    ESCANEOS {
        int id PK
        string origen_tipo "archivo | bd"
        string origen_nombre
        datetime fecha
        json filas_por_fuente
        json errores
        bytes llave_cifrada "llave AES del escaneo, cifrada con RSA"
    }
    HALLAZGOS {
        int id PK
        int escaneo_id FK
        string fuente "archivo o tabla"
        string columna "solo bases de datos"
        string posicion "línea 4 | fila id=7"
        int numero
        string tipo "RUT, TELEFONO, TARJETA..."
        string riesgo "Público | Interno | Confidencial | Restringido"
        int confianza "0 a 100"
        string nivel_confianza "HIGH | MEDIUM | LOW"
        text contexto
        string valor_enmascarado
        bytes valor_cifrado
        string revision "confirmado | falso_positivo"
        string revisado_por
        datetime revisado_en
        string nota_revision
    }
    USUARIOS {
        int id PK
        string usuario UK
        string nombre
        string correo UK
        string rol "Admin | Auditor | Visor"
        string clave_hash "bcrypt"
        bool activo
        bool debe_cambiar_clave
        int intentos_fallidos
        datetime bloqueado_hasta
        int fallos_auditor
        datetime auditor_bloqueado_hasta
        datetime creado
        datetime ultimo_ingreso
    }
    SESIONES {
        string token_hash PK "SHA-256 del token"
        int usuario_id FK
        datetime creada
        datetime ultimo_uso
        datetime expira
    }
    CODIGOS_RECUPERACION {
        int id PK
        int usuario_id FK
        string codigo_hash "bcrypt"
        datetime creado
        datetime expira
        int intentos
        bool usado
    }
    BITACORA {
        int id PK
        datetime fecha
        string accion
        string categoria
        bool alerta
        int usuario_id
        string usuario
        string nombre
        int afectado_id
        string detalle
        string ip
        int escaneo_id
    }
    REGLAS {
        int id PK
        string nombre UK "tipo del hallazgo"
        string descripcion
        string patron "expresión regular"
        json ejemplos
        string validacion
        json palabras_positivas
        json palabras_negativas
        bool requiere_contexto
        int confianza
        string riesgo
        int visibles
        bool activa
    }
    AJUSTES_VALIDADORES {
        string nombre PK "RUT, TELEFONO..."
        bool activo
        json palabras_positivas
        json palabras_negativas
    }
    CONFIGURACION {
        string clave PK
        bytes valor "llave pública y privada cifrada"
    }
```

### Descripción de las entidades

| Tabla | Para qué sirve | Relaciones |
|---|---|---|
| `escaneos` | Un escaneo de archivos o de una base de datos | 1 escaneo → N hallazgos (borrado en cascada) |
| `hallazgos` | Cada dato sensible encontrado, enmascarado y cifrado | N hallazgos → 1 escaneo |
| `usuarios` | Cuentas para entrar a K-Secure (las crea un Admin) | 1 usuario → N sesiones y N códigos |
| `sesiones` | Sesión abierta en un navegador; solo se guarda el hash del token | N sesiones → 1 usuario (cascada) |
| `codigos_recuperacion` | Código de 6 dígitos para recuperar la contraseña | N códigos → 1 usuario (cascada) |
| `bitacora` | Quién hizo qué y cuándo; solo se agregan filas | **Sin llaves foráneas a propósito**: el evento se conserva aunque se borre el escaneo o la cuenta |
| `reglas` | Detectores creados desde la pantalla Reglas | Independiente |
| `ajustes_validadores` | Validadores incluidos apagados o con palabras extra | Independiente |
| `configuracion` | Llaves de la bóveda (RSA) | Independiente |

### Decisiones de diseño

- **Cifrado híbrido:** cada escaneo tiene su propia llave AES (`escaneos.llave_cifrada`), cifrada con la llave
  pública RSA de `configuracion`. Para ver un original se necesita la clave de auditor, que descifra la llave privada.
- **Contraseñas y tokens nunca en claro:** `clave_hash` y `codigo_hash` con bcrypt; `token_hash` con SHA-256.
- **Índices** en `hallazgos.tipo`, `hallazgos.riesgo`, `hallazgos.revision` y `bitacora.fecha` para que los filtros
  de la pantalla Resultados y Bitácora respondan rápido con miles de filas.
- **Campos JSON** (`palabras_positivas`, `errores`...) para listas que se leen completas y no se consultan por partes.

---

## 2. Base del cliente simulado (demo)

Empresa ficticia con tablas al estilo SAP. K-Secure debe encontrar los datos sensibles **aunque el nombre de la
columna no lo diga** (por ejemplo `stcd1` es el RUT y `zzdata` guarda tarjetas).

```mermaid
erDiagram
    KNA1 ||--o{ ZPAGOS : "kunnr"
    KNA1 {
        varchar kunnr PK "N° de cliente"
        varchar name1 "nombre"
        varchar stcd1 "RUT (sensible)"
        varchar telf1 "teléfono (sensible)"
        varchar smtp_addr "correo (sensible)"
        varchar ort01 "comuna"
    }
    ZPAGOS {
        serial id PK
        varchar kunnr FK
        varchar zzdata "tarjeta (sensible)"
        int monto
        varchar glosa
    }
    EMPLEADOS {
        serial id PK
        varchar nombre
        varchar run "RUT (sensible)"
        varchar cuenta_bancaria "sensible"
        varchar patente_vehiculo "sensible"
        varchar correo "sensible"
    }
    VENTAS {
        int folio PK
        varchar rut_empresa "RUT de empresa"
        int total
    }
```

---

**Versión en imagen** (para pegar en informes y presentaciones): [`er_base_interna.png`](img/er_base_interna.png) · [`er_cliente_demo.png`](img/er_cliente_demo.png)
