"""Planilha-modelo Neriah.

O gargalo real não é o motor: é a coluna que não existe na planilha do cliente.
Este módulo gera o arquivo que resolve isso na origem — com os nomes que o
sistema reconhece, lista suspensa nas etapas (acaba com "Nao fechou" convivendo
com "Perdeu") e uma aba explicando o que cada coluna destrava.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .config_analise import CAMPOS_REUNIOES_INFO, ETAPAS_SUGERIDAS

VERDE = "099938"
VERDE_CLARO = "E8FBEF"
ESCURO = "0A1412"
CINZA = "F1F4F3"

F_TIT = Font(name="Arial", bold=True, size=15, color=ESCURO)
F_SUB = Font(name="Arial", italic=True, size=9.5, color="5A6B67")
F_CAB = Font(name="Arial", bold=True, color="FFFFFF", size=10)
F_TXT = Font(name="Arial", size=10)
F_EX = Font(name="Arial", size=10, italic=True, color="7D8A87")
F_SEC = Font(name="Arial", bold=True, size=11, color=VERDE)

FILL_CAB = PatternFill("solid", fgColor=VERDE)
FILL_OBR = PatternFill("solid", fgColor=VERDE_CLARO)
FILL_ZEBRA = PatternFill("solid", fgColor=CINZA)
BORDA = Border(*(Side(style="thin", color="D5DEDB"),) * 4)

# Ordem das colunas na planilha: obrigatórias primeiro, depois por impacto.
PESO = {"obrigatorio": 0, "alto": 1, "medio": 2, "baixo": 3}
ORDEM = sorted(CAMPOS_REUNIOES_INFO.items(), key=lambda kv: PESO[kv[1]["impacto"]])

EXEMPLOS = [
    {
        "cliente": "Padaria do Zé", "status": "Fechado", "data_reuniao": "05/03/2026",
        "valor": "2500,00", "campanha": "[GT] [WPP] [VENDAS]", "origem": "Facebook Ads",
        "motivo_perda": "", "responsavel": "Marina", "data_agendamento": "03/03/2026",
        "data_fechamento": "05/03/2026", "observacoes": "Fechou na hora, indicou um vizinho",
        "produto": "Plano ME", "data_lead": "01/03/2026",
    },
    {
        "cliente": "Mercado Sul", "status": "Perdido", "data_reuniao": "06/03/2026",
        "valor": "1800,00", "campanha": "[GT] [WPP] [VENDAS]", "origem": "Facebook Ads",
        "motivo_perda": "Achou caro", "responsavel": "Marina", "data_agendamento": "04/03/2026",
        "data_fechamento": "", "observacoes": "Comparou com a contabilidade atual e achou caro",
        "produto": "Plano ME", "data_lead": "02/03/2026",
    },
    {
        "cliente": "Bar do João", "status": "Follow Up", "data_reuniao": "07/03/2026",
        "valor": "3200,00", "campanha": "[INFO] [FORM] [LEAD]", "origem": "Instagram Ads",
        "motivo_perda": "", "responsavel": "Rafael", "data_agendamento": "05/03/2026",
        "data_fechamento": "", "observacoes": "Pediu o contrato para analisar, retorna dia 12",
        "produto": "Plano MEI", "data_lead": "04/03/2026",
    },
]


def _aba_reunioes(wb: Workbook) -> None:
    ws = wb.create_sheet("Reuniões", 0)
    ws["A1"] = "Controle Comercial — modelo Neriah Data"
    ws["A1"].font = F_TIT
    ws["A2"] = (
        "Uma linha por cliente. Preencha da coluna A para a direita: as colunas em verde são "
        "obrigatórias, as demais destravam indicadores (veja a aba 'Como preencher')."
    )
    ws["A2"].font = F_SUB
    ws.sheet_view.showGridLines = False

    linha_cab = 4
    for i, (campo, info) in enumerate(ORDEM, start=1):
        cel = ws.cell(linha_cab, i, info["rotulo"])
        cel.font, cel.fill, cel.border = F_CAB, FILL_CAB, BORDA
        cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = max(14, min(34, len(info["rotulo"]) + 9))
    ws.row_dimensions[linha_cab].height = 30

    # exemplos em itálico cinza — para apagar depois de entender o formato
    for j, ex in enumerate(EXEMPLOS):
        for i, (campo, _) in enumerate(ORDEM, start=1):
            cel = ws.cell(linha_cab + 1 + j, i, ex.get(campo, ""))
            cel.font, cel.border = F_EX, BORDA
            if j % 2:
                cel.fill = FILL_ZEBRA

    primeira_livre = linha_cab + 1 + len(EXEMPLOS)
    ultima = primeira_livre + 400
    for r in range(primeira_livre, ultima):
        for i in range(1, len(ORDEM) + 1):
            ws.cell(r, i).border = BORDA
            ws.cell(r, i).font = F_TXT

    # Lista suspensa na etapa: o campo que mais bagunça quando é texto livre
    col_status = next(i for i, (c, _) in enumerate(ORDEM, start=1) if c == "status")
    letra = get_column_letter(col_status)
    dv = DataValidation(
        type="list",
        formula1='"' + ",".join(ETAPAS_SUGERIDAS) + '"',
        allow_blank=True,
        showDropDown=False,  # False = mostra a setinha (a flag é "esconder")
    )
    dv.error = "Escolha uma das etapas da lista."
    dv.errorTitle = "Etapa inválida"
    dv.prompt = "Selecione a etapa atual do cliente."
    dv.promptTitle = "Etapa do Funil"
    ws.add_data_validation(dv)
    dv.add(f"{letra}{linha_cab + 1}:{letra}{ultima}")

    # marca visualmente as obrigatórias
    for i, (campo, info) in enumerate(ORDEM, start=1):
        if info["impacto"] == "obrigatorio":
            for r in range(primeira_livre, primeira_livre + 40):
                ws.cell(r, i).fill = FILL_OBR

    ws.freeze_panes = f"A{linha_cab + 1}"
    ws.auto_filter.ref = f"A{linha_cab}:{get_column_letter(len(ORDEM))}{ultima}"
    ws.cell(ultima + 2, 1, "As três primeiras linhas são exemplos — apague antes de usar.").font = F_SUB


# Nome da aba e dos rótulos: o parser procura por estes textos exatos, então
# mudar um aqui obriga a mudar o espelho em `leitura.py`. A lista é a única
# fonte dos dois lados — o modelo escreve a partir dela e o leitor lê por ela.
ABA_METAS = "Metas"
METAS_DA_PLANILHA = [
    ("receita_mes", "Faturamento esperado no mês (R$)", "brl",
     "Soma do valor dos contratos que você espera fechar no mês.", 60000),
    ("fechamentos_mes", "Clientes fechados esperados no mês", "int",
     "Quantos contratos novos o mês precisa entregar.", 12),
    ("leads_mes", "Leads esperados no mês", "int",
     "Quantas conversas o tráfego precisa gerar para sustentar essa meta.", 90),
    ("cac_max", "Teto de custo por cliente (CAC) (R$)", "brl",
     "O máximo que você aceita pagar em anúncio por cliente fechado.", 800),
    ("cpl_max", "Teto de custo por lead (R$)", "brl",
     "O máximo que você aceita pagar por conversa gerada.", 40),
    ("assertividade", "Assertividade esperada (%)", "pct",
     "De cada 100 reuniões realizadas, quantas devem fechar.", 0.25),
    ("comparecimento", "Comparecimento esperado (%)", "pct",
     "De cada 100 reuniões marcadas, quantas devem acontecer.", 0.70),
    ("win_rate", "Win rate esperado (%)", "pct",
     "Entre quem já decidiu (fechou ou perdeu), quantos devem fechar.", 0.40),
    ("lead_para_reuniao", "Lead que vira reunião (%)", "pct",
     "De cada 100 leads, quantos devem virar reunião agendada.", 0.20),
    ("ctr", "CTR mínimo no link (%)", "pct",
     "Proporção de quem vê o anúncio e clica.", 0.010),
    ("roas", "ROAS esperado (x)", "x",
     "Quantos reais de receita para cada real investido.", 3.0),
]


def _aba_metas(wb: Workbook) -> None:
    """A aba que o JET lê para dar a nota do mês.

    Em branco não é erro: cada meta vazia simplesmente sai do Score, e o JET
    renormaliza os pesos. Preencher só o que você de fato combinou dá uma nota
    mais honesta do que inventar número para todas as linhas.
    """
    ws = wb.create_sheet(ABA_METAS, 1)
    ws["A1"] = "Metas do mês"
    ws["A1"].font = F_TIT
    ws["A2"] = (
        "Preencha a coluna B com o que foi combinado para o mês. O JET usa estes números para dar "
        "a nota da operação e apontar onde ela ficou devendo. Linha em branco sai do cálculo — "
        "preencha só o que você realmente acompanha."
    )
    ws["A2"].font = F_SUB
    ws.sheet_view.showGridLines = False

    lin = 4
    for i, h in enumerate(["Meta", "Valor", "O que é"], 1):
        c = ws.cell(lin, i, h)
        c.font, c.fill, c.border = F_CAB, FILL_CAB, BORDA
        c.alignment = Alignment(horizontal="center", vertical="center")
    lin += 1

    for j, (_chave, rotulo, formato, explicacao, exemplo) in enumerate(METAS_DA_PLANILHA):
        rot = ws.cell(lin, 1, rotulo)
        val = ws.cell(lin, 2, exemplo)
        exp = ws.cell(lin, 3, explicacao)
        for cel in (rot, val, exp):
            cel.font, cel.border = F_TXT, BORDA
            cel.alignment = Alignment(wrap_text=True, vertical="center")
        val.fill = FILL_OBR
        val.alignment = Alignment(horizontal="right", vertical="center")
        val.number_format = {
            "brl": 'R$ #,##0.00', "int": "0", "pct": "0.0%", "x": '0.0"x"',
        }[formato]
        if j % 2:
            rot.fill = exp.fill = FILL_ZEBRA
        ws.row_dimensions[lin].height = 26
        lin += 1

    for letra, w in zip("ABC", [38, 18, 64]):
        ws.column_dimensions[letra].width = w

    lin += 1
    ws.cell(lin, 1, "Os números acima são exemplos — troque pelos seus.").font = F_SUB
    lin += 2
    ws.cell(lin, 1, "Como o JET usa isto").font = F_SEC
    lin += 1
    for regra in [
        "Resultado (peso 40): faturamento e clientes fechados contra o que foi combinado.",
        "Eficiência (peso 30): CAC, custo por lead e volume de leads.",
        "Assertividade (peso 30): as taxas de conversão do funil.",
        "Meta em branco não derruba a nota: o peso dela é redistribuído entre as outras.",
    ]:
        cel = ws.cell(lin, 1, regra)
        cel.font = F_TXT
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=lin, start_column=1, end_row=lin, end_column=3)
        lin += 1


def _aba_instrucoes(wb: Workbook) -> None:
    ws = wb.create_sheet("Como preencher")
    ws["A1"] = "O que cada coluna destrava"
    ws["A1"].font = F_TIT
    ws["A2"] = (
        "Você não precisa preencher tudo para começar. Com as duas obrigatórias já sai análise; "
        "cada coluna a mais acende um indicador novo."
    )
    ws["A2"].font = F_SUB
    ws.sheet_view.showGridLines = False

    lin = 4
    for i, h in enumerate(["Coluna", "Importância", "O que destrava", "Exemplo"], 1):
        c = ws.cell(lin, i, h)
        c.font, c.fill, c.border = F_CAB, FILL_CAB, BORDA
        c.alignment = Alignment(horizontal="center", vertical="center")
    lin += 1

    nomes = {
        "obrigatorio": "OBRIGATÓRIA",
        "alto": "Alto impacto",
        "medio": "Médio impacto",
        "baixo": "Complementar",
    }
    for j, (campo, info) in enumerate(ORDEM):
        valores = [info["rotulo"], nomes[info["impacto"]], info["destrava"], info["exemplo"]]
        for i, v in enumerate(valores, 1):
            cel = ws.cell(lin, i, v)
            cel.font, cel.border = F_TXT, BORDA
            cel.alignment = Alignment(wrap_text=True, vertical="top")
            if info["impacto"] == "obrigatorio":
                cel.fill = FILL_OBR
            elif j % 2:
                cel.fill = FILL_ZEBRA
        ws.row_dimensions[lin].height = 28
        lin += 1

    for letra, w in zip("ABCD", [30, 17, 62, 34]):
        ws.column_dimensions[letra].width = w

    lin += 2
    ws.cell(lin, 1, "Três regras que valem mais que qualquer coluna extra").font = F_SEC
    lin += 1
    for regra in [
        "1. Registre as perdas. Sem a etapa 'Perdido', a assertividade fica inflada e ninguém percebe.",
        "2. Use a lista de etapas. Texto livre vira 'Nao fechou' e 'Perdeu' na mesma planilha.",
        "3. Escreva a observação. É dela que saem as objeções e a temperatura do pipeline.",
    ]:
        cel = ws.cell(lin, 1, regra)
        cel.font = F_TXT
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=lin, start_column=1, end_row=lin, end_column=4)
        ws.row_dimensions[lin].height = 20
        lin += 1

    lin += 1
    ws.cell(lin, 1, "Pode renomear as colunas?").font = F_SEC
    lin += 1
    cel = ws.cell(
        lin, 1,
        "Pode. O Neriah reconhece vários nomes para o mesmo campo — 'Quem fez', 'Vendedor' e "
        "'Closer' chegam todos em Responsável. Este modelo só usa os nomes mais claros. O que não "
        "dá é faltar a coluna.",
    )
    cel.font, cel.alignment = F_TXT, Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=lin, start_column=1, end_row=lin + 1, end_column=4)


def _aba_etapas(wb: Workbook) -> None:
    ws = wb.create_sheet("Etapas")
    ws["A1"] = "Etapas aceitas"
    ws["A1"].font = F_TIT
    ws["A2"] = "A lista suspensa da aba Reuniões usa estes valores."
    ws["A2"].font = F_SUB
    ws.sheet_view.showGridLines = False

    significado = {
        "Agendado": "Marcada, ainda não aconteceu — fica fora das taxas",
        "Reunião Feita": "Aconteceu, sem desfecho registrado ainda",
        "Follow Up": "Em negociação, aguardando retorno",
        "Fechado": "Contrato assinado",
        "Perdido": "Não fechou — registre também o motivo",
        "No-show": "Cliente não compareceu",
        "Remarcado": "Adiada para outra data",
        "Cancelado": "Cancelada",
    }
    lin = 4
    for i, h in enumerate(["Etapa", "Quando usar"], 1):
        c = ws.cell(lin, i, h)
        c.font, c.fill, c.border = F_CAB, FILL_CAB, BORDA
    lin += 1
    for j, etapa in enumerate(ETAPAS_SUGERIDAS):
        for i, v in enumerate([etapa, significado[etapa]], 1):
            cel = ws.cell(lin, i, v)
            cel.font, cel.border = F_TXT, BORDA
            if j % 2:
                cel.fill = FILL_ZEBRA
        lin += 1
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 62


def gerar_planilha_modelo(destino: str | Path | None = None) -> bytes:
    """Monta a planilha-modelo. Devolve os bytes e, se `destino` vier, também salva."""
    wb = Workbook()
    wb.remove(wb.active)
    _aba_reunioes(wb)
    _aba_metas(wb)
    _aba_instrucoes(wb)
    _aba_etapas(wb)

    dados = BytesIO()
    wb.save(dados)
    conteudo = dados.getvalue()
    if destino:
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
    return conteudo
