from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import io
import pandas as pd
import pdfplumber
import docx

# Importaciones de la Base de Datos
from ksecure.database import get_db, engine, Base, DB_PASSWORD
from ksecure.db_models import CompanyData

# Importaciones de la Arquitectura de Validadores
from ksecure.validators.rut import RutValidator
from ksecure.validators.email import EmailValidator
from ksecure.validators.phone import PhoneValidator
from ksecure.validators.credit_card import CreditCardValidator

app = FastAPI()

# Asegurar que las tablas existan
Base.metadata.create_all(bind=engine)

# Instanciar los validadores
rut_validator = RutValidator()
email_validator = EmailValidator()
phone_validator = PhoneValidator()
cc_validator = CreditCardValidator()

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.get("/api/data")
def get_data(db: Session = Depends(get_db)):
    return db.query(CompanyData).all()

@app.post("/api/scan")
async def scan_data(file: Optional[UploadFile] = File(None), db: Session = Depends(get_db)):
    if file:
        content = await file.read()
        filename = file.filename.lower()
        text = ""
        
        try:
            if filename.endswith(".csv") or filename.endswith(".txt"):
                text = content.decode("utf-8", errors="ignore")
            elif filename.endswith(".pdf"):
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            elif filename.endswith(".docx"):
                doc = docx.Document(io.BytesIO(content))
                text_paragraphs = "\n".join([para.text for para in doc.paragraphs])
                text_tables = []
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            if cell.text:
                                text_tables.append(cell.text)
                text = text_paragraphs + "\n" + "\n".join(text_tables)
            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(content))
                text = df.to_string()
        except Exception as e:
            print(f"Error procesando {filename}: {e}")
            raise HTTPException(status_code=400, detail="Error al procesar el archivo")
        
        # Uso de la arquitectura POO (Método find() heredado de BaseValidator)
        ruts = [f.raw_value for f in rut_validator.find(text, filename)]
        emails = [f.raw_value for f in email_validator.find(text, filename)]
        telefonos = [f.raw_value for f in phone_validator.find(text, filename)]
        tarjetas = [f.raw_value for f in cc_validator.find(text, filename)]

        max_len = max(len(emails), len(ruts), len(telefonos), len(tarjetas))
        
        if max_len == 0:
            return {"message": "No se detectaron datos sensibles en el archivo.", "findings_count": 0}
        
        def pad_list(lst, size):
            return lst + [""] * (size - len(lst))
            
        emails = pad_list(emails, max_len)
        ruts = pad_list(ruts, max_len)
        telefonos = pad_list(telefonos, max_len)
        tarjetas = pad_list(tarjetas, max_len)
        
        new_records = []
        for i in range(max_len):
            new_record = CompanyData(
                nombre=f"Doc: {file.filename}",
                rut=ruts[i] if ruts[i] else None,
                email=emails[i] if emails[i] else None,
                telefono=telefonos[i] if telefonos[i] else None,
                tarjeta_credito=tarjetas[i] if tarjetas[i] else None
            )
            new_records.append(new_record)
        
        db.bulk_save_objects(new_records)
        db.commit()
        
        actual_findings = sum(1 for x in emails + ruts + telefonos + tarjetas if x != "")
        
        return {"message": "Archivo escaneado exitosamente", "findings_count": actual_findings}

    else:
        records = db.query(CompanyData).all()
        return {"message": "Base de datos analizada exitosamente.", "findings_count": len(records) * 4}

class AuthRequest(BaseModel):
    password: str

@app.post("/api/unmask")
def unmask_data(req: AuthRequest, db: Session = Depends(get_db)):
    if req.password != DB_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
    return db.query(CompanyData).all()