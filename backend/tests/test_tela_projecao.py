"""O cartão de projeção na home.

Não há runner de teste no frontend, então o que dá para garantir daqui é o
contrato: a home chama o endpoint, o cartão recebe os dados, e os três
elementos que impedem a leitura ingênua do número estão na tela — o método
usado, o quanto o investimento explica, e a marca nos cenários nunca testados.

O risco aqui não é o gráfico quebrar: é ele convencer. Uma reta bonita sobre
três pontos convence qualquer um, e é por isso que estes testes olham para as
ressalvas com o mesmo cuidado que olhariam para a conta.
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROJECAO = (RAIZ / "frontend/src/components/Projecao.tsx").read_text(encoding="utf-8")
HISTORICO = (RAIZ / "frontend/src/pages/Historico.tsx").read_text(encoding="utf-8")
API = (RAIZ / "frontend/src/api.ts").read_text(encoding="utf-8")


def test_a_home_busca_e_mostra_a_projecao():
    assert "api.projecao()" in HISTORICO
    assert "<Projecao dados={projecao} />" in HISTORICO
    assert 'requisitar<any>("/analises/projecao")' in API


def test_a_falha_da_projecao_nao_derruba_a_home():
    """Ela é um extra sobre o histórico, e extra nenhum vale a tela inteira."""
    assert "api.projecao().catch(() => null)" in HISTORICO


def test_o_cartao_trata_os_tres_metodos():
    for metodo in ('"insuficiente"', '"regra_de_tres"'):
        assert metodo in PROJECAO
    assert "dados.motivo" in PROJECAO, "a recusa tem de aparecer escrita"


def test_a_regra_de_tres_e_anunciada_como_regra_de_tres():
    """O pior resultado possível aqui é uma proporção parecer uma regressão."""
    assert "Ainda não é uma regressão" in PROJECAO


def test_o_r2_aparece_na_tela():
    """"O investimento explica 96% da variação" é o que calibra a confiança."""
    assert "r2" in PROJECAO and "explica" in PROJECAO


def test_cenario_fora_do_historico_e_marcado():
    assert "fora_do_historico" in PROJECAO and "nunca testado" in PROJECAO


def test_a_tela_diz_que_correlacao_nao_e_causa():
    """A frase que impede a leitura "é só dobrar a verba"."""
    assert "não o que causou o quê" in PROJECAO
    assert "andou junto" in PROJECAO


def test_o_valor_simulado_fora_da_faixa_avisa():
    assert "foraDaFaixa" in PROJECAO and "fora da faixa já praticada" in PROJECAO


def test_a_previsao_nao_finge_precisao_de_centavos():
    """"R$ 15.028,33 no mês que vem" promete o que ninguém pode prever."""
    assert "function previsto" in PROJECAO
    assert "Math.round(valor).toLocaleString" in PROJECAO
