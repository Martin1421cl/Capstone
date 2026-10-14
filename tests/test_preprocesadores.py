import zipfile

import pytest

from ksecure.preprocessors import process_file
from ksecure.preprocessors.texto import decode, looks_like_text
from ksecure.validators.rut import RutValidator

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
CORE = ('<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>Juan Pérez</dc:creator>'
        '<dc:title>Nómina</dc:title><cp:keywords>RUT 15.432.198-5</cp:keywords></cp:coreProperties>')


def make_zip(path, parts: dict):
    with zipfile.ZipFile(path, "w") as zf:
        for name, xml in parts.items():
            zf.writestr(name, xml)
    return str(path)


def make_pdf(path, lines, info="/Author (Ana Rojas)"):
    """PDF mínimo de una página con texto Helvetica, armado a mano."""
    stream = "BT /F1 12 Tf 72 720 Td " + " ".join(f"({l}) Tj 0 -16 Td" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< {info} >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    path.write_bytes(out)
    return str(path)


def ruts(content):
    return [m.metadata["rut_normalizado"] for m in RutValidator().validate_content(content.text, content.filename)]


# --- Texto plano ------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "RUT: 15.432.198-5 ñandú".encode("utf-8"),
    "RUT: 15.432.198-5 ñandú".encode("utf-8-sig"),
    "RUT: 15.432.198-5 ñandú".encode("utf-16"),
    "RUT: 15.432.198-5 ñandú".encode("utf-16-le"),
    "RUT: 15.432.198-5 ñandú".encode("cp1252"),
])
def test_decodificacion(raw):
    assert decode(raw) == "RUT: 15.432.198-5 ñandú"


def test_csv(tmp_path):
    p = tmp_path / "clientes.csv"
    p.write_bytes("nombre;rut\nAna;15.432.198-5\n".encode("cp1252"))
    r = process_file(str(p))
    assert r.success and r.processor_type == "plaintext"
    assert ruts(r) == ["15432198-5"]


def test_sin_extension_se_decide_por_contenido(tmp_path):
    texto, binario = tmp_path / "Dockerfile", tmp_path / "blob"
    texto.write_text("ENV RUT=15.432.198-5")
    binario.write_bytes(bytes(range(256)))
    assert process_file(str(texto)).success
    assert process_file(str(binario)).error == "tipo de archivo no soportado"


def test_pdf_no_pasa_como_texto():
    assert not looks_like_text(b"%PDF-1.4\n<< /Title (hola) >>")


# --- Office -----------------------------------------------------------------

def test_docx_parrafos_tablas_encabezado_y_metadata(tmp_path):
    doc = (f'<w:document {W}><w:body>'
           '<w:p><w:r><w:t>Nómina de</w:t></w:r><w:r><w:t xml:space="preserve"> trabajadores</w:t></w:r></w:p>'
           '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Nombre</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>RUT</w:t></w:r></w:p></w:tc></w:tr>'
           '<w:tr><w:tc><w:p><w:r><w:t>Ana</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>16.543.210-K</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
           '</w:body></w:document>')
    header = f'<w:hdr {W}><w:p><w:r><w:t>Confidencial</w:t></w:r></w:p></w:hdr>'
    p = make_zip(tmp_path / "nomina.docx", {
        "word/document.xml": doc, "word/header1.xml": header, "docProps/core.xml": CORE,
    })
    r = process_file(p)
    assert r.success and r.processor_type == "document_text+office_metadata"
    assert "--- HEADER ---\nConfidencial" in r.text
    assert "Nómina de trabajadores\nNombre\tRUT\nAna\t16.543.210-K" in r.text
    assert "Author: Juan Pérez\n" in r.text
    assert ruts(r) == ["16543210-K", "15432198-5"]  # tabla y Keywords de la metadata
    assert [s.name for s in r.sections] == ["Text Extractor", "office_metadata"]
    assert r.text[r.sections[1].start:].startswith("Title: Nómina")


def test_xlsx_shared_strings_e_inline(tmp_path):
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    sheet = (f'<worksheet {ns}><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
             '<row r="2"><c r="A2" t="inlineStr"><is><t>Ana</t></is></c><c r="B2" s="1"/><c r="C2"><v>15432198</v></c>'
             '<c r="D2" t="s"><v>2</v></c></row></sheetData></worksheet>')
    sst = f'<sst {ns}><si><t>Nombre</t></si><si><t>RUT</t></si><si><r><t>15.432.</t></r><r><t>198-5</t></r></si></sst>'
    p = make_zip(tmp_path / "a.xlsx", {
        "xl/worksheets/sheet10.xml": f'<worksheet {ns}><sheetData/></worksheet>',
        "xl/worksheets/sheet2.xml": sheet, "xl/sharedStrings.xml": sst,
    })
    r = process_file(p)
    assert r.text.startswith("--- sheet2 ---\nNombre\tRUT\nAna\t15432198\t15.432.198-5\n")
    assert r.text.index("sheet2") < r.text.index("sheet10")


def test_pptx_diapositivas_y_notas_por_rels(tmp_path):
    slide = lambda t: f'<p:sld xmlns:p="x" {A}><a:p><a:r><a:t>{t}</a:t></a:r></a:p></p:sld>'
    rels = ('<Relationships><Relationship Id="r1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" '
            'Target="../notesSlides/notesSlide7.xml"/></Relationships>')
    p = make_zip(tmp_path / "a.pptx", {
        "ppt/slides/slide1.xml": slide("Intro"), "ppt/slides/slide2.xml": slide("Cliente"),
        "ppt/slides/_rels/slide2.xml.rels": rels,
        "ppt/notesSlides/notesSlide7.xml": slide("RUT 15.432.198-5"),
    })
    r = process_file(p)
    assert "--- Slide 1 ---\nIntro\n\n--- Slide 2 ---\nCliente\n[SPEAKER NOTES]\nRUT 15.432.198-5" in r.text
    assert r.page_count == 2


def test_odt_y_ods(tmp_path):
    t = 'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
    tb = 'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    odt = make_zip(tmp_path / "a.odt", {
        "content.xml": f'<doc {t}><text:h>Ficha</text:h><text:p>RUT <text:span>15.432.198-5</text:span></text:p></doc>',
    })
    ods = make_zip(tmp_path / "a.ods", {
        "content.xml": f'<doc {t} {tb}><table:table-row><table:table-cell><text:p>Ana</text:p></table:table-cell>'
                       '<table:table-cell><text:p>15.432.198-5</text:p></table:table-cell></table:table-row></doc>',
    })
    assert process_file(odt).text == "Ficha\nRUT 15.432.198-5"
    assert process_file(ods).text == "Ana\t15.432.198-5"


def test_office_danado_no_bota_el_escaneo(tmp_path):
    p = tmp_path / "roto.docx"
    p.write_bytes(b"no soy un zip")
    r = process_file(str(p))
    assert not r.success and "BadZipFile" in r.error


# --- PDF --------------------------------------------------------------------

def test_pdf_texto_y_metadata(tmp_path):
    p = make_pdf(tmp_path / "a.pdf", ["Contrato de trabajo", "RUT 15.432.198-5"],
                 info="/Author (Ana Rojas) /RUT_Cliente (16.543.210-K)")
    r = process_file(p)
    assert r.success and r.processor_type == "document_text+pdf_metadata"
    assert "Contrato de trabajo" in r.text and "Author: Ana Rojas" in r.text
    assert "RUT_Cliente: 16.543.210-K" in r.text
    assert ruts(r) == ["15432198-5", "16543210-K"]
    assert r.page_count == 1
