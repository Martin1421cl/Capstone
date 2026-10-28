"""Exportar los resultados de un escaneo (RF-15): CSV para Excel, JSON para otros sistemas y PDF de reporte.

Siempre enmascarado: los archivos llevan lo mismo que se ve en pantalla, nunca un dato original.
Reciben lo que arma repositorio.para_exportar (resumen del escaneo + hallazgos con los filtros).
"""

import io
import json
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from ksecure.core.texto import csv_excel, nombre_tipo

AVISO = "Todos los valores están enmascarados: este archivo no contiene datos originales."
MAX_PDF = 1000  # filas de hallazgos en el PDF; el CSV y el JSON traen todos
LOGO = Path(__file__).parent / "web" / "static" / "img" / "logo.webp"
NIVEL = {"HIGH": "Alta", "MEDIUM": "Media", "LOW": "Baja"}  # para personas; el JSON deja el código
REVISION = {"pendiente": "Pendiente", "confirmado": "Confirmado", "falso_positivo": "Falso positivo",
            "sin_falsos": "sin falsos positivos"}


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _fecha(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d-%m-%Y %H:%M")


def filtros_texto(filtros: dict) -> str:
    partes = []
    if filtros.get("riesgo"):
        partes.append(f"riesgo {filtros['riesgo']}")
    if filtros.get("tipo"):
        partes.append(f"tipo {nombre_tipo(filtros['tipo'])}")
    if filtros.get("buscar"):
        partes.append(f"búsqueda «{filtros['buscar']}»")
    if filtros.get("revision"):
        partes.append(f"revisión: {REVISION[filtros['revision']].lower()}")
    return ", ".join(partes) if partes else "Sin filtros: todos los hallazgos"


# --- CSV ------------------------------------------------------------------------------------------

def a_csv(datos: dict) -> bytes:
    filas = ([h["fuente"], h["columna"], h["posicion"], nombre_tipo(h["tipo"]), h["riesgo"], h["confianza"],
              NIVEL.get(h["nivel_confianza"], h["nivel_confianza"]), h["contexto"], h["valor"],
              REVISION[h["revision"]], h["revisado_por"], h["nota"]] for h in datos["hallazgos"])
    return csv_excel(["Fuente", "Columna", "Posición", "Tipo", "Riesgo", "Confianza (%)", "Nivel de confianza",
                      "Contexto", "Dato (enmascarado)", "Revisión", "Revisado por", "Motivo"], filas).encode("utf-8")


# --- JSON -----------------------------------------------------------------------------------------

def a_json(datos: dict, quien, generado_utc: datetime) -> bytes:
    """Pensado para alimentar otro sistema (por ejemplo un DLP)."""
    e = datos["escaneo"]
    documento = {
        "generado_por": "K-Secure",
        "generado": generado_utc.isoformat(timespec="seconds") + "Z",
        "exportado_por": {"usuario": quien.usuario, "nombre": quien.nombre},
        "aviso": AVISO,
        "escaneo": {
            "id": e["id"], "origen_tipo": e["origen_tipo"], "origen_nombre": e["origen_nombre"], "fecha": e["fecha"],
            "total_hallazgos": e["total"], "por_riesgo": e["por_riesgo"], "por_tipo": e["por_tipo"],
            "fuentes": e["fuentes"], "filas_revisadas": e["filas_revisadas"],
            "columnas_sensibles": e["columnas"], "errores": e["errores"], "revision": e["revision"],
        },
        "filtros": {k: (v or None) for k, v in datos["filtros"].items()},
        "hallazgos_exportados": len(datos["hallazgos"]),
        "hallazgos": [{
            "id": h["id"], "fuente": h["fuente"], "columna": h["columna"], "posicion": h["posicion"],
            "tipo": h["tipo"], "tipo_nombre": nombre_tipo(h["tipo"]), "riesgo": h["riesgo"],
            "confianza": h["confianza"], "nivel_confianza": h["nivel_confianza"], "contexto": h["contexto"],
            "valor_enmascarado": h["valor"], "revision": h["revision"], "revisado_por": h["revisado_por"],
            "revisado_en": h["revisado_en"], "nota_revision": h["nota"],
        } for h in datos["hallazgos"]],
    }
    return json.dumps(documento, ensure_ascii=False, indent=2).encode("utf-8")


# --- PDF ------------------------------------------------------------------------------------------

def _plano(texto) -> str:
    """Texto para el PDF: la fuente estándar (Helvetica) cubre el español; lo demás queda como "?"."""
    return ("" if texto is None else str(texto)).encode("cp1252", "replace").decode("cp1252")


def _t(texto) -> str:
    """Lo mismo, escapado para usarlo dentro de un Paragraph (que entiende etiquetas como <b>)."""
    return escape(_plano(texto))


def a_pdf(datos: dict, quien, generado_local: datetime) -> bytes:
    """Reporte en A4. Requiere reportlab (está en requirements.txt)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageTemplate, Paragraph, Spacer,
                                    Table, TableStyle)

    oscuro, texto, gris = colors.HexColor("#04080b"), colors.HexColor("#10242c"), colors.HexColor("#5f7680")
    cian, borde, suave = colors.HexColor("#00b8c8"), colors.HexColor("#d5e6ea"), colors.HexColor("#f2f8f9")
    color_riesgo = {"Restringido": colors.HexColor("#e03131"), "Confidencial": colors.HexColor("#e8590c"),
                    "Interno": colors.HexColor("#1c7ed6"), "Público": colors.HexColor("#2f9e44")}

    def estilo(nombre, **k):
        base = {"fontName": "Helvetica", "fontSize": 9, "leading": 12, "textColor": texto}
        return ParagraphStyle(nombre, **{**base, **k})

    h1 = estilo("h1", fontName="Helvetica-Bold", fontSize=18, leading=22)
    h2 = estilo("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, spaceBefore=14, spaceAfter=6)
    normal, chico = estilo("normal"), estilo("chico", fontSize=8, leading=10, textColor=gris)
    celda, celda_mono = estilo("celda", fontSize=8, leading=10), estilo("mono", fontName="Courier", fontSize=8, leading=10)
    numero = estilo("numero", fontName="Helvetica-Bold", fontSize=20, leading=24)
    estilo_revision = {"pendiente": estilo("rp", fontSize=8, leading=10, textColor=gris),
                       "confirmado": estilo("rc", fontName="Helvetica-Bold", fontSize=8, leading=10),
                       "falso_positivo": estilo("rf", fontSize=8, leading=10, textColor=gris)}

    e, hallazgos, filtros = datos["escaneo"], datos["hallazgos"], datos["filtros"]
    ancho, alto = A4
    margen = 16 * mm
    util = ancho - 2 * margen

    def tabla(filas, anchos, encabezado=True, extra=()):
        t = Table(filas, colWidths=anchos, repeatRows=1 if encabezado else 0)
        reglas = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                  ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                  ("LINEBELOW", (0, 0), (-1, -1), 0.4, borde)]
        if encabezado:
            reglas += [("BACKGROUND", (0, 0), (-1, 0), oscuro), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                       ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                       ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, suave])]
        t.setStyle(TableStyle(reglas + list(extra)))
        return t

    contenido = [NextPageTemplate("resto")]

    # Título y datos del reporte
    origen = "Base de datos" if e["origen_tipo"] == "bd" else "Archivos"
    contenido += [
        Paragraph(_t(e["origen_nombre"]), h1),
        Paragraph(_t(f"{origen} · escaneado el {_fecha(e['fecha'])} · escaneo #{e['id']}"), chico),
        Spacer(1, 10),
    ]
    meta = [
        ("Exportado por", f"{quien.nombre} (@{quien.usuario}) el {generado_local:%d-%m-%Y %H:%M}"),
        ("Filtros", filtros_texto(filtros)),
        ("Qué se revisó", f"{_miles(e['fuentes'])} {'fuente' if e['fuentes'] == 1 else 'fuentes'}"
                          + (f" · {_miles(e['filas_revisadas'])} filas" if e["filas_revisadas"] else "")),
    ]
    contenido.append(tabla([[Paragraph(_t(a), chico), Paragraph(_t(b), normal)] for a, b in meta],
                           [32 * mm, util - 32 * mm], encabezado=False,
                           extra=[("BACKGROUND", (0, 0), (-1, -1), suave), ("LINEBELOW", (0, -1), (-1, -1), 0, suave)]))

    # Resumen por riesgo (todo el escaneo)
    contenido.append(Paragraph("Resumen por riesgo", h2))
    cajas = [[Paragraph(f'<font color="{color_riesgo[r].hexval().replace("0x", "#")}">{_miles(n)}</font>', numero)
              for r, n in e["por_riesgo"].items()],
             [Paragraph(_t(r), estilo(f"r{r}", fontName="Helvetica-Bold")) for r in e["por_riesgo"]]]
    caja = Table(cajas, colWidths=[util / 4] * 4)
    caja.setStyle(TableStyle(
        [("BACKGROUND", (0, 0), (-1, -1), suave), ("TOPPADDING", (0, 0), (-1, 0), 8),
         ("BOTTOMPADDING", (0, -1), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 10)]
        + [("LINEABOVE", (i, 0), (i, 0), 2.5, color_riesgo[r]) for i, r in enumerate(e["por_riesgo"])]
        + [("LINEAFTER", (i, 0), (i, -1), 3, colors.white) for i in range(3)]))
    contenido.append(caja)
    r = e["revision"]
    nota = (f"Total del escaneo: {_miles(e['total'])} hallazgos. Revisión: {_miles(r['confirmado'])} confirmados, "
            f"{_miles(r['falso_positivo'])} falsos positivos y {_miles(r['pendiente'])} pendientes.")
    if any(filtros.values()):
        nota += f" Este reporte incluye {_miles(len(hallazgos))} con los filtros aplicados."
    contenido += [Spacer(1, 4), Paragraph(_t(nota), chico)]

    # Por tipo de dato
    if e["por_tipo"]:
        contenido.append(Paragraph("Por tipo de dato", h2))
        filas = [["Tipo de dato", "Hallazgos", "% del total"]] + [
            [_plano(nombre_tipo(tipo)), _miles(n), f"{round(100 * n / e['total'])} %" if e["total"] else "—"]
            for tipo, n in e["por_tipo"].items()]
        contenido.append(tabla(filas, [util - 60 * mm, 30 * mm, 30 * mm],
                               extra=[("ALIGN", (1, 0), (-1, -1), "RIGHT")]))

    # Columnas sensibles (bases de datos y planillas)
    if e["columnas"]:
        contenido.append(Paragraph("Columnas sensibles", h2))
        filas = [["Columna", "Dato", "Riesgo", "Filas con el dato"]] + [
            [Paragraph(_t(f"{c['fuente']}.{c['columna']}"), celda), _plano(nombre_tipo(c["tipo"])),
             Paragraph(f'<font color="{color_riesgo[c["riesgo"]].hexval().replace("0x", "#")}"><b>{_t(c["riesgo"])}</b></font>', celda),
             f"{_miles(c['filas_con_datos'])} ({c['porcentaje']} %)"] for c in e["columnas"]]
        contenido.append(tabla(filas, [util - 100 * mm, 32 * mm, 30 * mm, 38 * mm],
                               extra=[("ALIGN", (3, 0), (3, -1), "RIGHT")]))

    # Hallazgos
    contenido.append(Paragraph("Hallazgos", h2))
    if len(hallazgos) > MAX_PDF:
        contenido.append(Paragraph(_t(f"Se muestran los primeros {_miles(MAX_PDF)} de {_miles(len(hallazgos))}, del mayor "
                                      "riesgo al menor. El CSV y el JSON traen todos."), chico))
        contenido.append(Spacer(1, 4))
    if hallazgos:
        filas = [["Dónde", "Tipo", "Dato (enmascarado)", "Riesgo", "Confianza", "Revisión"]]
        for h in hallazgos[:MAX_PDF]:
            donde = _t(h["fuente"]) + (f" · columna {_t(h['columna'])}" if h["columna"] else "")
            filas.append([
                Paragraph(f'{donde}<br/><font color="#5f7680">{_t(h["posicion"])}</font>', celda),
                Paragraph(_t(nombre_tipo(h["tipo"])), celda),
                Paragraph(_t(h["valor"]), celda_mono),
                Paragraph(f'<font color="{color_riesgo[h["riesgo"]].hexval().replace("0x", "#")}"><b>{_t(h["riesgo"])}</b></font>', celda),
                f"{h['confianza']} %",
                Paragraph(_t(REVISION[h["revision"]]), estilo_revision[h["revision"]]),
            ])
        contenido.append(tabla(filas, [util - 132 * mm, 24 * mm, 38 * mm, 23 * mm, 19 * mm, 28 * mm],
                               extra=[("ALIGN", (4, 0), (4, -1), "RIGHT")]))
    else:
        contenido.append(Paragraph("Sin hallazgos con estos filtros.", normal))

    if e["errores"]:
        contenido.append(Paragraph("No se pudo revisar", h2))
        contenido += [Paragraph("• " + _t(err), celda) for err in e["errores"]]

    # Encabezado de la primera página (franja oscura con el logo) y de las siguientes
    def primera(c, _doc):
        c.saveState()
        c.setFillColor(oscuro)
        c.rect(0, alto - 30 * mm, ancho, 30 * mm, stroke=0, fill=1)
        c.setFillColor(cian)
        c.rect(0, alto - 30 * mm - 1.2, ancho, 1.2, stroke=0, fill=1)
        try:
            from PIL import Image
            logo = Image.open(LOGO)
            c.drawImage(ImageReader(logo), margen, alto - 24 * mm, height=18 * mm, width=18 * mm * logo.width / logo.height,
                        mask="auto")
        except (OSError, ImportError):  # sin logo el reporte sirve igual
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(margen, alto - 17 * mm, "K-Secure")
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13)
        c.drawRightString(ancho - margen, alto - 14 * mm, "Reporte de escaneo")
        c.setFillColor(cian)
        c.setFont("Helvetica", 8.5)
        c.drawRightString(ancho - margen, alto - 19.5 * mm, "Datos enmascarados")
        c.restoreState()

    def resto(c, _doc):
        c.saveState()
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(gris)
        c.drawString(margen, alto - 10 * mm, _plano(f"K-Secure · Reporte del escaneo #{e['id']} · {e['origen_nombre']}")[:110])
        c.setStrokeColor(borde)
        c.line(margen, alto - 12 * mm, ancho - margen, alto - 12 * mm)
        c.restoreState()

    class ConPie(canvas.Canvas):
        """Agrega "Página X de Y" y el aviso al pie de cada página (se dibuja al final, cuando se sabe Y)."""

        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._paginas = []

        def showPage(self):
            self._paginas.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            for estado in self._paginas:
                self.__dict__.update(estado)
                self.setFont("Helvetica", 7.5)
                self.setFillColor(gris)
                self.drawString(margen, 10 * mm, _plano(AVISO))
                self.drawRightString(ancho - margen, 10 * mm, f"Página {self._pageNumber} de {len(self._paginas)}")
                super().showPage()
            super().save()

    salida = io.BytesIO()
    doc = BaseDocTemplate(salida, pagesize=A4, leftMargin=margen, rightMargin=margen, topMargin=18 * mm,
                          bottomMargin=18 * mm, title=f"K-Secure · {e['origen_nombre']}", author="K-Secure",
                          subject="Reporte de escaneo (datos enmascarados)")
    marco_primera = Frame(margen, 18 * mm, util, alto - 30 * mm - 5 * mm - 18 * mm, id="primera")
    marco_resto = Frame(margen, 18 * mm, util, alto - 18 * mm - 18 * mm, id="resto")
    doc.addPageTemplates([PageTemplate("primera", [marco_primera], onPage=primera),
                          PageTemplate("resto", [marco_resto], onPage=resto)])
    doc.build(contenido, canvasmaker=ConPie)
    return salida.getvalue()
