import random
from faker import Faker
from ksecure.database import SessionLocal, engine, Base
from ksecure.db_models import CompanyData


# Usamos el locale de Chile para que genere datos con formato local
fake = Faker('es_CL')

def generate_data(num_records=800):
    # Crea la tabla en PostgreSQL si no existe
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Limpiamos la tabla por si lo ejecutas más de una vez
    db.query(CompanyData).delete()
    db.commit()

    print(f"Generando {num_records} registros de prueba para K-Secure...")
    records = []
    
    for _ in range(num_records):
        # Generamos un RUT realista
        rut_simulado = f"{random.randint(5000000, 25000000)}-{random.choice('0123456789K')}"
        
        record = CompanyData(
            nombre=fake.name(),
            rut=rut_simulado,
            email=fake.email(),
            telefono=fake.phone_number(),
            tarjeta_credito=fake.credit_card_number(),
          
        )
        records.append(record)
    
    # Inserción masiva para mayor rendimiento
    db.bulk_save_objects(records)
    db.commit()
    db.close()
    print("¡Generación exitosa! Base de datos lista.")

if __name__ == "__main__":
    generate_data()