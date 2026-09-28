from pathlib import Path

from ksecure.report import ClassificationReport
from ksecure.scanner import KSecureScanner
from ksecure.database import init_db
from ksecure.db_service import save_findings_to_db

def main() -> None:
    # 1. Crear las tablas en PostgreSQL (si no existen)
    init_db()

    # 2. Inicializar el motor y escanear
    scanner = KSecureScanner()
    archivo_csv = Path("examples/sample_data.csv")
    
    print(f"Escaneando archivo: {archivo_csv.name}...")
    findings = scanner.scan_csv(archivo_csv) # Asumiendo que esta es la función en scanner.py

    # 3. Persistir en PostgreSQL los hallazgos enmascarados
    save_findings_to_db(findings)

    # 4. Generar reporte en consola (manteniendo el flujo anterior)
    report = ClassificationReport(findings)
    archivo_salida = "reporte_ksecure.json"
    
    # Le pasamos la ruta donde queremos guardar el JSON
    report.to_json(archivo_salida) 
    
    print("\n--- Reporte de Clasificación ---")
    print(f"El reporte completo se ha guardado exitosamente en el archivo: {archivo_salida}")

if __name__ == "__main__":
    main()