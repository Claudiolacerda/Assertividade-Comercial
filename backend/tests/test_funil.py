"""O topo do funil: leads, MQL e as taxas que dependem deles.

A planilha de reuniões só tem linha para quem chegou a agendar. Quem virou lead
e nunca marcou reunião não está lá — ele só existe como um número que o usuário
informa na aba Funil. Daí a regra que atravessa este arquivo:

    sem o número informado, o indicador NÃO aparece — não aparece zerado.

Um zero numa taxa de agendamento é uma afirmação sobre a operação. A ausência
do número é uma afirmação sobre a planilha. Trocar uma pela outra faz o cliente
ler um mês péssimo onde havia só uma aba em branco, e é o erro que estes testes
existem para impedir.
"""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl
import pytest

from app.core import analisar
from app.core.leitura import ler_funil_da_planilha
from app.core.modelo import ABA_FUNIL, CAMPOS_FUNIL, gerar_planilha_modelo

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"

pytestmark = pytest.mark.skipif(not META.exists(), reason="exemplo da Meta indisponível")

# 5 negócios: 2 fechados, 1 perdido, 1 em negociação, 1 ainda agendado.
NEGOCIOS = [
    ("Cliente A", "Fechado", "05/09/2026", "2500,00"),
    ("Cliente B", "Fechado", "06/09/2026", "1500,00"),
    ("Cliente C", "Perdido", "07/09/2026", "0"),
    ("Cliente D", "Follow Up", "08/09/2026", "0"),
    ("Cliente E", "Agendado", "20/09/2026", "0"),
]


def _planilha(tmp_path: Path, leads: int | None = None, mql: int | None = None) -> Path:
    """Gera a planilha-modelo, preenche as reuniões e, se pedido, o funil."""
    arq = tmp_path / "comercial.xlsx"
    gerar_planilha_modelo(arq)
    wb = openpyxl.load_workbook(arq)

    ws = wb["Reuniões"]
    cabecalho = [c.value for c in ws[4]]
    col = {nome: i + 1 for i, nome in enumerate(cabecalho)}
    for j, (cliente, etapa, data, valor) in enumerate(NEGOCIOS):
        linha = 5 + j
        for c in range(1, len(cabecalho) + 1):
            ws.cell(linha, c, None)
        ws.cell(linha, col["Cliente"], cliente)
        ws.cell(linha, col["Etapa do Funil"], etapa)
        ws.cell(linha, col["Data da Reunião Realizada"], data)
        ws.cell(linha, col["Valor"], valor)
        ws.cell(linha, col["Origem"], "Facebook Ads")

    wf = wb[ABA_FUNIL]
    # linha 5 = leads recebidos, linha 6 = MQL (a ordem de CAMPOS_FUNIL).
    # Atribuir por `.value` e não por `cell(l, c, valor)`: o openpyxl só aplica
    # o terceiro argumento quando ele não é None, então passar None ali é um
    # no-op e os exemplos do modelo continuavam na planilha — o teste de "aba
    # em branco" rodava com a aba preenchida.
    wf.cell(5, 2).value = leads
    wf.cell(6, 2).value = mql
    wb.save(arq)
    return arq


# --------------------------------------------------------------------- #
# A regra central: ausência não é zero
# --------------------------------------------------------------------- #
def test_sem_a_aba_preenchida_os_indicadores_de_topo_nao_aparecem(tmp_path):
    """Aba em branco não pode virar "0% de agendamento".

    Zero é uma afirmação sobre a operação; a ausência é uma afirmação sobre a
    planilha. Confundir as duas faz o cliente ler um mês péssimo onde havia só
    uma aba vazia.
    """
    res = analisar([META], [_planilha(tmp_path)])
    for chave in ("leadsinf", "mql", "l2mql", "txag", "mql2ag"):
        assert chave not in res.kpis, f"{chave} apareceu sem o número informado"
    assert not any("TOPO DO FUNIL" in titulo for titulo, _ in res.blocos)


def test_so_leads_informados_traz_a_taxa_de_agendamento_mas_nao_o_mql(tmp_path):
    """Quem informa só o que tem recebe só o que dá para calcular."""
    res = analisar([META], [_planilha(tmp_path, leads=200)])
    assert "leadsinf" in res.kpis and "txag" in res.kpis
    assert "mql" not in res.kpis and "mql2ag" not in res.kpis and "l2mql" not in res.kpis


def test_so_mql_informado_traz_a_passagem_mas_nao_a_mira(tmp_path):
    res = analisar([META], [_planilha(tmp_path, mql=80)])
    assert "mql" in res.kpis and "mql2ag" in res.kpis
    assert "leadsinf" not in res.kpis and "l2mql" not in res.kpis


