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
def _etapas(res, tabela: str) -> list[str]:
    return [linha["Etapa"] for linha in res.tabelas[tabela].to_dict("records")]


def test_o_mql_entra_no_funil_do_topo_entre_o_lead_e_o_agendamento(completo):
    etapas = _etapas(completo, "funil_topo")
    i_mql = next(i for i, e in enumerate(etapas) if "MQL" in e)
    i_lead = next(i for i, e in enumerate(etapas) if "Leads" in e)
    i_ag = next(i for i, e in enumerate(etapas) if "agendadas" in e)
    assert i_lead < i_mql < i_ag


def test_o_mql_nao_entra_no_funil_do_trafego_pago(completo):
    """Os dois funis medem universos diferentes, e misturá-los produz uma barra
    que cresce.

    O MQL é de todas as origens; os leads do funil pago são os que a Meta
    reportou. Num mês de 81 leads da Meta e 168 MQL, a etapa do meio subia
    207%. Num gráfico de funil, uma barra que cresce não é um dado estranho: é
    uma afirmação falsa, porque toda etapa ali é um recorte da anterior.
    """
    assert not any("MQL" in e for e in _etapas(completo, "funil"))


@pytest.mark.parametrize("tabela", ["funil", "funil_topo"])
def test_nenhum_funil_tem_barra_que_cresce(completo, tabela: str):
    """A regra que o MQL quebrou, agora medida nos dois funis."""
    linhas = completo.tabelas[tabela].to_dict("records")
    for anterior, atual in zip(linhas, linhas[1:]):
        assert atual["Quantidade"] <= anterior["Quantidade"], (
            f"{tabela}: '{atual['Etapa']}' ({atual['Quantidade']}) é maior que "
            f"'{anterior['Etapa']}' ({anterior['Quantidade']})"
        )


def test_sem_mql_informado_o_funil_nao_ganha_barra_repetida(tmp_path):
    """Etapa inventada é pior que etapa ausente, e etapa repetida também.

    Para quem chama de MQL quem marcou reunião, a barra do MQL e a das reuniões
    agendadas são o mesmo número com dois nomes. Duas barras iguais, com uma
    queda de 0% entre elas, ocupam espaço afirmando nada. Então o agendamento
    carrega os dois nomes e a barra é uma só.
    """
    res = analisar([META], [_planilha(tmp_path, leads=200)])
    etapas = _etapas(res, "funil_topo")
    assert etapas[0].startswith("Leads recebidos")
    assert etapas[1] == "MQL / reuniões agendadas"
    assert len([e for e in etapas if "MQL" in e]) == 1


def test_sem_a_aba_nao_existe_funil_do_topo(tmp_path):
    """Sem nenhum dos dois números não há o que desenhar."""
    res = analisar([META], [_planilha(tmp_path)])
    assert "funil_topo" not in res.tabelas


def test_mql_maior_que_os_leads_e_apontado_como_erro_de_preenchimento(tmp_path):
    """O MQL é um recorte dos leads: maior que eles é lapso, não mês histórico."""
    res = analisar([META], [_planilha(tmp_path, leads=50, mql=200)])
    texto = " ".join(res.diagnostico["Diagnóstico"])
    assert "não pode ser maior" in texto


# --------------------------------------------------------------------- #
# O MQL na definição de quem opera: quem marcou reunião
# --------------------------------------------------------------------- #
# Eu havia implementado o MQL do livro de marketing, uma etapa ANTES do
# agendamento, e exigido que fosse digitado. Mas na operação lead qualificado é
# quem marcou reunião, e esse número a planilha já tem: é a contagem de linhas.
# Pedir que fosse informado era pedir um dado que o sistema tinha na mão.
def test_o_lead_qualificado_e_contado_da_propria_planilha(tmp_path):
    """Sem informar nada, o número de leads qualificados já existe."""
    res = analisar([META], [_planilha(tmp_path)])
    k = res.kpis["ag"]
    assert int(k["valor"]) == 5, "as 5 linhas da planilha"
    assert "MQL" in k["rotulo"] and "qualificados" in k["rotulo"]


def test_nao_ha_dois_indicadores_com_o_mesmo_numero(tmp_path):
    """Um cartão "MQL" ao lado de "reuniões agendadas", ambos 5, é ruído."""
    res = analisar([META], [_planilha(tmp_path)])
    assert "mql" not in res.kpis


def test_mql_igual_as_reunioes_marcadas_nao_vira_etapa_separada(tmp_path):
    """Informar o mesmo número que a planilha conta não cria uma etapa.

    A taxa entre os dois daria 100% por construção, o que não é medição.
    """
    res = analisar([META], [_planilha(tmp_path, leads=200, mql=5)])
    assert "mql" not in res.kpis and "mql2ag" not in res.kpis
    assert len([e for e in _etapas(res, "funil_topo") if "MQL" in e]) == 1


