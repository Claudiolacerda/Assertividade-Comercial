"""A tela tem de mostrar todo indicador de topo que o motor calculou.

O motor cria os indicadores de topo um a um: quem informa só o MQL recebe
`mql` e `mql2ag` e nada mais (está provado em test_funil.py). A tela, porém,
condicionava a seção INTEIRA a `kpis.leadsinf`, então uma planilha com MQL e
sem leads escondia o MQL que já estava calculado e gravado. O sintoma era
"cadê os MQL?" numa análise onde eles existiam.

Não há runner de teste no frontend, então o que dá para garantir daqui é o
contrato entre os dois lados: toda chave que o motor pode emitir aparece na
tela, e a seção não depende de uma delas em particular.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ANALISE = (Path(__file__).resolve().parents[2] / "frontend/src/pages/Analise.tsx").read_text(
    encoding="utf-8"
)

TOPO = ["leadsinf", "mql", "l2mql", "txag", "mql2ag"]


@pytest.mark.parametrize("chave", TOPO)
def test_todo_indicador_de_topo_tem_lugar_na_tela(chave: str):
    assert f"kpis.{chave}" in ANALISE, f"o motor emite '{chave}' e a tela não o mostra em lugar nenhum"


def test_a_secao_de_topo_nao_depende_de_um_indicador_so():
    """`{kpis.leadsinf && (` era o defeito: um ausente escondia os outros quatro."""
    for chave in TOPO:
        assert f"{{kpis.{chave} && (" not in ANALISE, (
            f"a seção está condicionada a '{chave}'; use o conjunto (temTopo)"
        )
    assert "{temTopo && (" in ANALISE


def test_a_ausencia_do_topo_e_explicada_na_tela():
    """Antes não aparecia nem o número nem o motivo.

    Quem procurava o MQL não tinha como descobrir que ele vem de um campo que a
    planilha de reuniões não tem.
    """
    assert "{!temTopo && (" in ANALISE
    assert "<strong>Funil</strong>" in ANALISE
    assert "baixarModelo" in ANALISE, "o aviso precisa oferecer a planilha que tem a aba"


def test_leads_e_qualificados_aparecem_no_resumo():
    """Foram pedidos como indicadores de primeira linha, não como detalhe de tráfego.

    O lead qualificado é o `ag`, contado na planilha: ele tem de estar no Resumo
    mesmo quando nada foi informado, que é o caso de toda análise antiga.
    """
    resumo = ANALISE.split('aba === "resumo"')[1].split('aba === "jet"')[0]
    assert "kpis.leadsinf" in resumo and "kpis.mql" in resumo
    assert "kpis.ag" in resumo, "sem ele, uma análise sem a aba Funil não mostra o qualificado"


def test_o_aviso_de_falta_nao_pede_o_mql():
    """Ele vinha dizendo que o MQL era informado, e não é: a planilha o conta.

    Pedir ao usuário um número que o sistema já tem é o defeito que esta tela
    tinha, e o texto era parte dele.
    """
    aviso = ANALISE.split("{!temTopo && (")[1].split("</div>")[0]
    assert "total de leads" in aviso
    assert "já estão contados" in aviso


# --------------------------------------------------------------------- #
# Informar os números sem refazer o upload
# --------------------------------------------------------------------- #
INFORMAR = (Path(__file__).resolve().parents[2] / "frontend/src/components/InformarFunil.tsx").read_text(
    encoding="utf-8"
)


def test_a_tela_oferece_informar_os_numeros_quando_eles_faltam():
    """Baixar a planilha e subir de novo era a única saída, e não é saída.

    O resultado de uma análise fica gravado como JSON, então mandar o usuário
    preencher a planilha não resolvia o mês que ele já tinha analisado.
    """
    assert "InformarFunil" in ANALISE
    assert ANALISE.count("<InformarFunil") == 2, (
        "faltou um dos dois lugares: no aviso de ausência e no ajuste dos números já informados"
    )


def test_o_formulario_chama_o_reprocessamento_e_vai_para_a_versao_nova():
    assert "api.reprocessar" in INFORMAR
    assert "navegar(`/analises/${nova.id}`)" in INFORMAR, (
        "ficar na análise antiga depois de recalcular faz parecer que nada mudou"
    )


def test_o_formulario_aceita_recalcular_sem_informar_nada():
    """É o caminho de pôr uma análise antiga no motor de hoje."""
    assert "Informe pelo menos um dos dois" not in INFORMAR


# --------------------------------------------------------------------- #
# A aba "Quantos leads"
# --------------------------------------------------------------------- #
POR_LEAD = (Path(__file__).resolve().parents[2] / "frontend/src/components/PorLead.tsx").read_text(
    encoding="utf-8"
)
CHARTS = (Path(__file__).resolve().parents[2] / "frontend/src/components/Charts.tsx").read_text(
    encoding="utf-8"
)


def test_a_aba_existe_e_tem_painel():
    """Aba sem painel é um botão que não faz nada."""
    assert '{ id: "porlead"' in ANALISE
    assert 'aba === "porlead"' in ANALISE
    assert 'id="painel-porlead"' in ANALISE and 'aria-labelledby="aba-porlead"' in ANALISE
    assert "<PorLead kpis={kpis}" in ANALISE


@pytest.mark.parametrize("chave", ["lpag", "agfec", "lpfec"])
def test_a_aba_mostra_os_indicadores_que_o_motor_emite(chave: str):
    assert f"kpis.{chave}" in POR_LEAD


def test_o_cac_entra_pela_conta_e_nao_como_cartao_repetido():
    """Ele já tem cartão no Resumo e na aba de tráfego.

    Aqui o que importa dele é o preço de uma venda dentro da cadeia e o
    orçamento do simulador, não um quarto cartão quebrando a fileira de três.
    """
    assert 'valor(kpis, "cac")' in POR_LEAD
    assert "<Tile kpi={kpis.cac}" not in POR_LEAD


def test_as_duas_calculadoras_andam_nos_dois_sentidos():
    """"Tenho leads, o que espero" e "quero vender, de quanto preciso"."""
    assert "leadsSimulados / lpag" in POR_LEAD, "faltou estimar as reuniões a partir dos leads"
    assert "vendasDesejadas * lpfec" in POR_LEAD, "faltou estimar os leads a partir das vendas"


def test_a_aba_nao_inventa_numero_quando_nao_ha_razao():
    """Mês sem reunião e sem venda: nada a calcular, e a tela diz isso."""
    assert "if (!lpag && !lpfec)" in POR_LEAD


def test_o_formato_num_existe_nos_dois_lados():
    """O motor emite "num" e a tela tem de saber formatá-lo.

    Sem isso o valor cai no formatador de inteiros e "11,4 leads por reunião"
    aparece como "11".
    """
    assert 'formato === "num"' in CHARTS


def test_a_aba_recebe_a_base_de_calculo_e_a_declara():
    """Sem ela a tela escreveria "leads a gerar" sem dizer de onde.

    Na base informada, parte dos leads vem de indicação e de busca, que não
    custam mídia: dizer o número sem o universo convida a multiplicar pelo CPL
    e chegar a um orçamento que não existe.
    """
    assert "base={r.base_esforco}" in ANALISE
    assert 'base === "informada"' in POR_LEAD
    assert "todas as origens" in POR_LEAD and "do tráfego pago" in POR_LEAD
