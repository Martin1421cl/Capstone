"""Plan B: restablecer la contraseña de una cuenta directamente en la base, sin entrar a la web.

Sirve cuando nadie puede entrar como administrador (por ejemplo, el único admin olvidó su
contraseña). Quien tiene la connection string de la base ya tiene acceso total a ella, así que
este comando no abre ninguna puerta nueva.

Uso (desde la carpeta k-secure-web, con el entorno virtual activado):

  python -m ksecure.restablecer                      # lista las cuentas
  python -m ksecure.restablecer emanuel              # nueva contraseña temporal para "emanuel"
  python -m ksecure.restablecer emanuel --admin      # además la deja como Admin activa

Por defecto usa la misma base que la app en este PC (data/ksecure.db, o KSECURE_DB_URL si está
definida). Para la base de la nube (Neon), pasar su connection string:

  python -m ksecure.restablecer emanuel --url "postgresql://usuario:clave@ep-xxx.neon.tech/neondb?sslmode=require"
"""

import argparse
import sys

from sqlalchemy import select

from ksecure.almacenamiento import bitacora, usuarios
from ksecure.almacenamiento.db import crear_sesiones
from ksecure.almacenamiento.modelos import Usuario


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m ksecure.restablecer",
                                description="Restablece la contraseña de una cuenta de K-Secure sin entrar a la web.")
    p.add_argument("usuario", nargs="?", help="usuario de la cuenta (sin él, lista las cuentas)")
    p.add_argument("--admin", action="store_true", help="además deja la cuenta como Admin y activa")
    p.add_argument("--url", help="connection string de la base (por defecto, la de este PC o KSECURE_DB_URL)")
    a = p.parse_args(argv)

    try:
        sesiones = crear_sesiones(a.url)
    except Exception as e:  # el mensaje del motor es lo más útil (clave mala, servidor caído...)
        print(f"No se pudo abrir la base: {str(e).splitlines()[0]}", file=sys.stderr)
        return 1

    with sesiones() as db:
        if not a.usuario:
            cuentas = usuarios.listar(db)
            if not cuentas:
                print("La base no tiene cuentas: al abrir la web se pide crear el administrador.")
            for u in cuentas:
                estado = "activa" if u.activo else "desactivada"
                print(f"  {u.usuario:<20} {u.rol:<8} {estado:<12} {u.nombre}")
            return 0

        cuenta = db.scalar(select(Usuario).where(Usuario.usuario == a.usuario.strip().lower()))
        if cuenta is None:
            print(f'No existe la cuenta "{a.usuario}". Corre el comando sin usuario para ver la lista.', file=sys.stderr)
            return 1
        if a.admin:
            cuenta.rol, cuenta.activo = usuarios.ADMIN, True
            db.commit()
        cuenta, temporal = usuarios.restablecer(db, cuenta.id)
        bitacora.registrar(db, "clave_restablecida",
                           f"Contraseña temporal nueva para @{cuenta.usuario} desde la terminal (python -m ksecure.restablecer)"
                           + (", y quedó como Admin activa" if a.admin else ""), afectado=cuenta)

    print(f"Cuenta: {cuenta.usuario} ({cuenta.rol}{'' if cuenta.activo else ', desactivada'})")
    print(f"Contraseña temporal: {temporal}")
    print("Entra con ella a K-Secure: te pedirá crear una contraseña nueva. Sus sesiones abiertas se cerraron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
