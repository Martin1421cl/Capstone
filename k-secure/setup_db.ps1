# Configurar la contraseña del usuario 'postgres' para evitar el prompt
$env:PGPASSWORD = "1234"

# Ajusta la ruta si tu PostgreSQL está instalado en otra carpeta
$psql_path = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

# Comprobar y crear el usuario si no existe
$userExists = & $psql_path -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='ksecure_user'"
if ($userExists -ne "1") {
    # Aquí se aplican los privilegios exactos de la imagen
    & $psql_path -U postgres -c "CREATE USER ksecure_user WITH LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '1234';"
    Write-Host "Usuario 'ksecure_user' creado exitosamente con sus privilegios." -ForegroundColor Green
} else {
    Write-Host "El usuario 'ksecure_user' ya existe. Omitiendo..." -ForegroundColor Yellow
}

# Comprobar y crear la base de datos si no existe
$dbExists = & $psql_path -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='ksecure_db'"
if ($dbExists -ne "1") {
    & $psql_path -U postgres -c "CREATE DATABASE ksecure_db OWNER ksecure_user;"
    Write-Host "Base de datos 'ksecure_db' creada exitosamente." -ForegroundColor Green
} else {
    Write-Host "La base de datos 'ksecure_db' ya existe. Omitiendo..." -ForegroundColor Yellow
}

# Limpiar la variable de la memoria por seguridad
$env:PGPASSWORD = ""