def test_quem_tem_etapa_de_qualificacao_propria_continua_medindo_as_duas(tmp_path):
    """O MQL do livro: uma etapa anterior ao agendamento, com número maior.

    Quem de fato mantém essa etapa informa o número, ele difere da contagem de
    reuniões, e as duas passagens passam a dizer algo.
    """
    res = analisar([META], [_planilha(tmp_path, leads=200, mql=80)])
    assert int(res.kpi("mql")) == 80
    assert res.kpi("mql2ag") == pytest.approx(5 / 80)
    assert res.kpi("l2mql") == pytest.approx(80 / 200)
    etapas = _etapas(res, "funil_topo")
    assert etapas[1].startswith("MQL") and etapas[2] == "Reuniões agendadas"


def test_a_taxa_de_agendamento_e_nomeada_como_passagem_para_qualificado(tmp_path):
    """É a mesma coisa: de cada 100 leads, quantos viraram lead qualificado."""
    res = analisar([META], [_planilha(tmp_path, leads=200)])
    assert "lead → MQL" in res.kpis["txag"]["rotulo"]


# --------------------------------------------------------------------- #
# A aba na planilha-modelo
# --------------------------------------------------------------------- #
def test_a_aba_funil_do_modelo_volta_inteira_na_leitura(tmp_path):
    """Modelo e leitor usam a mesma lista; se um mudar sozinho, isto quebra.

    O campo opcional sai em branco no modelo, e branco tem de voltar como
    ausente: um exemplo ali viraria uma etapa de funil que ninguém contou.
    """
    arq = tmp_path / "modelo.xlsx"
    gerar_planilha_modelo(arq)
    lidos = ler_funil_da_planilha([arq])
    esperado = {chave: ex for chave, _r, _f, _e, ex in CAMPOS_FUNIL if ex is not None}
    assert lidos == pytest.approx(esperado)
    assert "mql" not in lidos, "o campo opcional vem com exemplo e inventa uma etapa"


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


# --------------------------------------------------------------------- #
# Onde mais os números aparecem
# --------------------------------------------------------------------- #
def test_o_relatorio_de_whatsapp_usa_o_lead_informado_e_mostra_o_mql(completo):
    """Dois "leads" com valores diferentes na mesma mensagem não se explicam.

    Com a aba Funil preenchida, o lead que vale no WhatsApp é o informado: ele
    conta todas as origens e é o que o dono do negócio chama de "os leads do
    mês". O da Meta continua no painel e na planilha.
    """
    from app.core.relatorio_zap import gerar_texto

    texto = gerar_texto(completo.to_payload(), "Cliente Exemplo", "2026-09")
    assert "Leads recebidos" in texto and "Leads gerados" not in texto
    assert "Leads qualificados (marcaram reunião)" in texto
    assert "Taxa de agendamento" in texto


def test_sem_a_aba_o_relatorio_volta_a_usar_o_lead_da_meta(tmp_path):
    res = analisar([META], [_planilha(tmp_path)])
    from app.core.relatorio_zap import gerar_texto

    texto = gerar_texto(res.to_payload(), "Cliente Exemplo", "2026-09")
    assert "Leads gerados" in texto and "Leads recebidos" not in texto
    # O lead qualificado continua lá: ele vem da planilha, não da aba Funil.
    assert "Leads qualificados (marcaram reunião)" in texto
    assert "MQL antes do agendamento" not in texto


def test_a_planilha_entregue_ganha_a_aba_do_funil_completo(completo):
    """O relatório que o cliente recebe tem de carregar os números novos."""
    import io

    import openpyxl as _opx

    from app.core.excel import gerar_excel

    wb = _opx.load_workbook(io.BytesIO(gerar_excel(completo)))
    assert "Funil do Lead ao Cliente" in wb.sheetnames
    ws = wb["Funil do Lead ao Cliente"]
    texto = " ".join(str(c.value) for linha in ws.iter_rows() for c in linha if c.value)
    assert "MQL" in texto and "Leads recebidos" in texto


def test_a_taxa_de_agendamento_nao_repete_o_nome_de_outra_taxa(tmp_path):
    """Com etapa de MQL própria, "lead → MQL" já é outra taxa.

    Dois indicadores com o mesmo rótulo e valores diferentes na mesma tela não
    se explicam.
    """
    res = analisar([META], [_planilha(tmp_path, leads=200, mql=80)])
    rotulos = [res.kpis[c]["rotulo"] for c in ("txag", "l2mql")]
    assert len(set(rotulos)) == 2
    assert res.kpis["txag"]["rotulo"] == "Taxa de agendamento (lead → reunião)"
