"""PDF, equivalente a text-extract-pdftextlib y meta-extract-pdflib de ferret-scan.

ferret-scan usa ledongthuc/pdf (texto) y pdfcpu (metadata); acá ambas cosas las hace pypdf.
"""

from pypdf import PdfReader

from ksecure.preprocessors.base import Preprocessor, format_fields

MAX_PAGES = 50  # el mismo tope de ferret-scan, para no eternizarse con PDFs enormes


def _open(path: str) -> PdfReader:
    reader = PdfReader(path)
    if reader.is_encrypted:
        reader.decrypt("")  # muchos PDF "protegidos" solo tienen clave de permisos, no de apertura
    return reader


class PdfTextPreprocessor(Preprocessor):
    name = "Text Extractor"
    processor_type = "document_text"
    extensions = (".pdf",)

    def extract(self, path: str) -> tuple[str, dict]:
        reader = _open(path)
        pages = [p.extract_text() or "" for p in reader.pages[:MAX_PAGES]]
        text = "\n--- PAGE BREAK ---\n".join(pages)
        fields = reader.get_fields() or {}
        form = "".join(f"Name: {name} Value: {f.get('/V')}\n"
                       for name, f in fields.items() if f.get("/V") not in (None, ""))
        if form:
            text += f"\n--- PDF Form Data ---\n{form}"
        return text, {"page_count": len(reader.pages)}


class PdfMetadataPreprocessor(Preprocessor):
    name = "pdf_metadata"
    processor_type = "pdf_metadata"
    extensions = (".pdf",)

    def extract(self, path: str) -> tuple[str, dict]:
        reader = _open(path)
        info = reader.metadata or {}
        fields = {
            "PDFVersion": reader.pdf_header.removeprefix("%PDF-"),
            "Encrypted": "true" if reader.is_encrypted else "",
            "Title": info.get("/Title", ""),
            "Author": info.get("/Author", ""),
            "Subject": info.get("/Subject", ""),
            "Keywords": info.get("/Keywords", ""),
            "Creator": info.get("/Creator", ""),
            "Producer": info.get("/Producer", ""),
            "CreationDate": info.get("/CreationDate", ""),
            "ModificationDate": info.get("/ModDate", ""),
            "PageCount": len(reader.pages),
        }
        fields = {k: str(v) for k, v in fields.items() if v not in (None, "")}
        # Campos propios del documento (ej. /RUT_Cliente), como FormatPropertiesMap.
        known = {"/Title", "/Author", "/Subject", "/Keywords", "/Creator", "/Producer", "/CreationDate", "/ModDate"}
        for key in sorted(set(info) - known):
            if str(info[key]).strip():
                fields[key.lstrip("/")] = str(info[key])
        fields["page_count"] = len(reader.pages)
        return format_fields({k: v for k, v in fields.items() if k != "page_count"}), fields
