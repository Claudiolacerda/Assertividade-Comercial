"""O PDF que justifica a projeção: os meses, o método e o que se conclui.

Existe porque o número sozinho não se defende numa reunião. Quando a agência
leva "aumentar 20% da verba traz 2 clientes a mais", a primeira pergunta do
cliente é "de onde você tirou isso" — e a resposta tem de caber numa folha,
com os meses que entraram na conta, a conta em si e, principalmente, o que ela
não autoriza a concluir.

Por isso a ordem das seções é a de uma defesa, não a de um painel: primeiro a
evidência (os meses), depois o método, depois o resultado, e por último os
limites. Quem só lê o começo vê os dados; quem só lê o fim vê as ressalvas.

O PDF é montado no servidor do próprio cliente, a partir das análises que já
estão no banco dele. Nenhum dado sai da máquina para ser desenhado.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .projecao import MINIMO_MESES

VERDE = colors.HexColor("#1f9d55")
TINTA = colors.HexColor("#1a1a1a")
TINTA_2 = colors.HexColor("#444444")
CINZA = colors.HexColor("#767676")
GRADE = colors.HexColor("#dcdcdc")
ALERTA = colors.HexColor("#9a6700")
VERMELHO = colors.HexColor("#b42318")

COR_NIVEL = {"ok": VERDE, "atencao": ALERTA, "critico": VERMELHO, "info": CINZA}
MARCA_NIVEL = {"ok": "+", "atencao": "!", "critico": "!!", "info": "·"}

MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _brl(v: float | None, casas: int = 2) -> str:
    if v is None:
        return "—"
    return "R$ " + f"{v:,.{casas}f}".translate(str.maketrans(",.", ".,"))


def _num(v: float | None, casas: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v:,.{casas}f}".translate(str.maketrans(",.", ".,"))


def _mes_extenso(iso: str | None) -> str:
    if not iso or len(iso) != 7:
        return iso or "—"
    ano, mes = iso.split("-")
    return f"{MESES_PT[int(mes) - 1]}/{ano}"


def _estilos() -> dict:
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
        "corpo": ParagraphStyle(
            "corpo", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=14, textColor=TINTA_2, alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "manchete": ParagraphStyle(
            "manchete", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=12, leading=16, textColor=TINTA,
            borderPadding=(8, 8, 8, 8), backColor=colors.HexColor("#f2f7f3"),
            leftIndent=0, spaceAfter=12,
        ),
        "manchete_fraca": ParagraphStyle(
            "manchete_fraca", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, leading=15, textColor=ALERTA,
            borderPadding=(8, 8, 8, 8), backColor=colors.HexColor("#fdf6e3"),
            leftIndent=0, spaceAfter=12,
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


def _tabela(dados: list[list[str]], larguras: list[float], destacar: int | None = None) -> Table:
    t = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    estilo = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), TINTA),
        ("TEXTCOLOR", (0, 1), (-1, -1), TINTA_2),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, TINTA),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, GRADE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if destacar is not None:
        estilo += [
            ("BACKGROUND", (0, destacar), (-1, destacar), colors.HexColor("#f4f4f4")),
            ("FONT", (0, destacar), (-1, destacar), "Helvetica-Bold", 8.5),
        ]
    t.setStyle(TableStyle(estilo))
    return t


# ------------------------------------------------------------------ #
# As seções
# ------------------------------------------------------------------ #
def tabela_dos_meses(p: dict) -> list[list[str]]:
    """A evidência: um mês por linha, com o CAC calculado na frente.

    É a seção que responde "de onde você tirou isso", e por isso ela vem antes
    de qualquer conclusão. O CAC vai junto porque é a coluna que o cliente
    confere de cabeça.
    """
    linhas = [["Mês", "Investimento", "Leads", "Clientes", "Receita", "CAC"]]
    for ponto in p.get("pontos", []):
        inv = ponto.get("inv") or 0.0
        fec = ponto.get("fec")
        linhas.append([
            _mes_extenso(ponto.get("mes_referencia")),
            _brl(inv),
            _num(ponto.get("leads"), 0) if ponto.get("leads") is not None else "—",
            _num(fec, 0) if fec is not None else "—",
            _brl(ponto.get("rec")) if ponto.get("rec") is not None else "—",
            _brl(inv / fec) if fec else "—",
        ])
    return linhas


def tabela_dos_cenarios(p: dict) -> list[list[str]]:
    alvos = [a for a in p.get("alvos", []) if (p.get("modelos") or {}).get(a["chave"])]
    linhas = [["Cenário", "Investimento"] + [a["rotulo"] for a in alvos]]
    for c in p.get("cenarios", []):
        variacao = c["variacao"]
        rotulo = "hoje" if variacao == 0 else f"{'+' if variacao > 0 else ''}{round(variacao * 100)}%"
        if c.get("fora_do_historico"):
            rotulo += " (nunca testado)"
        linha = [rotulo, _brl(c["investimento"], 0)]
        for a in alvos:
            dado = c.get(a["chave"]) or {}
            valor = dado.get("valor")
            if valor is None:
                linha.append("—")
                continue
            texto = _brl(valor, 0) if a["formato"] == "brl" else _num(valor, 1)
            if dado.get("min") is not None:
                faixa = (
                    f"{_brl(dado['min'], 0)} a {_brl(dado['max'], 0)}"
                    if a["formato"] == "brl"
                    else f"{_num(dado['min'])} a {_num(dado['max'])}"
                )
                texto += f"\n{faixa}"
            linha.append(texto)
        linhas.append(linha)
    return linhas


def texto_do_metodo(p: dict) -> list[str]:
    """Como a conta foi feita, em português, sem esconder a fórmula.

    Um relatório que diz "nossa inteligência calculou" não se defende. Este diz
    o nome do método, a fórmula e o que cada número significa, para que a
    conclusão possa ser contestada por quem entende.
    """
    n = p.get("n_meses", 0)
    if p.get("metodo") == "regra_de_tres":
        return [
            "Com menos de três meses de investimentos diferentes não é possível ajustar uma reta "
            "com margem de erro estimável. Os números deste relatório vêm de uma <b>regra de "
            "três</b> sobre a média dos meses: o resultado total dividido pelo investimento "
            "total, aplicado proporcionalmente a cada cenário.",
            "Ela supõe que cada real novo rende igual ao primeiro, o que raramente acontece na "
            "prática: a partir de certo ponto o público bom se esgota e o custo por resultado "
            f"sobe. Por isso ela é um ponto de partida, não uma previsão. Com {MINIMO_MESES} "
            "meses de investimentos diferentes o sistema passa a medir a tendência de verdade.",
        ]
    return [
        "O método é <b>regressão linear por mínimos quadrados</b>, a técnica padrão para medir "
        "como uma variável acompanha outra. Ela procura a reta "
        "<i>resultado = a + b × investimento</i> que passa o mais perto possível de todos os "
        f"meses ao mesmo tempo, usando os {n} meses da tabela acima como evidência.",
        "O <b>b</b> (inclinação) é o efeito: quanto o resultado muda a cada real a mais. O "
        "<b>a</b> (intercepto) é o que a reta estima sem investimento nenhum, e quando ele é "
        "positivo indica a parte do resultado que não depende do anúncio. O <b>R²</b> diz quanto "
        "da variação do resultado a reta consegue explicar: 100% seria uma reta perfeita, 0% "
        "significa que o investimento não ajuda a explicar o que aconteceu.",
        "A faixa que acompanha cada cenário é o <b>intervalo de previsão a 95%</b>, não o da "
        "média: ele responde \"quantas vendas vou ter nesse mês\", que é a pergunta de quem "
        "decide a verba, e por isso é o mais largo dos dois. Com poucos meses ele fica largo de "
        "propósito, e quando fica maior que a própria previsão o sistema deixa de exibi-lo, "
        "porque uma faixa que não informa nada atrapalha a leitura do número que informa.",
    ]


LIMITES = [
    "<b>Os meses mostram o que andou junto, não o que causou o quê.</b> No mesmo período em que "
    "o investimento mudou, também mudaram oferta, criativo, equipe e época do ano. A reta mede a "
    "associação entre investimento e resultado; atribuir o resultado inteiro ao investimento é "
    "uma decisão de interpretação, não um achado da conta.",
    "<b>A reta não vale fora da faixa já praticada.</b> Cenários marcados como \"nunca testado\" "
    "extrapolam: eles supõem que o próximo real renda como os anteriores, e o mais comum é que "
    "renda menos, porque o público de melhor qualidade é alcançado primeiro.",
    "<b>Poucos meses, margem larga.</b> A confiança desta conta cresce rápido com o número de "
    "meses analisados: cada mês novo com investimento diferente estreita a margem e torna a "
    "inclinação mais firme.",
    "<b>Receita não é lucro.</b> Onde o relatório fala em receita fechada, trata-se do valor dos "
    "contratos, antes do custo de entregar o serviço. A decisão de investir depende da margem, "
    "que este sistema não conhece.",
]


# ------------------------------------------------------------------ #
def gerar_pdf(
    projecao: dict,
    empresa: str = "",
    organizacao: str = "",
    emitido_em: date | None = None,
    destino=None,
) -> bytes:
    """Monta o relatório. Devolve os bytes e, se `destino` vier, também salva."""
    est = _estilos()
    buffer = BytesIO()
    hoje = emitido_em or date.today()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Efeito do investimento em tráfego — {empresa}" if empresa else "Efeito do investimento",
        author=organizacao or "Neriah Data",
    )
    largura = doc.width
    corpo: list = []

    # ---- Capa curta: o que é, de quem é, de quando é ----
    corpo.append(Paragraph("Efeito do investimento em tráfego sobre o resultado comercial", est["titulo"]))
    identificacao = " · ".join(x for x in [empresa, organizacao] if x)
    corpo.append(Paragraph(
        f"{identificacao}{' · ' if identificacao else ''}emitido em "
        f"{hoje.strftime('%d/%m/%Y')} · gerado pelo Neriah Data a partir das análises do período",
        est["subtitulo"],
    ))

    metodo = projecao.get("metodo")
    if metodo == "insuficiente":
        corpo.append(Paragraph("Não há base para projetar", est["secao"]))
        corpo.append(Paragraph(projecao.get("motivo") or "Nenhuma análise com investimento registrado.", est["corpo"]))
        doc.build(corpo)
        return _entregar(buffer, destino)

    n_meses = projecao.get("n_meses", 0)
    modelos = projecao.get("modelos") or {}
    vendas = modelos.get("fec")

    # ---- 1. A evidência ----
    corpo.append(Paragraph("1. Os meses que entraram na conta", est["secao"]))
    corpo.append(Paragraph(
        f"São {n_meses} mês(es) analisado(s) no sistema, usando sempre a última versão de cada "
        "mês. Todos os números abaixo saíram das planilhas enviadas nesses meses; nenhum foi "
        "estimado.",
        est["corpo"],
    ))
    corpo.append(_tabela(
        tabela_dos_meses(projecao),
        [largura * p for p in (0.20, 0.18, 0.12, 0.13, 0.19, 0.18)],
    ))
    faixa = projecao.get("faixa_observada") or {}
    if faixa:
        corpo.append(Spacer(1, 6))
        corpo.append(Paragraph(
            f"O investimento mensal variou entre {_brl(faixa.get('min'))} e "
            f"{_brl(faixa.get('max'))}. É dentro dessa faixa que as conclusões se apoiam em fatos.",
            est["nota"],
        ))

    # ---- 2. O método ----
    corpo.append(Paragraph("2. Como a conta foi feita", est["secao"]))
    for paragrafo in texto_do_metodo(projecao):
        corpo.append(Paragraph(paragrafo, est["corpo"]))

    # ---- 3. O que a conta deu ----
    corpo.append(Paragraph("3. O que a conta deu", est["secao"]))
    # A manchete vem do motor, com o nível junto, exatamente como na tela: o
    # documento não pode afirmar em letra grande o que a tela já qualificou.
    # Quando a reta é fraca, ela muda de texto E de cor de fundo.
    manchete = projecao.get("manchete")
    if manchete:
        estilo = est["manchete"] if manchete.get("nivel") == "ok" else est["manchete_fraca"]
        corpo.append(Paragraph(manchete["texto"], estilo))

    # O resumo do período é soma contra soma, sem modelo no meio: é a frase que
    # continua de pé quando a tendência não se sustenta, e a que o cliente lê
    # em voz alta na reunião.
    resumo = projecao.get("resumo")
    if resumo:
        corpo.append(Paragraph(f"<b>{resumo['texto']}</b>", est["corpo"]))
        corpo.append(Paragraph(resumo["rodape"], est["nota"]))
        corpo.append(Spacer(1, 6))
    coef = [["Resultado", "Efeito por R$ 1.000", "Base (a)", "R²"]]
    for alvo in projecao.get("alvos", []):
        m = modelos.get(alvo["chave"])
        if not m:
            continue
        coef.append([
            alvo["rotulo"],
            _brl(m["por_mil"], 2) if alvo["formato"] == "brl" else _num(m["por_mil"], 2),
            _brl(m["intercepto"], 2) if alvo["formato"] == "brl" else _num(m["intercepto"], 2),
            "—" if m.get("r2") is None else f"{m['r2'] * 100:.0f}%",
        ])
    if len(coef) > 1:
        corpo.append(_tabela(coef, [largura * p for p in (0.34, 0.24, 0.22, 0.20)]))
        corpo.append(Spacer(1, 6))
        corpo.append(Paragraph(
            "\"Base\" é o que a reta estima com investimento zero: quando é positiva, indica a "
            "parte do resultado que acontece sem depender do anúncio.",
            est["nota"],
        ))

    # ---- 4. A leitura ----
    leitura = projecao.get("leitura") or []
    if leitura:
        corpo.append(Paragraph("4. O que isso quer dizer", est["secao"]))
        for item in leitura:
            cor = COR_NIVEL.get(item.get("nivel"), CINZA)
            marca = MARCA_NIVEL.get(item.get("nivel"), "·")
            corpo.append(Paragraph(
                f'<font color="{cor.hexval()}"><b>{marca}</b></font>&nbsp;&nbsp;{item["texto"]}',
                est["leitura"],
            ))

    # ---- 5. Cenários ----
    # Sem quebra de página forçada: ela deixava meia folha em branco quando a
    # leitura era curta, e uma página vazia num relatório que o cliente recebe
    # parece defeito. O KeepTogether abaixo é que impede a tabela de rachar.
    corpo.append(Spacer(1, 4))
    corpo.append(Paragraph("5. Cenários de investimento", est["secao"]))
    corpo.append(Paragraph(
        "Cada linha aplica a conta acima a um investimento diferente, a partir do praticado no "
        "último mês. As linhas marcadas como \"nunca testado\" estão fora da faixa já praticada.",
        est["corpo"],
    ))
    cenarios = tabela_dos_cenarios(projecao)
    atual = next(
        (i for i, c in enumerate(projecao.get("cenarios", []), start=1) if c["variacao"] == 0),
        None,
    )
    colunas = len(cenarios[0])
    resto = (1 - 0.22 - 0.20) / max(1, colunas - 2)
    corpo.append(KeepTogether(
        _tabela(cenarios, [largura * p for p in [0.22, 0.20] + [resto] * (colunas - 2)], destacar=atual)
    ))

    for aviso in projecao.get("avisos", []):
        corpo.append(Spacer(1, 4))
        corpo.append(Paragraph(aviso, est["nota"]))

    # ---- 6. Limites ----
    corpo.append(Paragraph("6. O que este relatório não autoriza a concluir", est["secao"]))
    for limite in LIMITES:
        corpo.append(Paragraph(limite, est["corpo"]))

    corpo.append(Spacer(1, 10))
    corpo.append(KeepTogether(Paragraph(
        f"Relatório gerado automaticamente pelo Neriah Data em {hoje.strftime('%d/%m/%Y')}, a "
        f"partir de {n_meses} mês(es) de análise armazenados no sistema. Os cálculos são "
        "reproduzíveis: mesma base, mesmo resultado.",
        est["nota"],
    )))

    doc.build(corpo, onFirstPage=_rodape, onLaterPages=_rodape)
    return _entregar(buffer, destino)


def _rodape(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(18 * mm, 10 * mm, "Neriah Data · efeito do investimento em tráfego")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"página {doc.page}")
    canvas.restoreState()


def _entregar(buffer: BytesIO, destino) -> bytes:
    conteudo = buffer.getvalue()
    if destino:
        from pathlib import Path

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
    return conteudo
