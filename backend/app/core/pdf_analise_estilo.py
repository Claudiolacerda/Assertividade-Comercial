"""Estilos e peças do relatório do mês em PDF.

Separado do documento para o próximo relatório poder nascer com a mesma cara:
quem recebe dois PDFs do sistema na mesma semana precisa reconhecer de onde
vieram. O relatório da projeção (`pdf_projecao.py`) ainda tem os estilos dele;
unificar os dois é mudança para quando o segundo precisar mexer neles, e não
agora, que mexeria num documento que já está no ar sem necessidade.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle

VERDE = colors.HexColor("#1f9d55")
TINTA = colors.HexColor("#1a1a1a")
TINTA_2 = colors.HexColor("#444444")
CINZA = colors.HexColor("#767676")
GRADE = colors.HexColor("#dcdcdc")
ALERTA = colors.HexColor("#9a6700")
VERMELHO = colors.HexColor("#b42318")

COR_NIVEL = {"ok": VERDE, "atencao": ALERTA, "critico": VERMELHO, "info": CINZA}
MARCA_NIVEL = {"ok": "+", "atencao": "!", "critico": "!!", "info": "·"}


def estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=17, leading=21, textColor=TINTA, alignment=0, spaceAfter=2,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=13, textColor=CINZA, spaceAfter=14,
        ),
        "secao": ParagraphStyle(
            "secao", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=TINTA, spaceBefore=14, spaceAfter=6,
        ),
        "subsecao": ParagraphStyle(
            "subsecao", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=CINZA, spaceBefore=4, spaceAfter=4,
        ),
        "corpo": ParagraphStyle(
            "corpo", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=14, textColor=TINTA_2, alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "manchete": ParagraphStyle(
            "manchete", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=12, leading=16, textColor=TINTA,
            borderPadding=(8, 8, 8, 8), backColor=colors.HexColor("#f2f7f3"), spaceAfter=12,
        ),
        "manchete_fraca": ParagraphStyle(
            "manchete_fraca", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, leading=15, textColor=ALERTA,
            borderPadding=(8, 8, 8, 8), backColor=colors.HexColor("#fdf6e3"), spaceAfter=12,
        ),
        "leitura": ParagraphStyle(
            "leitura", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=13.5, textColor=TINTA_2, leftIndent=14,
            firstLineIndent=-14, spaceAfter=7,
        ),
        "nota": ParagraphStyle(
            "nota", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=11, textColor=CINZA, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
    }


def tabela_simples(
    dados: list[list[str]],
    larguras: list[float],
    destacar: int | None = None,
    cabecalho: bool = True,
) -> Table:
    """Tabela do relatório.

    `cabecalho=False` é a continuação de uma tabela cujo cabeçalho ficou na
    página anterior: sem ele, a primeira linha de dados sairia em negrito e
    com a régua grossa, como se fosse título, e o leitor perderia um cliente.
    """
    t = Table(dados, colWidths=larguras, repeatRows=1 if cabecalho else 0, hAlign="LEFT")
    estilo = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), TINTA_2),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, GRADE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if cabecalho:
        estilo += [
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
            ("TEXTCOLOR", (0, 0), (-1, 0), TINTA),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, TINTA),
        ]
    if destacar is not None:
        estilo += [
            ("BACKGROUND", (0, destacar), (-1, destacar), colors.HexColor("#f4f4f4")),
            ("FONT", (0, destacar), (-1, destacar), "Helvetica-Bold", 8.5),
        ]
    t.setStyle(TableStyle(estilo))
    return t


def rodape(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(18 * mm, 10 * mm, "Neriah Data")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"página {doc.page}")
    canvas.restoreState()
