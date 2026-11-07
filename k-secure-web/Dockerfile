# K-Secure en un contenedor: la misma app que corre en Render, lista para cualquier PC o servidor.
#
#   docker build -t ksecure .
#   docker run -p 8000:8000 ksecure            # con SQLite dentro del contenedor (demo rápida)
#   docker compose up --build                  # con PostgreSQL (ver docker-compose.yml)

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias primero: Docker reutiliza esta capa mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pyproject.toml .
COPY ksecure ./ksecure
COPY demo ./demo

# Usuario sin privilegios: si alguien vulnerara la app, no tendría permisos de root.
RUN useradd --create-home --uid 1000 ksecure \
    && mkdir -p /app/data \
    && chown -R ksecure:ksecure /app
USER ksecure

# La base interna SQLite (si no se usa KSECURE_DB_URL) vive aquí; montar un volumen para no perderla.
VOLUME ["/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status == 200 else 1)"

CMD ["uvicorn", "ksecure.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
