"""Router de archivos, equivalente a internal/router de ferret-scan.

Cada archivo pasa por todos los preprocesadores que lo aceptan (ej. un .docx
por el de texto y el de metadata). Los textos se unen en uno solo y cada tramo
queda registrado en sections, para saber de dónde salió cada hallazgo.
"""

import os

from ksecure.preprocessors.base import Preprocessor, ProcessedContent, Section
from ksecure.preprocessors.office import OfficeMetadataPreprocessor, OfficeTextPreprocessor
from ksecure.preprocessors.pdf import PdfMetadataPreprocessor, PdfTextPreprocessor
from ksecure.preprocessors.texto import PlainTextPreprocessor


def default_preprocessors() -> list[Preprocessor]:
    return [
        PlainTextPreprocessor(), OfficeTextPreprocessor(), PdfTextPreprocessor(),
        OfficeMetadataPreprocessor(), PdfMetadataPreprocessor(),
    ]


def process_file(path: str, preprocessors: list[Preprocessor] | None = None) -> ProcessedContent:
    combined = ProcessedContent(
        filename=os.path.basename(path),
        format=os.path.splitext(path)[1].lower().lstrip("."),
    )
    chosen = [p for p in (preprocessors or default_preprocessors()) if p.can_process(path)]
    if not chosen:
        combined.error = "tipo de archivo no soportado"
        return combined

    text, types, errors = "", [], []
    for p in chosen:
        r = p.process(path)
        if not r.success:
            errors.append(f"{p.name}: {r.error}")
            continue
        if not r.text:
            continue
        if text:
            text += f"\n\n--- {p.name} ---\n"
        combined.sections.append(Section(p.name, len(text), len(text) + len(r.text)))
        text += r.text
        types.append(r.processor_type)
        combined.page_count = combined.page_count or r.page_count
        combined.metadata.update({f"{p.name}_{k}": v for k, v in r.metadata.items()})

    combined.text = text
    combined.processor_type = "+".join(types)
    # Éxito si al menos un preprocesador pudo leer el archivo, aunque esté vacío.
    combined.success = len(errors) < len(chosen)
    combined.error = "; ".join(errors)
    return combined
