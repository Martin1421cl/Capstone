"""Servidor web, equivalente a internal/web de ferret-scan.

Ejecutar:  uvicorn ksecure.web.app:app --reload   (documentación de la API en /docs)
"""

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ksecure.core.models import Match
from ksecure.preprocessors import process_file
from ksecure.validators import default_validators

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB por archivo, igual que ferret-scan

app = FastAPI(title="K-Secure", description="Detección de datos sensibles chilenos en archivos")
_validators = default_validators()


def match_to_dict(m: Match) -> dict:
    return {
        "text": m.text,
        "type": m.type,
        "confidence": m.confidence,
        "confidence_level": m.confidence_level.value,
        "risk_level": m.risk_level.value,
        "line_number": m.line_number,
        "start_column": m.start_column,
        "end_column": m.end_column,
        "positive_keywords": m.context.positive_keywords,
        "negative_keywords": m.context.negative_keywords,
        "metadata": m.metadata,
    }


async def scan_upload(upload: UploadFile) -> dict:
    name = os.path.basename(upload.filename or "archivo")
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return {"filename": name, "success": False, "error": "archivo demasiado grande (máx. 100 MB)", "matches": []}
    # Se guarda con un nombre temporal: del nombre del usuario solo se usa la extensión.
    fd, path = tempfile.mkstemp(suffix=Path(name).suffix.lower())
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        content = process_file(path)
    finally:
        os.remove(path)
    if not content.success:
        return {"filename": name, "success": False, "error": content.error, "matches": []}
    matches = [m for v in _validators for m in v.validate_content(content.text, name)]
    matches.sort(key=lambda m: (m.line_number, m.start_column))
    return {
        "filename": name,
        "success": True,
        "processor_type": content.processor_type,
        "page_count": content.page_count,
        "matches": [match_to_dict(m) for m in matches],
    }


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scan")
async def scan(files: list[UploadFile]):
    """Escanea uno o más archivos y devuelve los datos sensibles encontrados en cada uno."""
    if not files:
        raise HTTPException(400, "no se envió ningún archivo")
    results = [await scan_upload(f) for f in files]
    return {"results": results, "total_matches": sum(len(r["matches"]) for r in results)}
