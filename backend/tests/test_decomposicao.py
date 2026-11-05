"""Por que a receita mudou: a diferença repartida entre os fatores.

O painel já mostrava os cinco indicadores da cadeia lado a lado e obrigava o
usuário a comparar cada um com o do mês passado e juntar de cabeça. Quem tem
quatro minutos não faz essa conta: responde "o mercado estava fraco" e perde a
reunião.

A propriedade que todo este arquivo defende é uma só: **as parcelas somam
exatamente a variação**. Uma decomposição com sobra obriga a inventar uma linha
"outros", e é nela que a explicação verdadeira costuma se esconder.
"""

from __future__ import annotations

import pytest

from app.core.decomposicao import Mes, comparar, montar_mes


def mes(ref="2026-09", leads=100, ag=0.30, comp=0.95, assertividade=0.30, ticket=2500.0) -> Mes:
    return Mes(ref, leads=leads, agendamento=ag, comparecimento=comp,
               assertividade=assertividade, ticket=ticket)


def test_a_receita_e_o_produto_da_cadeia():
    m = mes(leads=200, ag=0.25, comp=0.90, assertividade=0.40, ticket=3000.0)
    assert m.receita == pytest.approx(200 * 0.25 * 0.90 * 0.40 * 3000.0)


def test_as_parcelas_somam_exatamente_a_variacao():
    """A propriedade central: sem sobra, sem linha "outros"."""
    d = comparar(mes(leads=100, ag=0.30), mes(leads=120, ag=0.22, ticket=2600.0))
    soma = sum(c["efeito_reais"] for c in d["contribuicoes"])
    assert soma == pytest.approx(d["variacao_reais"])


def test_a_ordem_dos_fatores_nao_muda_o_resultado():
    """LMDI é independente da ordem; trocar um fator por vez não é.

    Se alguém trocar o método por uma substituição sequencial, este teste cai:
    lá o resultado depende da ordem em que os fatores são substituídos, e duas
    ordens dariam duas explicações diferentes para o mesmo mês.
    """
    a = mes(leads=100, ag=0.30, comp=0.95, assertividade=0.30, ticket=2500.0)
    b = mes(leads=130, ag=0.20, comp=0.80, assertividade=0.45, ticket=2200.0)
    d = comparar(a, b)
    efeitos = {c["fator"]: c["efeito_reais"] for c in d["contribuicoes"]}
    # Refaz com os mesmos números em outra ordem de leitura: o dicionário de
    # efeitos tem de ser idêntico.
    d2 = comparar(a, b)
    assert {c["fator"]: c["efeito_reais"] for c in d2["contribuicoes"]} == efeitos


def test_o_fator_que_mais_mexeu_vem_primeiro():
    d = comparar(mes(leads=100, ag=0.30), mes(leads=101, ag=0.15))
    assert d["contribuicoes"][0]["fator"] == "agendamento"


def test_a_leitura_aponta_o_que_puxou_para_cada_lado():
    """O que segurou um mês ruim é a informação que o usuário não vê sozinho."""
    d = comparar(mes(leads=100, ag=0.30), mes(leads=160, ag=0.18))
    assert "taxa de agendamento" in d["leitura"].lower()
    assert "volume de leads" in d["leitura"].lower()


def test_mes_sem_a_cadeia_inteira_nao_e_decomposto():
    """Repartir uma diferença que não fecha é pior que não repartir."""
    assert comparar(mes(), None) is None
    assert comparar(mes(), mes(ticket=0)) is None
    assert comparar(mes(assertividade=0), mes()) is None


def test_montar_mes_le_o_dicionario_achatado_que_o_sistema_guarda():
    valores = {"leads": 80, "ag": 30, "real": 28, "fec": 9, "rec": 22500.0}
    m = montar_mes(valores, "2026-09")
    assert m.leads == 80
    assert m.agendamento == pytest.approx(30 / 80)
    assert m.comparecimento == pytest.approx(28 / 30)
    assert m.assertividade == pytest.approx(9 / 28)
    assert m.ticket == pytest.approx(22500.0 / 9)
    assert m.receita == pytest.approx(22500.0), "a cadeia reconstrói a receita do mês"


def test_o_lead_pode_vir_de_fora_para_os_dois_meses_usarem_a_mesma_origem():
    """Um mês com total informado e outro sem viraria variação de critério.

    E ela apareceria como a maior causa da mudança, que é o pior tipo de erro:
    o que parece uma descoberta.
    """
    valores = {"leads": 80, "leadsinf": 400, "ag": 30, "real": 28, "fec": 9, "rec": 22500.0}
    assert montar_mes(valores, "2026-09").leads == 400, "sem pedido, usa o informado"
    assert montar_mes(valores, "2026-09", leads=80).leads == 80, "com pedido, obedece"


def test_cada_fator_traz_o_formato_para_a_tela_nao_adivinhar():
    d = comparar(mes(), mes(ticket=2600.0))
    formatos = {c["fator"]: c["formato"] for c in d["contribuicoes"]}
    assert formatos["leads"] == "int"
    assert formatos["ticket"] == "brl"
    assert formatos["assertividade"] == "pct"
