"""O Neriah lê a exportação dos CRMs que o cliente já usa?

O gargalo do produto nunca foi o motor: é a planilha que chega. Estes testes
pegam a mesma base de 32 negócios e a servem em seis formatos diferentes —
cabeçalho em inglês, cabeçalho com prefixo, status no feminino, data com hora,
decimal com vírgula — e exigem o mesmo resultado dos seis. Qualquer divergência
é culpa do formato, porque os números por baixo são idênticos.

As fixtures estão em `fixtures_crm/`, geradas por `fixtures_crm/gerar.py`, e o
grau de confiança de cada formato está documentado lá: HubSpot e Pipedrive têm
nomes de propriedade amplamente documentados; RD Station teve três campos
confirmados na documentação; DataCrazy e Datalitics são produtos reais cujo
formato de exportação não é público, e ali a planilha é uma reconstrução
plausível, não o arquivo verdadeiro.

Nem todo CRM distingue tudo. HubSpot e RD Station não têm etapa de no-show: lá
o ausente fica como reunião marcada ou negócio em andamento. Colapsar os dois
não é defeito do Neriah, é o que o formato permite dizer, e por isso o esperado
muda por CRM nos campos de contagem — nunca no dinheiro.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core import analisar

FIXTURES = Path(__file__).parent / "fixtures_crm"
DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"

pytestmark = pytest.mark.skipif(
    not (META.exists() and FIXTURES.exists()), reason="fixtures indisponíveis"
)

VERDADE = json.loads((FIXTURES / "_verdade.json").read_text(encoding="utf-8"))

# O que cada formato consegue expressar. A chave ausente significa "igual à
# verdade da base"; a presente é o que aquele CRM colapsa.
CRMS = {
    "hubspot_deals_export.csv": ("HubSpot", {"noshow": 0, "agendados": 8}),
    # O Pipedrive distingue agendado de em negociação pela etapa, mas não tem
    # etapa de no-show: quem faltou fica na etapa da reunião marcada.
    "pipedrive_deals_export.csv": ("Pipedrive", {"noshow": 0, "agendados": 8}),
    "rdstation_negociacoes.csv": ("RD Station", {"em_negociacao": 16, "noshow": 0, "agendados": 0}),
    "agendor_negocios.csv": ("Agendor", {}),
    "datacrazy_leads.csv": ("DataCrazy", {}),
    "datalitics_leads.csv": ("Datalitics", {}),
}


def _resultado(arquivo: str):
    return analisar([META], [FIXTURES / arquivo])


@pytest.mark.parametrize("arquivo,crm", [(a, v[0]) for a, v in CRMS.items()])
def test_o_arquivo_e_lido_sem_erro(arquivo, crm):
    """Antes de qualquer número: o Neriah aceita o arquivo.

    Quatro destes seis eram recusados de saída por falta de alias de coluna, e
    um derrubava a análise com TypeError.
    """
    res = _resultado(arquivo)
    assert len(res.tabelas["base_reunioes"]) == VERDADE["linhas"], (
        f"{crm}: perdeu linhas na leitura"
    )


@pytest.mark.parametrize("arquivo,crm", [(a, v[0]) for a, v in CRMS.items()])
def test_o_dinheiro_bate_em_todos_os_formatos(arquivo, crm):
    """Fechados e receita não podem variar com o formato do arquivo.

    É o número que vira decisão de verba, então nenhum CRM tem licença para
    entregá-lo diferente.
    """
    res = _resultado(arquivo)
    assert int(res.kpi("fec")) == VERDADE["fechados"], f"{crm}: contagem de fechados"
    assert round(res.kpi("rec"), 2) == VERDADE["receita"], f"{crm}: receita"
    assert int(res.kpi("per")) == VERDADE["perdidos"], f"{crm}: contagem de perdidos"


@pytest.mark.parametrize("arquivo,crm,ajuste", [(a, v[0], v[1]) for a, v in CRMS.items()])
def test_as_contagens_batem_com_o_que_o_formato_expressa(arquivo, crm, ajuste):
    res = _resultado(arquivo)
    esperado = {**VERDADE, **ajuste}
    obtido = {
        "em_negociacao": int(res.kpi("neg")),
        "noshow": int(res.kpi("ns")),
        "agendados": int(res.kpi("fut")),
    }
    for campo, valor in obtido.items():
        assert valor == esperado[campo], f"{crm}: {campo}"


@pytest.mark.parametrize("arquivo,crm", [(a, v[0]) for a, v in CRMS.items()])
def test_nenhum_status_fica_sem_classificacao(arquivo, crm):
    """'Não classificado' é o balde do que o vocabulário não reconheceu.

    Era onde caíam os 'Ganha' do RD Station e os 'Won' do Pipedrive, e um
    negócio ali não entra em taxa nenhuma: some da conta sem avisar.
    """
    res = _resultado(arquivo)
    import pandas as pd

    por_status = pd.DataFrame(res.tabelas["por_status"])
    coluna = por_status.columns[0]
    nao_classificados = por_status[por_status[coluna] == "Não classificado"]
    assert nao_classificados.empty, f"{crm}: sobrou status não reconhecido"


def test_pipedrive_avisa_que_o_mes_nao_vem_da_reuniao():
    """Sem data de reunião, o mês passa a significar outra coisa, e isso é dito.

    O Pipedrive exporta "Add time" e "Won time", nenhuma delas é reunião. Usar
    uma delas em silêncio faria o cliente ler "reuniões de setembro" onde está
    escrito "negócios criados em setembro".
    """
    res = _resultado("pipedrive_deals_export.csv")
    assert any("não tem data de reunião" in a for a in res.avisos), res.avisos


def test_a_data_escolhida_e_a_mais_preenchida_nao_a_primeira():
    """A data de fechamento só existe no negócio ganho.

    Escolhê-la como âncora jogava fora os 23 negócios que não fecharam, e a
    análise saía com 100% de conversão — o pior tipo de erro, o que parece bom.
    """
    res = _resultado("pipedrive_deals_export.csv")
    assert len(res.tabelas["base_reunioes"]) == 32
    assert int(res.kpi("fec")) == 9


def test_data_com_hora_nao_derruba_a_leitura():
    """Um CRM de WhatsApp exporta data com hora em toda linha.

    A limpeza removia todo espaço antes de parsear, então '05/09/2026 09:12'
    virava '05/09/202609:12' e a planilha inteira ficava sem data válida.
    """
    res = _resultado("datacrazy_leads.csv")
    assert res.mes_referencia == "2026-09"
    assert len(res.tabelas["base_reunioes"]) == 32

@pytest.mark.parametrize("arquivo,crm", [(a, v[0]) for a, v in CRMS.items()])
def test_o_cac_sai_igual_em_todos_os_formatos(arquivo, crm):
    """O CAC é número de capa, e saía R$ 0,00 em dois dos seis formatos.

    Ele depende de a origem ser reconhecida como tráfego pago. Duas causas
    diferentes davam o mesmo sintoma: o HubSpot diz "Paid Social", que não
    estava no vocabulário; e no Pipedrive o apelido "Deal - Source" casava por
    prefixo com "Deal - Source Campaign" e consumia a coluna, então a origem
    virava o nome da campanha e a campanha ficava órfã.

    Nenhum teste pegou isso porque todos olhavam contagem e receita. Quem pegou
    foi a tela: o cartão de CAC mostrando zero numa análise em que todo negócio
    veio de anúncio.
    """
    res = _resultado(arquivo)
    assert int(res.kpi("fecp")) == VERDADE["fechados"], f"{crm}: fechados vindos de tráfego pago"
    assert round(res.kpi("cac"), 2) == 405.67, f"{crm}: CAC"


def test_origem_organica_nao_vira_trafego_pago(tmp_path):
    """"paid" entrou no vocabulário; "social" sozinho não, e por um motivo.

    "Organic Social" é o oposto de tráfego pago, e um vocabulário com "social"
    solto contaria o lead orgânico como vindo do anúncio — inflando o número de
    clientes atribuídos à campanha e derrubando o CAC artificialmente.
    """
    import csv

    arq = tmp_path / "misto.csv"
    with arq.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Deal Name", "Deal Stage", "Close Date", "Amount", "Original Traffic Source"])
        for i in range(4):
            w.writerow([f"Pago {i}", "Closed Won", f"1{i}/09/2026", "1000,00", "Paid Social"])
        for i in range(4):
            w.writerow([f"Organico {i}", "Closed Won", f"1{i}/09/2026", "1000,00", "Organic Social"])
    res = analisar([META], [arq])
    assert int(res.kpi("fec")) == 8, "os oito fecharam"
    assert int(res.kpi("fecp")) == 4, "só os quatro pagos contam para o CAC"


def test_pipedrive_usa_a_etapa_para_separar_agendado_de_negociando():
    """"Open" não diz se a reunião já aconteceu, e a etapa diz.

    O Pipedrive exporta "Deal - Status" (Won/Lost/Open) e "Deal - Stage" (a fase
    do funil). Lendo só o status, toda reunião ainda não acontecida virava "Em
    negociação" e entrava no denominador da assertividade: a agência aparecia
    pior do que é, porque reunião marcada para semana que vem contava como
    reunião que não fechou. Com 8 agendamentos em 32 negócios, 28,1% em vez de
    37,5%.
    """
    res = _resultado("pipedrive_deals_export.csv")
    assert int(res.kpi("fut")) == 8, "os 8 em etapa de reunião marcada"
    assert int(res.kpi("real")) == 24, "realizadas não inclui quem ainda não foi atendido"
    assert round(res.kpi("assert"), 3) == 0.375


def test_a_etapa_nao_desfaz_um_desfecho_ja_decidido():
    """Negócio ganho continua ganho, mesmo que a etapa diga outra coisa.

    No Pipedrive o negócio ganho fica em "Negotiations Started", que sozinha
    classificaria como em negociação. A etapa só reescreve o que está em aberto.
    """
    res = _resultado("pipedrive_deals_export.csv")
    assert int(res.kpi("fec")) == 9 and int(res.kpi("per")) == 7


def test_pipedrive_e_hubspot_concordam_apesar_do_formato_diferente():
    """Mesma base, cabeçalhos diferentes, dois CRMs: o mesmo número.

    É a prova de que o motor lê o conteúdo e não o formato.
    """
    pd_, hs = _resultado("pipedrive_deals_export.csv"), _resultado("hubspot_deals_export.csv")
    for chave in ["fec", "per", "neg", "fut", "real", "rec", "cac"]:
        assert round(pd_.kpi(chave), 2) == round(hs.kpi(chave), 2), f"divergiu em {chave}"
