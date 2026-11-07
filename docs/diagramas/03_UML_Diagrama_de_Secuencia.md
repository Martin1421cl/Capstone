# Diagramas de secuencia (UML) — K-Secure

Tres flujos principales, tal como están implementados en `k-secure-web/ksecure/web/api/`.

---

## 1. Escanear archivos (CU-01)

El auditor sube uno o varios archivos. K-Secure los guarda en una carpeta temporal con un nombre propio (el nombre
del usuario nunca decide la ruta), los escanea, cifra cada original y borra los temporales.

```mermaid
sequenceDiagram
    autonumber
    actor A as Auditor
    participant W as Web (archivos.html)
    participant S as Sesión y roles
    participant API as API /api/archivos
    participant E as Escaneo (archivos.py)
    participant P as Preprocesadores
    participant V as Validadores
    participant R as Repositorio
    participant B as Bóveda
    participant DB as Base interna
    participant L as Bitácora

    A->>W: Elige archivos y presiona "Escanear"
    W->>API: POST /api/archivos (multipart)
    API->>S: requiere(AUDITOR)
    S-->>API: sesión válida, rol Auditor
    API->>B: ¿clave de auditor configurada?
    alt sin clave de auditor
        API-->>W: 409 "Primero crea la clave de auditor"
    end
    API->>API: guarda cada archivo en carpeta temporal (máx. 100 MB)
    API->>E: escanear_archivos(archivos, validadores activos)
    loop por cada archivo
        E->>P: process_file(ruta)
        P-->>E: texto + metadata (o tabla por columnas)
        loop por cada validador
            E->>V: validate_content(texto, nombre, columna)
            V-->>E: lista de Match (confianza, riesgo, enmascarado)
        end
    end
    E-->>API: ResultadoEscaneo
    API->>R: guardar(resultado)
    R->>B: nueva_llave_escaneo()
    B-->>R: llave AES + llave cifrada con RSA
    R->>DB: INSERT escaneo + hallazgos (enmascarado + cifrado)
    API->>L: anotar("escaneo_archivos")
    L->>DB: INSERT evento
    API-->>W: {escaneo_id}
    W->>A: Abre la página de resultados
```

---

## 2. Revelar un dato original (CU-04)

```mermaid
sequenceDiagram
    autonumber
    actor A as Auditor
    participant W as Web (resultados.html)
    participant API as API /api/hallazgos/{id}/revelar
    participant R as Repositorio
    participant B as Bóveda
    participant DB as Base interna
    participant L as Bitácora

    A->>W: Presiona "Ver original" e ingresa la clave de auditor
    W->>API: POST {clave}
    API->>DB: ¿la cuenta está bloqueada para revelar?
    alt bloqueada (5 fallos)
        API-->>W: 429 "Demasiados intentos. Espera N s"
    end
    API->>R: revelar(hallazgo_id, clave)
    R->>DB: lee valor_cifrado y llave_cifrada del escaneo
    R->>B: revelar(clave, llave_cifrada, valor_cifrado)
    alt clave incorrecta
        B-->>R: ClaveIncorrecta
        API->>DB: fallos_auditor + 1 (bloquea 1 min al llegar a 5)
        API->>L: anotar("revelar_fallido")
        API-->>W: 403 "Clave incorrecta"
    else clave correcta
        B->>B: descifra llave privada RSA → llave AES → valor
        B-->>R: valor original
        API->>L: anotar("dato_revelado") antes de responder
        API-->>W: {valor}
        W->>A: Muestra el dato original
    end
```

---

## 3. Iniciar sesión (CU-08)

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant W as Web (login.html)
    participant API as API /api/sesion/ingresar
    participant US as usuarios.py
    participant DB as Base interna
    participant L as Bitácora

    U->>W: Ingresa usuario y contraseña
    W->>API: POST {usuario, clave}
    API->>US: autenticar(usuario, clave)
    US->>DB: busca la cuenta
    alt cuenta bloqueada o desactivada
        US-->>API: CuentaBloqueada / CuentaDesactivada
        API->>L: anotar("cuenta_bloqueada" o "ingreso_fallido")
        API-->>W: 429 (bloqueada) o 403 (desactivada)
    else contraseña incorrecta
        US->>DB: intentos_fallidos + 1 (5 = bloqueo de 5 min)
        API->>L: anotar("ingreso_fallido", alerta)
        API-->>W: 401
    else contraseña correcta (bcrypt)
        API->>US: abrir_sesion(usuario)
        US->>DB: crea Sesion (solo hash SHA-256 del token)
        API->>L: anotar("ingreso")
        API-->>W: cookie de sesión (HttpOnly)
        alt contraseña temporal
            W->>U: Pide cambiar la contraseña
        else
            W->>U: Abre el inicio
        end
    end
```

---

**Versión en imagen** (para pegar en informes y presentaciones): [`secuencia_escanear_archivos.png`](img/secuencia_escanear_archivos.png) · [`secuencia_revelar_dato.png`](img/secuencia_revelar_dato.png) · [`secuencia_iniciar_sesion.png`](img/secuencia_iniciar_sesion.png)
