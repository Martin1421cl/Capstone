# Diagrama de componentes y despliegue (UML) — K-Secure

---

## 1. Componentes

Cada paquete de `k-secure-web/ksecure/` es un componente con una responsabilidad. Las dependencias van en un solo
sentido: la web usa el escaneo y el almacenamiento, el escaneo usa preprocesadores y validadores, y el núcleo
(`core`) no depende de nadie.

```mermaid
flowchart TB
    subgraph Cliente["Navegador"]
        UI["«componente»<br/>Web estática<br/>HTML · CSS · JS (módulos ES)"]
    end

    subgraph App["Servidor K-Secure (FastAPI + Uvicorn)"]
        direction TB
        WEB["«componente» web<br/>app.py · api/*"]
        SES["«componente» sesion<br/>login y permisos por rol"]
        ESC["«componente» escaneo<br/>archivos · celdas · bases_datos"]
        PRE["«componente» preprocessors<br/>texto · tablas · office · pdf"]
        VAL["«componente» validators<br/>rut · telefono · tarjeta · email<br/>cuenta_bancaria · patente · secreto · regla"]
        CORE["«componente» core<br/>Match · ContextInfo · niveles"]
        ALM["«componente» almacenamiento<br/>repositorio · boveda · usuarios<br/>reglas · bitacora · db"]
        EXP["«componente» exportar<br/>CSV · JSON · PDF"]
        COR["«componente» correo"]
    end

    subgraph Datos["Datos"]
        BDI[("Base interna<br/>SQLite / PostgreSQL")]
        BDC[("Bases del cliente<br/>PostgreSQL · MySQL<br/>SQL Server · Oracle")]
    end

    GAS["Apps Script de Gmail<br/>(envío de correos)"]

    UI -- "HTTP/JSON<br/>(cookie de sesión)" --> WEB
    WEB --> SES
    WEB --> ESC
    WEB --> ALM
    WEB --> EXP
    SES --> ALM
    ESC --> PRE
    ESC --> VAL
    VAL --> CORE
    PRE --> CORE
    ALM --> CORE
    ALM -- "SQLAlchemy" --> BDI
    ESC -- "solo SELECT" --> BDC
    COR -- "HTTPS" --> GAS
    SES --> COR
```

| Componente | Interfaz que ofrece | Depende de |
|---|---|---|
| `web` | API REST `/api/*` y páginas estáticas | sesion, escaneo, almacenamiento, exportar |
| `sesion` | `requiere(rol)` para cada endpoint | almacenamiento (usuarios) |
| `escaneo` | `escanear_archivos()`, `escanear_bd()` → `ResultadoEscaneo` | preprocessors, validators |
| `preprocessors` | `process_file(ruta)` → `ProcessedContent` | core |
| `validators` | `Validator.validate_content()` → `list[Match]` | core |
| `almacenamiento` | `repositorio`, `boveda`, `usuarios`, `reglas`, `bitacora` | base interna |
| `exportar` | `a_csv()`, `a_json()`, `a_pdf()` | reportlab |
| `correo` | `Correo.enviar()` | Apps Script (HTTPS) |

---

## 2. Despliegue

K-Secure se puede desplegar de tres formas con el mismo código.

```mermaid
flowchart LR
    subgraph Nube["Producción (gratis)"]
        direction TB
        RENDER["«nodo» Render<br/>Python 3.13<br/>uvicorn ksecure.web.app:app"]
        NEON[("«nodo» Neon<br/>PostgreSQL<br/>AWS us-east-2")]
        RENDER -- "TLS" --> NEON
    end

    subgraph Docker["Servidor propio (Docker Compose)"]
        direction TB
        APPC["«contenedor» ksecure-app<br/>python:3.13-slim · puerto 8000"]
        DBC[("«contenedor» ksecure-db<br/>postgres:16")]
        DEMO[("«contenedor» cliente-demo<br/>postgres:16 · perfil demo")]
        APPC --> DBC
        APPC -. "escaneo de prueba" .-> DEMO
    end

    subgraph Local["PC del equipo"]
        PC["«nodo» uvicorn local<br/>SQLite en data/"]
    end

    USR["Navegador"] -- "HTTPS" --> RENDER
    USR -- "HTTP :8000" --> APPC
    USR -- "HTTP :8000" --> PC
    GITHUB["GitHub<br/>Martin1421cl/Capstone"] -- "despliegue automático<br/>(render.yaml)" --> RENDER
```

---

**Versión en imagen** (para pegar en informes y presentaciones): [`componentes.png`](img/componentes.png) · [`despliegue.png`](img/despliegue.png)
