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
    assert "aba <strong>Funil</strong>" in ANALISE
    assert "baixarModelo" in ANALISE, "o aviso precisa oferecer a planilha que tem a aba"


def test_leads_e_mql_aparecem_no_resumo():
    """Foram pedidos como indicadores de primeira linha, não como detalhe de tráfego."""
    resumo = ANALISE.split('aba === "resumo"')[1].split('aba === "jet"')[0]
    assert "kpis.leadsinf" in resumo and "kpis.mql" in resumo
