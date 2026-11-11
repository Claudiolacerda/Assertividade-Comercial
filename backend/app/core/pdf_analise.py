"""O relatório do mês em PDF: o que aconteceu, por que, e o que fazer.

A planilha entregue tem tudo, e é exatamente esse o problema dela numa
reunião: vinte abas não se apresentam. O PDF é o recorte que cabe numa mesa —
os números do mês, o que eles dizem, o funil, quem fechou e o que a base de
dados ainda esconde.

A ordem é a da conversa que o gestor tem com o cliente, não a do banco de
dados: primeiro o resultado, depois a explicação, depois a lista nominal, e
por último as ressalvas de quem produziu o número. Quem lê só a primeira
página sai sabendo como foi o mês.

Reaproveita os estilos do relatório de projeção para os dois documentos
saírem com a mesma cara; o que muda é o recorte.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table

from .pdf_analise_estilo import COR_NIVEL, MARCA_NIVEL, estilos, rodape, tabela_simples
from .texto import br, fmt

# Blocos de indicador que entram no PDF, na ordem em que se fala deles. Os
# demais (qualidade, base tratada) ficam na planilha: aqui o critério é caber
# numa reunião, não ser completo.
BLOCOS_NO_PDF = 4

# Colunas que fazem sentido imprimir de cada tabela. Uma tabela de 26 colunas
# não cabe em A4, e cortar na largura esconde justamente o que está à direita.
COLUNAS_POR_TABELA = {
    "por_responsavel": ["Responsável", "Reuniões agendadas", "Reuniões realizadas", "Fechados",
                        "Assertividade (%)"],
    "por_marcacao": ["Marcação no nome", "Reuniões agendadas", "Fechados", "Assertividade (%)"],
    "por_semana": ["Semana", "Reuniões agendadas", "Reuniões realizadas", "Fechados",
                   "Assertividade (%)"],
    "motivos_perda": ["Motivo da perda", "Quantidade", "% das perdas (%)"],
    "fechamentos": ["Cliente", "Marcação", "Status na planilha", "Data da reunião", "Responsável"],
}

LIMITE_LINHAS = 18
# Quantas linhas sobem junto com o título para ele não ficar sozinho no pé da folha.
LINHAS_COM_O_TITULO = 4


def _valor(kpi: dict) -> str:
    """O mesmo texto que está na tela, quando o motor já o gravou.

    O painel lê `texto` do payload; recalcular aqui é a forma mais fácil de o
    documento e a tela discordarem no arredondamento.
    """
    texto = kpi.get("texto")
    if texto:
        return _sem_emoji(texto)
    return _numero(kpi["valor"], kpi["formato"])


def gerar_pdf(
    resultado: dict,
    empresa: str = "",
    organizacao: str = "",
    versao: int | None = None,
    emitido_em: date | None = None,
    destino=None,
) -> bytes:
    """Monta o relatório do mês. `resultado` é o payload gravado da análise."""
    est = estilos()
    buffer = BytesIO()
    hoje = emitido_em or date.today()
    nome_mes = resultado.get("nome_mes") or resultado.get("mes_referencia") or ""
    kpis = resultado.get("kpis") or {}
    tabelas = resultado.get("tabelas") or {}

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Análise comercial — {empresa} — {nome_mes}".strip(" —"),
        author=organizacao or "Neriah Data",
    )
    largura = doc.width
    corpo: list = []

    # ---- Capa curta ----
    corpo.append(Paragraph(f"Análise comercial · {nome_mes}", est["titulo"]))
    identificacao = " · ".join(x for x in [empresa, organizacao] if x)
    versao_txt = f" · versão {versao}" if versao else ""
    corpo.append(Paragraph(
        f"{identificacao}{versao_txt} · emitido em {hoje.strftime('%d/%m/%Y')} · "
        "gerado pelo Neriah Data",
        est["subtitulo"],
    ))

    # ---- 1. Os números do mês ----
    corpo.append(Paragraph("1. Os números do mês", est["secao"]))
    for bloco in (resultado.get("blocos") or [])[:BLOCOS_NO_PDF]:
        # No payload gravado cada bloco é {"titulo", "chaves"}; em memória é uma
        # tupla. Desempacotar a tupla direto fazia a seção sair VAZIA quando o
        # PDF vinha do banco — em silêncio, porque iterar o dicionário devolve
        # as chaves e a lista de indicadores virava a palavra "chaves".
        if isinstance(bloco, dict):
            titulo, chaves = bloco.get("titulo", ""), bloco.get("chaves", [])
        else:
            titulo, chaves = bloco
        presentes = [k for k in chaves if k in kpis]
        if not presentes:
            continue
        linhas = [["Indicador", "Valor", "Meta", "Situação"]]
        for chave in presentes:
            k = kpis[chave]
            meta = "—"
            if k.get("meta_tipo"):
                meta = ("mín. " if k["meta_tipo"] == "min" else "máx. ") + br(
                    fmt(k["meta_valor"], k["formato"])
                )
            linhas.append([_sem_emoji(k["rotulo"]), _valor(k), meta, _situacao(k)])
        corpo.append(KeepTogether([
            Paragraph(_titulo_de_bloco(titulo), est["subsecao"]),
            tabela_simples(linhas, [largura * p for p in (0.46, 0.17, 0.17, 0.20)]),
            Spacer(1, 10),
        ]))

    # ---- 2. O que os números dizem ----
    diagnostico = resultado.get("diagnostico") or []
    if diagnostico:
        corpo.append(Paragraph("2. O que os números dizem", est["secao"]))
        for item in diagnostico[:14]:
            nivel = _nivel(item.get("Nível", ""))
            corpo.append(Paragraph(
                f'<font color="{COR_NIVEL[nivel].hexval()}"><b>{MARCA_NIVEL[nivel]}</b></font>'
                f'&nbsp;&nbsp;{_sem_emoji(item.get("Diagnóstico", ""))}',
                est["leitura"],
            ))

    # ---- 3. O funil ----
    funil = tabelas.get("funil_topo") or tabelas.get("funil") or []
    if funil:
        corpo.append(Paragraph("3. O funil do mês", est["secao"]))
        linhas = [["Etapa", "Quantidade", "Conversão da etapa anterior"]]
        for passo in funil:
            conversao = passo.get("Conversão da etapa anterior (%)")
            linhas.append([
                passo.get("Etapa", ""),
                _numero(float(passo.get("Quantidade") or 0), "int"),
                "—" if conversao in (None, 0) else br(fmt(float(conversao), "pct")),
            ])
        corpo.append(tabela_simples(linhas, [largura * p for p in (0.52, 0.24, 0.24)]))

    # ---- 4. Quem fechou ----
    # Sem quebra de página forçada: ela deixava meia folha em branco quando o
    # funil terminava no alto da página seguinte, e folha vazia num relatório
    # que o cliente recebe parece defeito. O KeepTogether abaixo é que impede
    # um título ficar sozinho no pé da página.
    for chave, titulo, explicacao in [
        ("fechamentos", "4. Todos os fechamentos do mês",
         "Cada linha contada como venda, com o texto que estava na planilha."),
        ("por_marcacao", "5. Por marcação no nome",
         "Etiqueta depois do hífen no nome do cliente: parceiro, indicação ou vendedor externo."),
        ("por_responsavel", "6. Por responsável", None),
        ("por_semana", "7. Semana a semana", None),
        ("motivos_perda", "8. Por que perdemos", None),
    ]:
        linhas = tabelas.get(chave) or []
        if not linhas:
            continue
        cabeca = [Paragraph(titulo, est["secao"])]
        if explicacao:
            cabeca.append(Paragraph(explicacao, est["corpo"]))
        # O corte é decidido aqui, uma vez, e não dentro de cada pedaço: quando
        # a tabela era partida em duas para o título não ficar sozinho no pé da
        # página, cada metade aplicava o limite por conta própria e o aviso
        # saía contando as linhas da metade, não as da tabela.
        mostradas = linhas[:LIMITE_LINHAS]
        corpo.append(KeepTogether(
            cabeca + [_tabela_de(mostradas[:LINHAS_COM_O_TITULO], chave, largura)]
        ))
        if len(mostradas) > LINHAS_COM_O_TITULO:
            corpo.append(
                _tabela_de(mostradas[LINHAS_COM_O_TITULO:], chave, largura, cabecalho=False)
            )
        if len(linhas) > LIMITE_LINHAS:
            corpo.append(Paragraph(
                f"Mostrando {LIMITE_LINHAS} de {len(linhas)} linhas; a lista inteira está na "
                "planilha em Excel.",
                est["nota"],
            ))
        corpo.append(Spacer(1, 8))

    # ---- Ressalvas ----
    avisos = resultado.get("avisos") or []
    if avisos:
        corpo.append(Paragraph("Como estes números foram lidos", est["secao"]))
        for aviso in avisos:
            corpo.append(Paragraph(f"• {aviso}", est["nota"]))

    cobertura = resultado.get("cobertura") or {}
    faltando = [c["rotulo"] for c in cobertura.get("campos", []) if not c.get("encontrado")]
    if faltando:
        corpo.append(Spacer(1, 6))
        corpo.append(Paragraph(
            f"A planilha deste mês tem {cobertura.get('encontrados')} de "
            f"{cobertura.get('total')} campos que o sistema entende. Faltam: "
            f"{', '.join(faltando)}. Cada um deles liga indicadores que hoje não aparecem.",
            est["nota"],
        ))

    doc.build(corpo, onFirstPage=rodape, onLaterPages=rodape)
    conteudo = buffer.getvalue()
    if destino:
        from pathlib import Path

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
    return conteudo


# As fontes embutidas do PDF (Helvetica) não têm emoji: cada um vira um
# quadrado preto. Eles existem na tela para dar peso visual, e no documento o
# peso vem do negrito e da cor.
_EMOJI = str.maketrans({c: None for c in "⭐🔴🔥⚠️✅ℹ️📈📉"})


# O bloco vem em caixa alta do motor ("COMERCIAL — TODAS AS ORIGENS"); .title()
# sozinho levantava também as palavras de ligação ("Todas As Origens").
_MINUSCULAS = {"a", "as", "o", "os", "da", "das", "de", "do", "dos", "e", "em", "no", "nos", "na", "nas", "por", "para", "com"}


def _titulo_de_bloco(titulo: str) -> str:
    palavras = titulo.title().split()
    return " ".join(
        p.lower() if i and p.lower() in _MINUSCULAS else p for i, p in enumerate(palavras)
    )


def _sem_emoji(texto: str) -> str:
    return str(texto).translate(_EMOJI).strip()


def _situacao(kpi: dict) -> str:
    """Dentro, fora, ou a terceira resposta — a mesma da tela."""
    veredito = (kpi.get("faixa") or {}).get("veredito")
    if veredito in ("indistinguivel", "amostra_pequena"):
        return "ainda não dá para dizer"
    if kpi.get("meta_tipo") is None:
        return "—"
    return "dentro da meta" if kpi.get("dentro_da_meta") else "fora da meta"


def _nivel(texto: str) -> str:
    if "🔴" in texto:
        return "critico"
    if "⚠️" in texto or "🔥" in texto:
        return "atencao"
    if "✅" in texto:
        return "ok"
    return "info"


def _tabela_de(
    linhas: list[dict], chave: str, largura: float, cabecalho: bool = True
) -> Table:
    """Monta a tabela recortada nas colunas que cabem em A4.

    `cabecalho=False` continua uma tabela já começada na página anterior: as
    primeiras linhas vão junto com o título (para ele não ficar sozinho no pé
    da folha) e o resto flui.
    """
    colunas = [c for c in COLUNAS_POR_TABELA.get(chave, []) if c in linhas[0]]
    if not colunas:
        colunas = list(linhas[0])[:5]
    dados = [colunas] if cabecalho else []
    for linha in linhas:
        dados.append([_celula(linha.get(c)) for c in colunas])
    larguras = [largura * (0.34 if i == 0 else 0.66 / max(1, len(colunas) - 1))
                for i in range(len(colunas))]
    return tabela_simples(dados, larguras, cabecalho=cabecalho)


def _celula(valor) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float):
        # Taxa guardada como fração (0,257) e contagem (9,0) no mesmo lugar: o
        # nome da coluna é que diz qual é qual, e aqui só o tamanho ajuda.
        return _numero(valor, "pct" if 0 < abs(valor) < 1 else "int")
    return _sem_emoji(valor) if isinstance(valor, str) else str(valor)


def _numero(valor: float, formato: str) -> str:
    """Formata com a pontuação brasileira também quando não há R$ nem %.

    `br()` só troca os separadores dentro de R$, % e x, então "144,456"
    impressões saía com a vírgula de milhar do inglês.
    """
    texto = fmt(valor, formato)
    if "%" in texto or "R$" in texto or texto.endswith("x"):
        return br(texto)  # br() sabe trocar os separadores dentro desses
    if formato == "num":
        return texto  # fmt() já devolve "1,8"; traduzir de novo faria "1.8"
    return texto.translate(str.maketrans(",.", ".,"))
