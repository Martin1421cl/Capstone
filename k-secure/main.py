import os
import shutil
from fastapi import FastAPI, Depends, File, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ksecure.database import SessionLocal
from ksecure.db_models import DBScanResult
from ksecure.scanner import KSecureScanner
from ksecure.db_service import save_findings_to_db

app = FastAPI(title="K-Secure DLP")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/alertas")
def get_alertas(db: Session = Depends(get_db)):
    resultados = db.query(DBScanResult).order_by(DBScanResult.timestamp.desc()).all()
    return resultados

# --- NUEVO ENDPOINT PARA SUBIR Y ESCANEAR ARCHIVOS ---
@app.post("/api/scan")
async def scan_file_api(file: UploadFile = File(...)):
    # 1. Guardar el archivo temporalmente en el servidor
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 2. Escanear el archivo usando tu motor universal
        scanner = KSecureScanner()
        findings = scanner.scan_file(temp_file_path)
        
        # 3. Persistir en PostgreSQL
        if findings:
            save_findings_to_db(findings)
            
        return {"filename": file.filename, "findings_count": len(findings)}
        
    finally:
        # 4. Limpiar (borrar) el archivo temporal por seguridad
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)