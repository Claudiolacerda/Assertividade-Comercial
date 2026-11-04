"""A projeção do efeito do investimento, e as recusas que ela precisa fazer.

Este é o módulo do sistema com mais chance de enganar alguém. Ele responde "e
se eu investir mais", que é a pergunta cuja resposta errada custa dinheiro de
verdade, e responde com uma reta — que parece ciência mesmo quando é desenho.

Por isso metade destes testes não verifica contas: verifica recusas. Dois
pontos não viram regressão, investimento parado não ensina nada sobre mudar o
investimento, e um cenário fora do que já foi praticado sai marcado como tal.
"""

from __future__ import annotations

import pytest

from app.core.projecao import MINIMO_MESES, ajustar, projetar


def meses(pares: list[tuple[str, float, float]]) -> list[dict]:
    """(mês, investimento, fechados) -> pontos, com receita e leads coerentes."""
    return [
        {"mes_referencia": m, "inv": inv, "fec": fec, "rec": fec * 2500.0, "leads": inv / 45}
        for m, inv, fec in pares
    ]


# De propósito NÃO é uma reta exata: dados perfeitos dão resíduo zero, margem
# zero, e os testes de intervalo passariam sem medir nada.
SUBINDO = meses(
    [
        ("2026-05", 2000.0, 5),
        ("2026-06", 3000.0, 7),
        ("2026-07", 2500.0, 5),
        ("2026-08", 4000.0, 10),
        ("2026-09", 3500.0, 8),
    ]
)


# --------------------------------------------------------------------- #
# A conta
# --------------------------------------------------------------------- #
def test_a_reta_encontra_a_relacao_que_existe_nos_dados():
    """Dados gerados de uma reta exata têm de devolver essa reta."""
    x = [1000.0, 2000.0, 3000.0, 4000.0]
    reta = ajustar(x, [2 + 0.003 * v for v in x])
    assert reta is not None
    assert reta.b == pytest.approx(0.003)
    assert reta.a == pytest.approx(2.0)
    assert reta.r2 == pytest.approx(1.0)


def test_o_efeito_e_publicado_por_mil_reais():
    """"0,002 cliente por real" não se lê; "2 clientes por mil reais" se lê."""
    p = projetar(SUBINDO)
    assert p["modelos"]["fec"]["por_mil"] == pytest.approx(
        p["modelos"]["fec"]["inclinacao"] * 1000
    )


def test_os_cenarios_partem_do_investimento_do_ultimo_mes():
    p = projetar(SUBINDO)
    assert p["investimento_atual"] == 3500.0
    hoje = next(c for c in p["cenarios"] if c["variacao"] == 0)
    assert hoje["investimento"] == 3500.0
    mais30 = next(c for c in p["cenarios"] if c["variacao"] == pytest.approx(0.3))
    assert mais30["investimento"] == pytest.approx(4550.0)


def test_mais_investimento_preve_mais_resultado_quando_a_reta_sobe():
    p = projetar(SUBINDO)
    valores = [c["fec"]["valor"] for c in p["cenarios"]]
    assert valores == sorted(valores)


def test_a_faixa_de_previsao_acompanha_o_valor():
    p = projetar(SUBINDO)
    for c in p["cenarios"]:
        assert c["fec"]["min"] <= c["fec"]["valor"] <= c["fec"]["max"]


def test_a_faixa_abre_conforme_se_afasta_do_meio():
    """Prever longe do que se viu é mais incerto, e a conta sabe disso."""
    p = projetar(SUBINDO)
    largura = lambda c: c["fec"]["max"] - c["fec"]["min"]  # noqa: E731
    perto = next(c for c in p["cenarios"] if c["variacao"] == 0)
    longe = next(c for c in p["cenarios"] if c["variacao"] == pytest.approx(0.5))
    assert largura(longe) > largura(perto)


def test_previsao_nunca_sai_negativa():
    """A reta pode cruzar o zero; "-1,2 cliente" na tela destrói o resto."""
    caindo = meses([("2026-05", 1000.0, 9), ("2026-06", 2000.0, 5), ("2026-07", 3000.0, 1)])
    p = projetar(caindo)
    for c in p["cenarios"]:
        assert c["fec"]["valor"] >= 0 and c["fec"]["min"] >= 0


