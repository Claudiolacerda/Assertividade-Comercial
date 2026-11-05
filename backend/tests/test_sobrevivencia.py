"""O ciclo de venda que conta também quem ainda não fechou.

A média do ciclo sempre olhou só para quem fechou. O problema não é o cálculo,
é quem ele deixa de fora: o negócio em negociação há 60 dias não entra em lugar
nenhum. Como os ciclos longos são justamente os que ainda não terminaram, a
média enxerga só os curtos — o viés é sistemático e sempre otimista, e o número
sai bonito exatamente quando a operação está travando.

É o mesmo erro de medir tempo de espera perguntando só a quem já foi atendido.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core import analisar
from app.core.sobrevivencia import Caso, estimar, resumir

FIXTURES = Path(__file__).resolve().parent / "fixtures_crm"
DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"


# --------------------------------------------------------------------- #
# A conta
# --------------------------------------------------------------------- #
def test_sem_censura_a_curva_e_a_contagem_simples():
    """Com todo mundo fechado, Kaplan-Meier tem de concordar com o óbvio."""
    curva = estimar([Caso(10, True), Caso(20, True), Caso(30, True), Caso(40, True)])
    assert curva.ate(20) == pytest.approx(0.5)
    assert curva.ate(40) == pytest.approx(1.0)
    assert curva.mediana == 20


def test_o_negocio_em_aberto_entra_como_informacao_parcial():
    """Ele não fechou, mas sabe-se que passou de X dias sem fechar.

    Descartá-lo (o que a média fazia) joga fora justamente a evidência de que o
    ciclo é mais longo do que os fechamentos sugerem.
    """
    so_fechados = estimar([Caso(10, True), Caso(20, True)])
    com_abertos = estimar([Caso(10, True), Caso(20, True), Caso(90, False), Caso(95, False)])
    assert so_fechados.ate(20) == pytest.approx(1.0)
    assert com_abertos.ate(20) == pytest.approx(0.5), "metade dos acompanhados ainda não fechou"


def test_a_media_simples_e_otimista_e_a_curva_mostra_isso():
    """O caso que motivou o módulo, com números redondos."""
    casos = [Caso(5, True), Caso(12, True), Caso(20, True), Caso(45, True)] + [
        Caso(d, False) for d in (10, 18, 25, 33, 50, 70)
    ]
    media_simples = (5 + 12 + 20 + 45) / 4
    resumo = resumir(estimar(casos), media_ingenua=media_simples)
    assert media_simples == pytest.approx(20.5)
    assert resumo["mediana_dias"] > media_simples, "a curva vê o que a média não vê"


def test_sem_nenhum_fechamento_nao_ha_curva():
    """Uma reta em zero não é estimativa, é ausência de uma."""
    assert estimar([Caso(30, False), Caso(60, False)]) is None
    assert resumir(None) is None


def test_a_curva_nunca_anda_para_tras():
    """Fração acumulada que fechou só pode crescer com o tempo."""
    casos = [Caso(d, d % 3 == 0) for d in range(1, 40)]
    pontos = estimar(casos).pontos
    acumulados = [p["acumulado"] for p in pontos]
    assert acumulados == sorted(acumulados)


def test_os_marcos_saem_na_ordem_e_com_a_leitura():
    resumo = resumir(estimar([Caso(5, True), Caso(40, True), Caso(80, False)]))
    assert [m["dias"] for m in resumo["marcos"]] == [7, 15, 30, 60, 90]
    assert "30 dias" in resumo["leitura"]


def test_ciclo_mais_longo_que_a_janela_nao_inventa_mediana():
    """Dizer "mediana de 90 dias" quando só 28% fecharam seria inventar."""
    casos = [Caso(5, True)] + [Caso(d, False) for d in (30, 40, 50, 60)]
    resumo = resumir(estimar(casos))
    assert resumo["mediana_dias"] is None
    assert "não há mediana" in resumo["leitura"]


# --------------------------------------------------------------------- #
# Ligado no motor
# --------------------------------------------------------------------- #
@pytest.mark.skipif(not META.exists(), reason="exemplo da Meta indisponível")
def test_um_export_de_crm_com_data_de_fechamento_gera_a_curva():
    arq = FIXTURES / "pipedrive_deals_export.csv"
    if not arq.exists():
        pytest.skip("fixture indisponível")
    res = analisar([META], [arq])
    km = res.ciclo_km
    assert km, "o export tem data de fechamento, então a curva tem de existir"
    assert km["n"] > km["fechados"], "os não fechados também entram na conta"
    assert km["em_aberto_ou_perdidos"] > 0
    assert "ciclo_curva" in res.tabelas and "ciclo_marcos" in res.tabelas


@pytest.mark.skipif(not META.exists(), reason="exemplo da Meta indisponível")
def test_planilha_sem_data_de_fechamento_nao_ganha_curva_inventada():
    """É o único dado que a conta exige e o sistema não consegue deduzir."""
    reunioes = DADOS / "reunioes" / "Controle_Comercial_Exemplo_-_Setembro.csv"
    if not reunioes.exists():
        pytest.skip("exemplo de reuniões indisponível")
    res = analisar([META], [reunioes])
    assert res.ciclo_km == {}
    assert "ciclo_curva" not in res.tabelas


@pytest.mark.skipif(not META.exists(), reason="exemplo da Meta indisponível")
def test_a_curva_viaja_no_payload_para_a_tela():
    arq = FIXTURES / "pipedrive_deals_export.csv"
    if not arq.exists():
        pytest.skip("fixture indisponível")
    payload = analisar([META], [arq]).to_payload()
    assert payload["ciclo_km"]["marcos"]


@pytest.mark.skipif(not META.exists(), reason="exemplo da Meta indisponível")
def test_close_date_do_hubspot_e_data_de_fechamento_e_nao_de_reuniao():
    """Ela vivia como apelido de data da reunião, e isso custava o ciclo inteiro.

    O export de CRM quase nunca tem data de reunião: o Close Date era a única
    data de desfecho e era consumida como se fosse a conversa, então o sistema
    nunca enxergava um fechamento datado e nenhum cliente de CRM tinha ciclo de
    venda. O mês continua situado pela data de entrada do lead, com aviso.
    """
    arq = FIXTURES / "hubspot_deals_export.csv"
    if not arq.exists():
        pytest.skip("fixture indisponível")
    res = analisar([META], [arq])
    mapa = res.mapeamento
    linha = mapa[mapa["Campo do sistema"] == "data_fechamento"]
    assert "Close Date" in linha["Coluna encontrada no arquivo"].to_string()
    assert res.ciclo_km, "com a data de fechamento no lugar certo, a curva existe"


def test_a_tela_desenha_a_escada_sem_depender_da_biblioteca():
    """O último degrau precisa de um ponto depois dele para existir.

    Com "stepAfter" do Recharts, o fechamento mais tardio sumia do gráfico
    justamente por ser o último. A escada passa a ser montada a mão, com dois
    pontos por degrau.
    """
    fonte = (
        Path(__file__).resolve().parents[2] / "frontend/src/components/CicloFechamento.tsx"
    ).read_text(encoding="utf-8")
    assert 'type="linear"' in fonte
    assert "dados.push({ dias: ponto.dias, acumulado: anterior })" in fonte
    assert "ReferenceLine" in fonte, "o fim do acompanhamento tem de ficar visível"