def test_zero_informado_conta_como_nao_informado(tmp_path):
    """Escrever 0 na aba é o mesmo que deixar em branco.

    Ninguém teve um mês com zero leads e ainda assim cinco reuniões marcadas:
    o zero ali é lapso de preenchimento, não medição.
    """
    res = analisar([META], [_planilha(tmp_path, leads=0, mql=0)])
    assert "leadsinf" not in res.kpis and "mql" not in res.kpis


# --------------------------------------------------------------------- #
# As contas
# --------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def completo(tmp_path_factory):
    return analisar([META], [_planilha(tmp_path_factory.mktemp("f"), leads=200, mql=80)])


def test_as_taxas_do_topo_batem_com_a_aritmetica(completo):
    assert int(completo.kpi("leadsinf")) == 200
    assert int(completo.kpi("mql")) == 80
    assert int(completo.kpi("ag")) == 5, "os 5 negócios da planilha"
    assert completo.kpi("l2mql") == pytest.approx(80 / 200)
    assert completo.kpi("txag") == pytest.approx(5 / 200)
    assert completo.kpi("mql2ag") == pytest.approx(5 / 80)


def test_a_taxa_de_conversao_e_fechados_sobre_agendados(completo):
    """O que o usuário chama de taxa de conversão: de 100 marcadas, quantas fecham."""
    assert int(completo.kpi("fec")) == 2
    assert completo.kpi("fag") == pytest.approx(2 / 5)
    assert "Taxa de conversão" in completo.kpis["fag"]["rotulo"]


def test_a_taxa_de_agendamento_e_comparada_com_a_meta(completo):
    """Ela herda a meta de lead para reunião, que já existia na configuração."""
    k = completo.kpis["txag"]
    assert k["meta_tipo"] == "min" and k["meta_valor"] > 0
    assert k["dentro_da_meta"] is False, "5 em 200 está longe de qualquer meta razoável"


def test_os_agendados_sao_nomeados_como_leads_qualificados(completo):
    """O usuário chama de lead qualificado quem marcou reunião."""
    assert "qualificados" in completo.kpis["ag"]["rotulo"]


# --------------------------------------------------------------------- #
# O gráfico de funil
# --------------------------------------------------------------------- #
def test_o_mql_entra_no_funil_entre_o_lead_e_o_agendamento(completo):
    etapas = [linha["Etapa"] for linha in completo.tabelas["funil"].to_dict("records")]
    assert any("MQL" in e for e in etapas)
    i_mql = next(i for i, e in enumerate(etapas) if "MQL" in e)
    i_lead = next(i for i, e in enumerate(etapas) if "Leads" in e)
    i_ag = next(i for i, e in enumerate(etapas) if "agendadas" in e)
    assert i_lead < i_mql < i_ag


def test_sem_mql_o_funil_nao_ganha_etapa_inventada(tmp_path):
    """Etapa inventada é pior que etapa ausente.

    A queda entre duas barras de um funil é lida como perda. Pôr ali uma etapa
    que ninguém contou faz o gráfico afirmar uma perda que não existe.
    """
    res = analisar([META], [_planilha(tmp_path, leads=200)])
    etapas = [linha["Etapa"] for linha in res.tabelas["funil"].to_dict("records")]
    assert not any("MQL" in e for e in etapas)


# --------------------------------------------------------------------- #
# A aba na planilha-modelo
# --------------------------------------------------------------------- #
def test_a_aba_funil_do_modelo_volta_inteira_na_leitura(tmp_path):
    """Modelo e leitor usam a mesma lista; se um mudar sozinho, isto quebra."""
    arq = tmp_path / "modelo.xlsx"
    gerar_planilha_modelo(arq)
    lidos = ler_funil_da_planilha([arq])
    esperado = {chave: exemplo for chave, _r, _f, _e, exemplo in CAMPOS_FUNIL}
    assert lidos == pytest.approx(esperado)


def test_a_aba_funil_e_separada_da_de_metas(tmp_path):
    """Metas é o que se quer; Funil é o que aconteceu.

    Juntar as duas faria o JET comparar um número com ele mesmo.
    """
    arq = tmp_path / "modelo.xlsx"
    gerar_planilha_modelo(arq)
    wb = openpyxl.load_workbook(arq)
    assert ABA_FUNIL in wb.sheetnames and "Metas" in wb.sheetnames
    assert ABA_FUNIL != "Metas"


def test_csv_e_planilha_sem_a_aba_nao_quebram():
    """A aba é opcional: export de CRM nenhum tem isso."""
    assert ler_funil_da_planilha([META]) == {}


def test_a_analise_de_um_csv_continua_igual(tmp_path):
    """Nenhum dos indicadores novos pode alterar o que já era calculado."""
    reunioes = DADOS / "reunioes" / "Controle_Comercial_Exemplo_-_Setembro.csv"
    if not reunioes.exists():
        pytest.skip("exemplo de reuniões indisponível")
    res = analisar([META], [reunioes])
    assert "leadsinf" not in res.kpis
    assert int(res.kpi("fec")) == 9, "o número cravado da planilha de exemplo"
