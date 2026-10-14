"""Office (docx, xlsx, pptx) y OpenDocument (odt, ods, odp).

Igual que text-extract-officetextlib y meta-extract-officelib de ferret-scan:
estos archivos son ZIP con XML adentro, así que se leen con zipfile y
ElementTree, sin librerías de Office.
"""

import re
import zipfile
import xml.etree.ElementTree as ET

from ksecure.preprocessors.base import Preprocessor, format_fields

# Límites contra "zip bombs", los mismos de ferret-scan.
MAX_ENTRY_BYTES = 50 * 1024 * 1024
MAX_TOTAL_TEXT = 200 * 1024 * 1024

OOXML = (".docx", ".xlsx", ".pptx")
ODF = (".odt", ".ods", ".odp")


def _local(tag) -> str:
    """'{http://...}t' -> 't'. Comparar sin namespace aguanta cualquier prefijo."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


class _Package:
    """Las partes del ZIP, buscadas sin importar mayúsculas (un productor puede escribir 'Word/Document.xml')."""

    def __init__(self, zf: zipfile.ZipFile):
        self.zf = zf
        self.names = {n.lower(): n for n in zf.namelist()}

    def xml(self, name: str):
        real = self.names.get(name.lower())
        if real is None:
            return None
        with self.zf.open(real) as f:
            data = f.read(MAX_ENTRY_BYTES)
        try:
            return ET.fromstring(data)
        except ET.ParseError:
            return None  # parte truncada por el límite o dañada: se omite, como ferret-scan

    def matching(self, prefix: str, suffix: str = ".xml") -> list[str]:
        found = [n for low, n in self.names.items()
                 if low.startswith(prefix.lower()) and low.endswith(suffix) and "/_rels/" not in low]
        return sorted(found, key=_part_number)


def _part_number(name: str) -> tuple:
    """'ppt/slides/slide12.xml' -> 12, para ordenar slide2 antes que slide10."""
    m = re.search(r"(\d+)\.xml$", name, re.I)
    return (int(m.group(1)) if m else 10**9, name)


def _join_capped(parts: list[str]) -> str:
    out, total = [], 0
    for p in parts:
        if total > MAX_TOTAL_TEXT:
            break
        out.append(p)
        total += len(p)
    return "".join(out)


# --- Word -------------------------------------------------------------------

def _w_paragraph(p) -> str:
    chunks = []
    for el in p.iter():
        tag = _local(el.tag)
        if tag == "t" and el.text:
            chunks.append(el.text)
        elif tag == "tab":
            chunks.append("\t")
        elif tag in ("br", "cr"):
            chunks.append("\n")
    return "".join(chunks)


def _w_blocks(el, lines: list[str]):
    """Párrafos en líneas; tablas con una fila por línea y celdas separadas por tab."""
    for child in el:
        tag = _local(child.tag)
        if tag == "p":
            lines.append(_w_paragraph(child))
        elif tag == "tbl":
            for tr in (c for c in child.iter() if _local(c.tag) == "tr"):
                cells = [" ".join(_w_paragraph(p) for p in tc.iter() if _local(p.tag) == "p")
                         for tc in tr if _local(tc.tag) == "tc"]
                lines.append("\t".join(cells))
        else:  # body, sdt (controles de contenido), txbxContent...
            _w_blocks(child, lines)


def _w_text(root) -> str:
    lines: list[str] = []
    _w_blocks(root, lines)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _docx(pkg: _Package) -> str:
    root = pkg.xml("word/document.xml")
    if root is None:
        raise ValueError("word/document.xml no encontrado")
    parts = []
    for name in pkg.matching("word/header"):
        if (h := pkg.xml(name)) is not None and (t := _w_text(h)):
            parts.append(f"--- HEADER ---\n{t}\n\n")
    parts.append(_w_text(root))
    for name in pkg.matching("word/footer"):
        if (f := pkg.xml(name)) is not None and (t := _w_text(f)):
            parts.append(f"\n\n--- FOOTER ---\n{t}")
    return _join_capped(parts)


# --- Excel ------------------------------------------------------------------

def _xlsx(pkg: _Package) -> str:
    shared = []
    if (sst := pkg.xml("xl/sharedStrings.xml")) is not None:
        shared = ["".join(t.text or "" for t in si.iter() if _local(t.tag) == "t")
                  for si in sst if _local(si.tag) == "si"]
    parts = []
    for name in pkg.matching("xl/worksheets/sheet"):
        sheet = pkg.xml(name)
        if sheet is None:
            continue
        rows = []
        for row in (r for r in sheet.iter() if _local(r.tag) == "row"):
            cells = []
            for c in (c for c in row if _local(c.tag) == "c"):
                kind = c.get("t")
                v = next((e.text for e in c if _local(e.tag) == "v"), None)
                if kind == "s" and v is not None:
                    i = int(v)
                    value = shared[i] if 0 <= i < len(shared) else ""
                elif kind == "inlineStr":
                    value = "".join(t.text or "" for t in c.iter() if _local(t.tag) == "t")
                else:
                    value = v or ""
                if value:
                    cells.append(value)
            if cells:
                rows.append("\t".join(cells))
        label = name.rsplit("/", 1)[-1].removesuffix(".xml")
        parts.append(f"--- {label} ---\n" + "\n".join(rows) + "\n\n")
    return _join_capped(parts)


# --- PowerPoint -------------------------------------------------------------

def _a_text(root) -> str:
    """Texto de DrawingML: un párrafo <a:p> por línea."""
    lines = ["".join(t.text or "" for t in p.iter() if _local(t.tag) == "t")
             for p in root.iter() if _local(p.tag) == "p"]
    return "\n".join(l for l in lines if l)


def _notes_for(pkg: _Package, slide: str) -> str | None:
    """Las notas del orador de ESTA diapositiva, según su .rels (no por posición)."""
    folder, file = slide.rsplit("/", 1)
    rels = pkg.xml(f"{folder}/_rels/{file}.rels")
    if rels is None:
        return None
    for rel in rels:
        if rel.get("Type", "").endswith("/notesSlide"):
            target = rel.get("Target", "")
            return f"ppt/notesSlides/{target.rsplit('/', 1)[-1]}"
    return None


def _pptx(pkg: _Package) -> tuple[str, int]:
    slides = pkg.matching("ppt/slides/slide")
    parts = []
    for i, name in enumerate(slides, start=1):
        parts.append(f"--- Slide {i} ---\n")
        if (s := pkg.xml(name)) is not None:
            parts.append(_a_text(s))
        notes = _notes_for(pkg, name)
        if notes and (n := pkg.xml(notes)) is not None and (t := _a_text(n)):
            parts.append(f"\n[SPEAKER NOTES]\n{t}")
        parts.append("\n\n")
    for i, name in enumerate(pkg.matching("ppt/slideMasters/slideMaster"), start=1):
        if (m := pkg.xml(name)) is not None:
            parts.append(f"--- Master {i} ---\n{_a_text(m)}\n\n")
    return _join_capped(parts), len(slides)


# --- OpenDocument -----------------------------------------------------------

def _odf_paragraphs(root) -> str:
    return "\n".join("".join(p.itertext()) for p in root.iter() if _local(p.tag) in ("p", "h"))


def _ods_rows(root) -> str:
    rows = []
    for row in (r for r in root.iter() if _local(r.tag) == "table-row"):
        cells = ["\n".join("".join(p.itertext()) for p in cell.iter() if _local(p.tag) == "p")
                 for cell in row if _local(cell.tag) == "table-cell"]
        if any(cells):
            rows.append("\t".join(c for c in cells if c))
    return "\n".join(rows)


def _odf(pkg: _Package, ext: str) -> str:
    content = pkg.xml("content.xml")
    if content is None:
        raise ValueError("content.xml no encontrado")
    if ext == ".ods":
        return _ods_rows(content)
    text = _odf_paragraphs(content)
    styles = pkg.xml("styles.xml")
    if styles is not None and (s := _odf_paragraphs(styles).strip()):
        label = "MASTER SLIDES" if ext == ".odp" else "STYLES/HEADERS/FOOTERS"
        text += f"\n\n--- {label} ---\n{s}"
    return text


class OfficeTextPreprocessor(Preprocessor):
    name = "Text Extractor"
    processor_type = "document_text"
    extensions = OOXML + ODF

    def extract(self, path: str) -> tuple[str, dict]:
        ext = path[path.rfind("."):].lower()
        with zipfile.ZipFile(path) as zf:
            pkg = _Package(zf)
            if ext == ".docx":
                return _docx(pkg), {}
            if ext == ".xlsx":
                return _xlsx(pkg), {}
            if ext == ".pptx":
                text, slides = _pptx(pkg)
                return text, {"page_count": slides}
            return _odf(pkg, ext), {}


# --- Metadata ---------------------------------------------------------------

# Nombre del elemento XML -> campo, en el orden en que ferret-scan los muestra.
_OOXML_FIELDS = {
    "title": "Title", "subject": "Subject", "creator": "Author", "description": "Description",
    "keywords": "Keywords", "category": "Category", "Application": "Application",
    "AppVersion": "ApplicationVersion", "Company": "Company", "lastModifiedBy": "LastModifiedBy",
    "Manager": "Manager", "contentStatus": "ContentStatus", "identifier": "Identifier",
    "language": "Language", "revision": "Revision", "Template": "Template",
    "created": "CreationDate", "modified": "ModificationDate", "Pages": "PageCount",
    "Words": "WordCount", "Characters": "CharacterCount", "TotalTime": "TotalEditTime",
    "HiddenSlides": "HiddenSlides",
}
_ODF_FIELDS = {
    "title": "Title", "subject": "Subject", "initial-creator": "Author", "creator": "LastModifiedBy",
    "description": "Description", "keyword": "Keywords", "generator": "Application",
    "language": "Language", "editing-cycles": "Revision", "creation-date": "CreationDate",
    "date": "ModificationDate", "editing-duration": "TotalEditTime",
}


def _collect(root, mapping: dict, fields: dict):
    for el in root.iter():
        key = mapping.get(_local(el.tag))
        if key and el.text and el.text.strip():
            fields[key] = el.text.strip()


class OfficeMetadataPreprocessor(Preprocessor):
    name = "office_metadata"
    processor_type = "office_metadata"
    extensions = OOXML + ODF

    def extract(self, path: str) -> tuple[str, dict]:
        fields: dict = {}
        custom: dict = {}
        with zipfile.ZipFile(path) as zf:
            pkg = _Package(zf)
            if path.lower().endswith(ODF):
                if (meta := pkg.xml("meta.xml")) is not None:
                    _collect(meta, _ODF_FIELDS, fields)
                    for el in meta.iter():
                        if _local(el.tag) == "user-defined" and el.text:
                            name = next((v for k, v in el.attrib.items() if _local(k) == "name"), "")
                            custom[name] = el.text
                        elif _local(el.tag) == "document-statistic":
                            attrs = {_local(k): v for k, v in el.attrib.items()}
                            fields["PageCount"] = attrs.get("page-count", "")
                            fields["WordCount"] = attrs.get("word-count", "")
                            fields["CharacterCount"] = attrs.get("character-count", "")
            else:
                for part in ("docProps/core.xml", "docProps/app.xml"):
                    if (root := pkg.xml(part)) is not None:
                        _collect(root, _OOXML_FIELDS, fields)
                if (root := pkg.xml("docProps/custom.xml")) is not None:
                    for prop in root:
                        value = "".join(prop.itertext()).strip()
                        if value:
                            custom[prop.get("name", "")] = value
        ordered = {k: fields[k] for k in _OOXML_FIELDS.values() if k in fields}
        text = format_fields(ordered)
        if custom:
            text += "\n--- Custom Properties ---\n" + format_fields(
                {f"Custom_{k}": custom[k] for k in sorted(custom)})
        ordered.update({f"Custom_{k}": v for k, v in custom.items()})
        if ordered.get("PageCount", "").isdigit():
            ordered["page_count"] = int(ordered["PageCount"])
        return text, ordered
