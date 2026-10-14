"""Interfaz de los preprocesadores, equivalente a internal/preprocessors de ferret-scan.

Un preprocesador saca el texto (o la metadata) de un tipo de archivo para que
los validadores lo revisen. Cada uno declara qué extensiones atiende y entrega
un ProcessedContent.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Section:
    """Tramo de ProcessedContent.text y qué preprocesador lo produjo.

    Como ContentSection de ferret-scan: la estructura va aparte del texto, para
    que un documento que contenga "--- office_metadata ---" no pueda fingir una sección.
    """

    name: str
    start: int
    end: int


@dataclass
class ProcessedContent:
    filename: str
    text: str = ""
    format: str = ""
    processor_type: str = ""
    page_count: int = 0
    success: bool = False
    error: str = ""
    metadata: dict = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)


class Preprocessor(ABC):
    name: str = ""
    processor_type: str = ""
    extensions: tuple[str, ...] = ()

    def can_process(self, path: str) -> bool:
        return os.path.splitext(path)[1].lower() in self.extensions

    @abstractmethod
    def extract(self, path: str) -> tuple[str, dict]:
        """Texto extraído y metadata (dict). Lanza una excepción si el archivo no se puede leer."""

    def process(self, path: str) -> ProcessedContent:
        result = ProcessedContent(
            filename=os.path.basename(path),
            format=os.path.splitext(path)[1].lower().lstrip("."),
            processor_type=self.processor_type,
        )
        try:
            result.text, result.metadata = self.extract(path)
            result.page_count = result.metadata.get("page_count", 0)
            result.success = True
        except Exception as e:  # un archivo dañado no debe botar el escaneo completo
            result.error = f"{type(e).__name__}: {e}"
        return result


def format_fields(fields: dict) -> str:
    """Campos de metadata como "Clave: valor" por línea, omitiendo los vacíos (FormatMetadataField)."""
    return "".join(f"{k}: {v}\n" for k, v in fields.items() if v not in (None, "", 0))
