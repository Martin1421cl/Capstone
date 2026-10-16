"""Tablas de la base interna de K-Secure.

Regla de oro: el dato original NUNCA se guarda en claro. Se guarda enmascarado
para mostrarlo, y cifrado para que un auditor con la clave pueda verlo (ver boveda.py).
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Configuracion(Base):
    __tablename__ = "configuracion"

    clave: Mapped[str] = mapped_column(String(50), primary_key=True)
    valor: Mapped[bytes] = mapped_column(LargeBinary)


class Escaneo(Base):
    __tablename__ = "escaneos"

    id: Mapped[int] = mapped_column(primary_key=True)
    origen_tipo: Mapped[str] = mapped_column(String(20))       # "archivo" o "bd"
    origen_nombre: Mapped[str] = mapped_column(String(300))
    fecha: Mapped[datetime] = mapped_column(default=datetime.now)
    filas_por_fuente: Mapped[dict] = mapped_column(type_=JSON, default=dict)
    errores: Mapped[list] = mapped_column(type_=JSON, default=list)
    # Llave con la que se cifraron los originales de este escaneo, cifrada a su vez con la llave pública.
    llave_cifrada: Mapped[bytes] = mapped_column(LargeBinary)

    hallazgos: Mapped[list["Hallazgo"]] = relationship(
        back_populates="escaneo", cascade="all, delete-orphan", passive_deletes=True)


class Hallazgo(Base):
    __tablename__ = "hallazgos"

    id: Mapped[int] = mapped_column(primary_key=True)
    escaneo_id: Mapped[int] = mapped_column(ForeignKey("escaneos.id", ondelete="CASCADE"), index=True)
    fuente: Mapped[str] = mapped_column(String(300))           # archivo o tabla
    columna: Mapped[str | None] = mapped_column(String(300))   # solo bases de datos
    posicion: Mapped[str] = mapped_column(String(300))         # "línea 4" / "fila id=7"
    tipo: Mapped[str] = mapped_column(String(50), index=True)
    riesgo: Mapped[str] = mapped_column(String(20), index=True)
    confianza: Mapped[int] = mapped_column(Integer)
    nivel_confianza: Mapped[str] = mapped_column(String(10))
    contexto: Mapped[str] = mapped_column(Text, default="")    # palabras clave que influyeron
    valor_enmascarado: Mapped[str] = mapped_column(String(300))
    valor_cifrado: Mapped[bytes] = mapped_column(LargeBinary)

    escaneo: Mapped[Escaneo] = relationship(back_populates="hallazgos")


class Regla(Base):
    """Regla creada desde la pantalla "Reglas" (ver validators/regla.py)."""

    __tablename__ = "reglas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)   # ej. PASAPORTE; es el "tipo" del hallazgo
    descripcion: Mapped[str] = mapped_column(String(300), default="")
    patron: Mapped[str] = mapped_column(String(500))
    ejemplos: Mapped[list | None] = mapped_column(type_=JSON, default=list)  # con qué se armó el patrón
    validacion: Mapped[str] = mapped_column(String(20), default="ninguna")
    palabras_positivas: Mapped[list] = mapped_column(type_=JSON, default=list)
    palabras_negativas: Mapped[list] = mapped_column(type_=JSON, default=list)
    requiere_contexto: Mapped[bool] = mapped_column(Boolean, default=False)
    confianza: Mapped[int] = mapped_column(Integer, default=70)
    riesgo: Mapped[str] = mapped_column(String(20))
    visibles: Mapped[int] = mapped_column(Integer, default=4)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class AjusteValidador(Base):
    """Cambios a un validador incluido (RUT, TELEFONO...): activarlo y sumarle palabras de contexto."""

    __tablename__ = "ajustes_validadores"

    nombre: Mapped[str] = mapped_column(String(50), primary_key=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    palabras_positivas: Mapped[list] = mapped_column(type_=JSON, default=list)
    palabras_negativas: Mapped[list] = mapped_column(type_=JSON, default=list)
