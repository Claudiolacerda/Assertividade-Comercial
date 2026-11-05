"""Uma aba por mês: o formato em que a planilha de controle comercial nasce.

O sistema lia só a PRIMEIRA aba do arquivo. Numa planilha com Agosto, Setembro
e Outubro, pedir outubro devolvia os números de agosto — e carimbava o
resultado como outubro. Os totais batiam com alguma coisa, só não com o mês
certo, e nada na tela dizia isso.

Filtrar por data não resolve esse formato: nele a data falta justamente nas
linhas fechadas, onde o vendedor preenche o status e não a data. Quem separa os
meses aqui é o NOME DA ABA, que é a intenção do usuário dita em voz alta.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from app.core import analisar
from app.core.leitura import mes_da_aba

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"

pytestmark = pytest.mark.skipif(not META.exists(), reason="exemplo da Meta indisponível")

# Mês -> (fechados, reuniões feitas). Números diferentes por aba de propósito:
# é assim que se percebe qual aba foi lida.
MESES = {"Agosto": 4, "Setembro": 2, "Outubro": 7}


@pytest.fixture(scope="module")
def planilha_por_mes(tmp_path_factory) -> Path:
    """Três abas nomeadas por mês, no formato painel-por-semana.

    As linhas fechadas vão SEM data, como na planilha real: é esse detalhe que
    faz o filtro por data ser o caminho errado.
    """
    arq = tmp_path_factory.mktemp("abas") / "controle.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for mes, fechados in MESES.items():
        ws = wb.create_sheet(mes)
        ws["A1"] = "Painel Comercial"
        ws["A3"] = "Semana 1"
        for i, titulo in enumerate(["Cliente", "Data da Reunião Realizada", "Etapa do Funil", "Origem"], 1):
            ws.cell(4, i, titulo)
        linha = 5
        for n in range(fechados):
            ws.cell(linha, 1, f"{mes[:3]} fechado {n}")
            ws.cell(linha, 3, "Fechado")  # sem data, como na planilha de verdade
            ws.cell(linha, 4, "Facebook Ads")
            linha += 1
        for n in range(3):
            ws.cell(linha, 1, f"{mes[:3]} reuniao {n}")
            ws.cell(linha, 2, f"0{n + 1}/{list(MESES).index(mes) + 8:02d}/2026")
            ws.cell(linha, 3, "Reunião Feita")
            ws.cell(linha, 4, "Facebook Ads")
            linha += 1
    wb.save(arq)
    return arq


# --------------------------------------------------------------------- #
# O nome da aba
# --------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "nome,esperado",
    [
        ("Agosto", (8, None)),
        ("Outubro 2026", (10, 2026)),
        ("out/26", (10, 2026)),
        ("2026-10", (10, 2026)),
        ("Reuniões", None),
        ("Metas", None),
        ("Funil", None),
        ("Semana 1", None),
        ("", None),
    ],
)
def test_le_o_mes_do_nome_da_aba(nome, esperado):
    """As abas da planilha-modelo não podem virar mês nenhum."""
    assert mes_da_aba(nome) == esperado


# --------------------------------------------------------------------- #
# A análise
# --------------------------------------------------------------------- #
@pytest.mark.parametrize("mes,fechados", [("2026-08", 4), ("2026-09", 2), ("2026-10", 7)])
def test_cada_mes_pedido_le_a_aba_daquele_mes(planilha_por_mes, mes, fechados):
    """O teste que impede o bug voltar: pedir outubro e receber agosto."""
    from dataclasses import replace

    from app.core.config_analise import ConfigAnalise

    res = analisar([META], [planilha_por_mes], replace(ConfigAnalise(), mes_referencia=mes))
    assert res.mes_referencia == mes
    assert int(res.kpi("fec")) == fechados


def test_sem_mes_escolhido_analisa_o_mais_recente(planilha_por_mes):
    """É o mês que a pessoa acabou de fechar."""
    res = analisar([META], [planilha_por_mes])
    assert res.mes_referencia == "2026-10"
    assert int(res.kpi("fec")) == MESES["Outubro"]


def test_a_tela_diz_qual_aba_foi_usada_e_quais_ficaram_de_fora(planilha_por_mes):
    """Sem isso, o usuário não tem como saber que havia outras abas."""
    from dataclasses import replace

    from app.core.config_analise import ConfigAnalise

    res = analisar([META], [planilha_por_mes], replace(ConfigAnalise(), mes_referencia="2026-09"))
    avisos = " ".join(res.avisos)
    assert "aba de setembro/2026" in avisos
    assert "Agosto" in avisos and "Outubro" in avisos


def test_as_linhas_fechadas_sem_data_nao_sao_descartadas(planilha_por_mes):
    """O detalhe que torna o filtro por data errado neste formato.

    Se o mês fosse escolhido pela data da linha, os fechamentos sumiriam: eles
    são exatamente as linhas em que o vendedor preenche o status e não a data.
    """
    res = analisar([META], [planilha_por_mes])
    assert int(res.kpi("fec")) == MESES["Outubro"], "os fechados sem data continuam contando"


def test_a_planilha_modelo_nao_e_confundida_com_abas_por_mes(tmp_path):
    """Reuniões, Metas, Funil, Como preencher e Etapas não são meses.

    Se alguma delas virasse mês, a análise passaria a filtrar por aba e
    devolveria uma planilha vazia.
    """
    from app.core.modelo import gerar_planilha_modelo

    arq = tmp_path / "modelo.xlsx"
    gerar_planilha_modelo(arq)
    nomes = openpyxl.load_workbook(arq).sheetnames
    assert all(mes_da_aba(n) is None for n in nomes), nomes


# --------------------------------------------------------------------- #
# O que mais a aba por mês conserta
# --------------------------------------------------------------------- #
def _planilha_dia_solto(tmp_path: Path) -> Path:
    """Aba "Agosto" com a data escrita só com o dia, como na planilha real.

    Quem mantém uma aba por mês escreve "12" na coluna de data: o mês já está
    no nome da aba, e repeti-lo em toda linha é trabalho à toa.
    """
    arq = tmp_path / "dia_solto.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Agosto")
    ws["A1"] = "Painel Comercial"
    ws["A3"] = "Semana 1"
    for i, titulo in enumerate(["Cliente", "Data da Reunião Realizada", "Etapa do Funil", "Origem"], 1):
        ws.cell(4, i, titulo)
    linhas = [
        ("Cliente A", 12, "Fechado", "Facebook Ads"),
        ("Cliente B", 14, "Reunião Feita", "Facebook Ads"),
        ("Cliente C", "20/08/2026", "Reunião Feita", "Facebook Ads"),
        ("Semana 3", None, None, None),  # título que escapou do leitor de blocos
        ("Cliente D", 21, "Perdido", "Facebook Ads"),
    ]
    for j, linha in enumerate(linhas):
        for i, valor in enumerate(linha, 1):
            if valor is not None:
                ws.cell(5 + j, i, valor)
    wb.save(arq)
    return arq


def test_data_escrita_so_com_o_dia_usa_o_mes_da_aba(tmp_path):
    """Sem isso, 40 das 46 linhas de agosto ficavam sem data na planilha real.

    E linha sem data some da semana, do ciclo e do tempo em aberto.
    """
    res = analisar([META], [_planilha_dia_solto(tmp_path)])
    b = res.tabelas["base_reunioes"]
    assert b["data_reuniao"].notna().sum() == 4, "as três com dia solto mais a que já era data"
    assert str(b["data_reuniao"].min())[:7] == "2026-08"
    assert any("só com o dia" in a for a in res.avisos)


def test_dia_impossivel_no_mes_nao_vira_data(tmp_path):
    """31 numa aba de abril é erro de digitação, não dia 31 de abril."""
    arq = tmp_path / "abril.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Abril 2026")
    for i, titulo in enumerate(["Cliente", "Data da Reunião Realizada", "Etapa do Funil"], 1):
        ws.cell(1, i, titulo)
    ws.cell(2, 1, "Cliente A"); ws.cell(2, 2, 31); ws.cell(2, 3, "Fechado")
    ws.cell(3, 1, "Cliente B"); ws.cell(3, 2, 15); ws.cell(3, 3, "Fechado")
    wb.save(arq)
    b = analisar([META], [arq]).tabelas["base_reunioes"]
    assert b["data_reuniao"].notna().sum() == 1


def test_linha_de_titulo_nao_vira_cliente(tmp_path):
    """"Semana 3" virava um cliente, contava como reunião e entrava nas taxas."""
    res = analisar([META], [_planilha_dia_solto(tmp_path)])
    clientes = set(res.tabelas["base_reunioes"]["cliente"])
    assert "Semana 3" not in clientes
    assert len(res.tabelas["base_reunioes"]) == 4
    assert any("título da planilha" in a for a in res.avisos)


def test_o_resultado_de_uma_planilha_com_abas_por_mes_e_gravavel(planilha_por_mes):
    """A conta rodava e a GRAVAÇÃO quebrava: Period não vira JSON.

    O erro aparecia no fim, depois de o usuário esperar a análise inteira, e
    vinha como um SQL gigante na tela. Qualquer coluna de trabalho que não seja
    serializável derruba a análise toda, então o tratamento é na saída, não no
    nome da coluna.
    """
    import json

    payload = analisar([META], [planilha_por_mes]).to_payload()
    texto = json.dumps(payload, ensure_ascii=False)
    assert len(texto) > 1000
    assert "mes_aba" not in payload["tabelas"]["base_reunioes"][0], "coluna de trabalho não sai na base"


def test_period_em_qualquer_tabela_vira_texto():
    """A defesa que vale para a próxima coluna que alguém acrescentar."""
    import json

    import pandas as pd

    from app.core.pipeline import _tabela_json

    df = pd.DataFrame({"mes": pd.Series([pd.Period("2026-10", "M")], dtype="period[M]")})
    json.dumps(_tabela_json(df))