# --------------------------------------------------------------------- #
# As recusas
# --------------------------------------------------------------------- #
def test_dois_meses_nao_viram_regressao():
    """Com dois pontos a reta é exata, o R² dá 1 e a margem some.

    É a previsão que parece mais perfeita exatamente quando é mais frágil, e
    por isso o módulo se recusa a fazê-la.
    """
    p = projetar(meses([("2026-08", 3000.0, 7), ("2026-09", 4000.0, 9)]))
    assert p["metodo"] == "regra_de_tres"
    assert str(MINIMO_MESES) in p["motivo"]
    assert any("regra de três" in a for a in p["avisos"])


def test_a_regra_de_tres_ainda_responde_alguma_coisa():
    """Melhor que a tela vazia: o ritmo médio, dito como ritmo médio."""
    p = projetar(meses([("2026-08", 3000.0, 6), ("2026-09", 3000.0, 6)]))
    assert p["metodo"] == "regra_de_tres"
    hoje = next(c for c in p["cenarios"] if c["variacao"] == 0)
    assert hoje["fec"]["valor"] == pytest.approx(6.0)
    assert hoje["fec"]["min"] is None, "regra de três não tem intervalo de confiança"


def test_investimento_parado_nao_ensina_nada_sobre_muda_lo():
    """Quatro meses gastando o mesmo não dizem o que acontece se mudar."""
    p = projetar(meses([(f"2026-0{m}", 3000.0, 5 + m) for m in (5, 6, 7, 8)]))
    assert p["metodo"] == "regra_de_tres"
    assert "mesmo em todos os meses" in p["motivo"]


def test_sem_nenhum_mes_nao_ha_projecao():
    assert projetar([])["metodo"] == "insuficiente"
    assert projetar([{"mes_referencia": "2026-09", "inv": 0, "fec": 3}])["metodo"] == "insuficiente"


def test_reta_que_desce_nao_sustenta_promessa_de_aumento():
    """Investir mais e vender menos é um achado, não um motivo para esconder."""
    p = projetar(meses([("2026-05", 1000.0, 9), ("2026-06", 2000.0, 7), ("2026-07", 3000.0, 4)]))
    assert p["metodo"] == "regressao"
    modelo = p["modelos"]["fec"]
    assert modelo["confiavel"] is False
    assert "não veio junto com mais" in modelo["aviso"]


def test_relacao_fraca_e_mostrada_com_o_tamanho_da_fraqueza():
    """R² baixo não é motivo para esconder: é motivo para dizer o número."""
    # Sobe no geral (a inclinação é positiva), mas os pontos não formam reta
    # nenhuma: é o caso em que o número existe e não vale muito.
    baguncado = meses(
        [
            ("2026-05", 1000.0, 3),
            ("2026-06", 2000.0, 9),
            ("2026-07", 3000.0, 5),
            ("2026-08", 4000.0, 10),
        ]
    )
    modelo = projetar(baguncado)["modelos"]["fec"]
    assert modelo["confiavel"] is False
    assert "explica só" in modelo["aviso"]


def test_cenario_fora_do_ja_praticado_sai_marcado():
    """Dobrar a verba raramente dobra o resultado, e a tela precisa avisar."""
    p = projetar(SUBINDO)
    assert p["faixa_observada"] == {"min": 2000.0, "max": 4000.0}
    dentro = next(c for c in p["cenarios"] if c["variacao"] == 0)
    fora = next(c for c in p["cenarios"] if c["variacao"] == pytest.approx(0.5))
    assert dentro["fora_do_historico"] is False
    assert fora["fora_do_historico"] is True


def test_poucos_meses_avisam_mesmo_quando_a_reta_e_boa():
    p = projetar(meses([("2026-07", 2000.0, 4), ("2026-08", 3000.0, 6), ("2026-09", 4000.0, 8)]))
    assert p["modelos"]["fec"]["confiavel"] is True
    assert "3 meses" in p["modelos"]["fec"]["aviso"]


def test_alvo_sem_dado_nao_entra_na_conta():
    """Planilha sem coluna de valor não tem receita, e isso não derruba o resto."""
    pontos = [{**p, "rec": None} for p in SUBINDO]
    p = projetar(pontos)
    assert "fec" in p["modelos"] and "rec" not in p["modelos"]
    assert all("rec" not in c for c in p["cenarios"])


def test_alvo_que_nunca_variou_nao_vira_reta_perfeita():
    """Toda venda igual em todo mês: o R² seria 1 por vacuidade."""
    iguais = [{"mes_referencia": f"2026-0{m}", "inv": 1000.0 * m, "fec": 5} for m in (5, 6, 7, 8)]
    assert projetar(iguais)["modelos"]["fec"]["r2"] == 0.0
