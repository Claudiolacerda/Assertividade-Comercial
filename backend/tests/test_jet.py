"""Testes do JET.

O que estes testes protegem, em uma frase: um Score baixo tem de significar
mês ruim, e um Score alto tem de significar mês bom. Os dois jeitos de quebrar
isso são premiar uma lacuna de registro (CAC zero porque ninguém fechou) e
castigar uma meta que o cliente não escreveu. Quase todo teste aqui é sobre
um desses dois.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.core import ConfigAnalise, analisar
from app.core.jet import PESOS_PILAR, avaliar
from app.core.leitura import _para_numero_meta, ler_metas_da_planilha
from app.core.modelo import METAS_DA_PLANILHA, gerar_planilha_modelo

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"
REUNIOES = DADOS / "reunioes" / "Controle_Comercial_Exemplo_-_Setembro.csv"


# --------------------------------------------------------------------- #
# Um Resultado de mentira, para montar o cenário exato de cada teste sem
# depender de uma planilha que tenha aquele formato de problema.
# --------------------------------------------------------------------- #
@dataclass
class ResFalso:
    valores: dict[str, float]
    tem_valor: bool = True
    tabelas: dict[str, pd.DataFrame] = field(default_factory=dict)
    config: Any = field(default_factory=ConfigAnalise)

    @property
    def kpis(self) -> dict[str, dict[str, Any]]:
        return {k: {"rotulo": k} for k in self.valores}

    def kpi(self, chave: str) -> float:
        return float(self.valores.get(chave, 0.0))


def montar(metas: dict[str, float] | None = None, **valores) -> ResFalso:
    base = {"rec": 0, "fec": 0, "cac": 0, "cpl": 0, "leads": 0, "roas": 0, "assert": 0,
            "comp": 0, "win": 0, "l2r": 0, "ctr": 0, "inv": 0, "imp": 0, "real": 0,
            "per": 0, "ns": 0, "rem": 0, "ag": 0, "sd": 0, "fecp": 0}
    base.update(valores)
    cfg = ConfigAnalise()
    if metas:
        cfg.metas = {**cfg.metas, **metas}
    return ResFalso(valores=base, config=cfg)


# --------------------------------------------------------------------- #
# A armadilha central: denominador vazio não é nota cheia
# --------------------------------------------------------------------- #
def test_cac_zero_por_falta_de_fechamento_nao_pontua_cheio():
    """CAC é investimento ÷ fechados, e vem 0,0 quando ninguém fechou.

    Zero real por cliente é aritmeticamente o melhor CAC possível e na prática
    o pior mês possível. Se este teste quebrar, o JET está dando nota máxima
    para quem não vendeu nada.
    """
    res = montar(metas={"cac_max": 800}, inv=5000, fecp=0, cac=0.0)
    jet = avaliar(res)
    cac = next(i for i in jet.indicadores if i["chave"] == "cac")
    assert cac["pontuado"] is True, "deveria contar, e contar como fracasso"
    assert cac["atingimento"] == 0.0
    assert cac["custo"] == pytest.approx(12.0)


def test_cac_dentro_do_teto_pontua_cheio():
    res = montar(metas={"cac_max": 800}, inv=4000, fecp=10, cac=400.0)
    cac = next(i for i in avaliar(res).indicadores if i["chave"] == "cac")
    assert cac["atingimento"] == 100.0 and cac["custo"] == 0.0


def test_cac_no_dobro_do_teto_pontua_metade():
    res = montar(metas={"cac_max": 800}, inv=16000, fecp=10, cac=1600.0)
    cac = next(i for i in avaliar(res).indicadores if i["chave"] == "cac")
    assert cac["atingimento"] == pytest.approx(50.0)


def test_cpl_zero_sem_lead_nao_pontua_cheio():
    res = montar(metas={"cpl_max": 40}, inv=3000, leads=0, cpl=0.0)
    cpl = next(i for i in avaliar(res).indicadores if i["chave"] == "cpl")
    assert cpl["pontuado"] is True and cpl["atingimento"] == 0.0


def test_comparecimento_nao_pontua_quando_ninguem_registra_ausencia():
    """100% de comparecimento numa planilha sem no-show é falta de registro."""
    res = montar(metas={"comparecimento": 0.70}, real=20, ns=0, rem=0, comp=1.0)
    comp = next(i for i in avaliar(res).indicadores if i["chave"] == "comp")
    assert comp["pontuado"] is False
    assert "não registra no-show" in comp["motivo_fora"]


def test_comparecimento_pontua_quando_ha_uma_ausencia_registrada():
    res = montar(metas={"comparecimento": 0.70}, real=19, ns=1, rem=0, comp=0.95)
    comp = next(i for i in avaliar(res).indicadores if i["chave"] == "comp")
    assert comp["pontuado"] is True and comp["atingimento"] == 100.0


def test_win_rate_fora_quando_nenhuma_perda_foi_registrada():
    res = montar(metas={"win_rate": 0.40}, fec=5, per=0, win=1.0)
    win = next(i for i in avaliar(res).indicadores if i["chave"] == "win")
    assert win["pontuado"] is False and "perda" in win["motivo_fora"]


# --------------------------------------------------------------------- #
# A outra armadilha: meta em branco não é mês ruim
# --------------------------------------------------------------------- #
def test_meta_nao_preenchida_sai_do_calculo_em_vez_de_zerar():
    """Sem meta de faturamento, o pilar Resultado sai e os pesos renormalizam.

    O mesmo mês, pontuado perfeito no que tem meta, tem de dar 100 — não 60
    por causa dos 40 pontos do pilar que ninguém configurou.
    """
    # Tudo o que tem meta é cumprido com folga, para que o único motivo de o
    # Score não dar 100 seja o pilar que saiu.
    res = montar(
        metas={"receita_mes": 0, "fechamentos_mes": 0, "leads_mes": 0},
        inv=4000, imp=1000, fecp=10, real=20, ns=2, per=3, leads=100,
        cac=400.0, cpl=20.0, roas=4.0, comp=0.9, win=0.5, l2r=0.25, ctr=0.02,
        **{"assert": 0.30},
    )
    jet = avaliar(res)
    resultado = next(p for p in jet.pilares if p["chave"] == "resultado")
    assert resultado["pontuado"] is False and resultado["nota"] is None
    assert jet.score == pytest.approx(100.0)
    assert "faturamento do mês" in jet.metas_ausentes


def test_pesos_renormalizam_para_cem_entre_os_pilares_vivos():
    res = montar(metas={"cac_max": 800, "assertividade": 0.25}, inv=4000, fecp=10, cac=400.0,
                 real=20, **{"assert": 0.25})
    jet = avaliar(res)
    efetivos = [p["peso_efetivo"] for p in jet.pilares if p["pontuado"]]
    assert sum(efetivos) == pytest.approx(100.0, abs=0.2)
    assert all(p["peso_efetivo"] == 0.0 for p in jet.pilares if not p["pontuado"])


def test_sem_nenhuma_meta_o_score_e_zero_e_a_leitura_explica():
    res = montar(metas={k: 0 for k in ConfigAnalise().metas})
    jet = avaliar(res)
    assert jet.score == 0.0
    assert "Preencha a aba Metas" in jet.leitura


def test_leitura_avisa_quando_um_pilar_inteiro_ficou_de_fora():
    res = montar(metas={"cac_max": 800, "assertividade": 0.25}, inv=4000, fecp=10, cac=400.0,
                 real=20, **{"assert": 0.30})
    jet = avaliar(res)
    assert "2 dos 3 pilares" in jet.leitura and "Resultado" in jet.leitura


def test_superar_a_meta_nao_compensa_outra_zerada():
    """Faturar o triplo não paga o CAC estourado: o teto de atingimento é 100%."""
    res = montar(metas={"receita_mes": 10000, "fechamentos_mes": 10}, rec=90000, fec=10)
    resultado = next(p for p in avaliar(res).pilares if p["chave"] == "resultado")
    assert resultado["nota"] == pytest.approx(100.0)
    rec = next(i for i in avaliar(res).indicadores if i["chave"] == "rec")
    assert rec["atingimento"] == 100.0  # 900% entra como 100%


# --------------------------------------------------------------------- #
# Pontos de melhoria
# --------------------------------------------------------------------- #
def test_melhorias_vem_do_que_mais_custou_para_o_que_menos_custou():
    res = montar(
        metas={"cac_max": 800, "assertividade": 0.25, "ctr": 0.01},
        inv=4000, fecp=0, cac=0.0, real=20, imp=1000, ctr=0.009, **{"assert": 0.10},
    )
    custos = [m["custo"] for m in avaliar(res).melhorias if m["tipo"] == "indicador"]
    assert custos == sorted(custos, reverse=True)
    assert custos[0] == pytest.approx(12.0)  # o CAC zerado, de peso 12


def test_lacunas_de_registro_entram_sem_tirar_pontos():
    res = montar(metas={"assertividade": 0.25}, real=20, per=0, ag=20, ns=0, rem=0,
                 **{"assert": 0.30})
    melhorias = avaliar(res).melhorias
    registros = [m for m in melhorias if m["tipo"] == "registro"]
    assert any("Nenhuma perda registrada" in m["titulo"] for m in registros)
    assert all(m["custo"] == 0.0 for m in registros)


# --------------------------------------------------------------------- #
# Nota por campanha
# --------------------------------------------------------------------- #
def test_campanha_sem_lead_nao_vira_a_melhor_do_mes():
    """Custo por lead de uma campanha sem lead vem 0 e pareceria imbatível."""
    res = montar(metas={"cpl_max": 40, "ctr": 0.01})
    res.tabelas["meta_campanhas"] = pd.DataFrame([
        {"Campanha": "queimou verba", "Investimento (R$)": 2000.0,
         "Leads / resultados": 0, "Custo por lead (R$)": 0.0, "CTR no link (%)": 0.02},
        {"Campanha": "funcionou", "Investimento (R$)": 1000.0,
         "Leads / resultados": 50, "Custo por lead (R$)": 20.0, "CTR no link (%)": 0.02},
    ])
    notas = {c["campanha"]: c["nota"] for c in avaliar(res).campanhas}
    assert notas["queimou verba"] < notas["funcionou"]
    assert notas["funcionou"] == pytest.approx(100.0)


def test_campanhas_saem_da_pior_para_a_melhor():
    res = montar(metas={"cpl_max": 40, "ctr": 0.01})
    res.tabelas["meta_campanhas"] = pd.DataFrame([
        {"Campanha": "boa", "Investimento (R$)": 100.0, "Leads / resultados": 10,
         "Custo por lead (R$)": 10.0, "CTR no link (%)": 0.02},
        {"Campanha": "ruim", "Investimento (R$)": 100.0, "Leads / resultados": 1,
         "Custo por lead (R$)": 100.0, "CTR no link (%)": 0.001},
    ])
    campanhas = avaliar(res).campanhas
    assert [c["campanha"] for c in campanhas] == ["ruim", "boa"]


def test_campanha_sem_verba_no_periodo_fica_fora():
    res = montar(metas={"cpl_max": 40})
    res.tabelas["meta_campanhas"] = pd.DataFrame([
        {"Campanha": "pausada", "Investimento (R$)": 0.0, "Leads / resultados": 0,
         "Custo por lead (R$)": 0.0, "CTR no link (%)": 0.0},
    ])
    assert avaliar(res).campanhas == []


def test_nota_por_venda_quando_a_planilha_liga_campanha_a_cliente():
    res = montar(metas={"cac_max": 800, "cpl_max": 40, "lead_para_reuniao": 0.20})
    res.tabelas["campanha_x_vendas"] = pd.DataFrame([
        {"Campanha": "vendeu", "Investimento (R$)": 2000.0, "Leads Meta": 50, "Fechados": 5,
         "CAC (R$)": 400.0, "Custo por lead (R$)": 40.0, "Lead → reunião (%)": 0.30},
    ])
    campanha = avaliar(res).campanhas[0]
    assert campanha["base"] == "venda" and campanha["fechados"] == 5
    assert campanha["nota"] == pytest.approx(100.0)


# --------------------------------------------------------------------- #
# A aba Metas da planilha
# --------------------------------------------------------------------- #
def test_numero_da_meta_aceita_o_que_o_excel_e_o_humano_escrevem():
    assert _para_numero_meta(0.25) == 0.25  # float do Excel passa inteiro
    assert _para_numero_meta(2500.5) == 2500.5  # e não vira 25005
    assert _para_numero_meta("R$ 1.234,56") == 1234.56
    assert _para_numero_meta("1234.56") == 1234.56
    assert _para_numero_meta("") is None
    assert _para_numero_meta("abc") is None
    assert _para_numero_meta(True) is None


def test_aba_metas_do_modelo_volta_inteira_na_leitura(tmp_path):
    arq = tmp_path / "modelo.xlsx"
    gerar_planilha_modelo(arq)
    lidas = ler_metas_da_planilha([arq])
    esperado = {chave: exemplo for chave, _r, _f, _e, exemplo in METAS_DA_PLANILHA}
    assert lidas == pytest.approx(esperado)


def test_planilha_sem_aba_metas_nao_quebra(tmp_path):
    import openpyxl

    wb = openpyxl.Workbook()
    wb.active["A1"] = "nada a ver"
    arq = tmp_path / "outra.xlsx"
    wb.save(arq)
    assert ler_metas_da_planilha([arq]) == {}


def test_csv_nao_tem_aba_e_e_ignorado_em_silencio():
    assert ler_metas_da_planilha([REUNIOES]) == {}


def test_porcentagem_digitada_como_inteiro_vira_fracao(tmp_path):
    """Quem digita 25 numa célula sem formato quer 25%, não 2500%."""
    import openpyxl

    from app.core.modelo import ABA_METAS

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = ABA_METAS
    ws["A1"] = "Assertividade esperada (%)"
    ws["B1"] = 25
    arq = tmp_path / "metas.xlsx"
    wb.save(arq)
    assert ler_metas_da_planilha([arq])["assertividade"] == pytest.approx(0.25)


# --------------------------------------------------------------------- #
# Ponta a ponta, na planilha de exemplo
# --------------------------------------------------------------------- #
@pytest.mark.skipif(not (META.exists() and REUNIOES.exists()), reason="exemplos indisponíveis")
def test_jet_roda_na_planilha_de_exemplo():
    jet = analisar([META], [REUNIOES]).jet
    assert 0 <= jet["score"] <= 100
    assert jet["faixa"] in {"excelente", "bom", "atencao", "critico"}
    assert len(jet["pilares"]) == len(PESOS_PILAR)
    # sem coluna de valor e sem metas de volume, o pilar Resultado não pontua
    resultado = next(p for p in jet["pilares"] if p["chave"] == "resultado")
    assert resultado["pontuado"] is False
    assert "2 dos 3 pilares" in jet["leitura"]


@pytest.mark.skipif(not (META.exists() and REUNIOES.exists()), reason="exemplos indisponíveis")
def test_metas_da_planilha_vencem_as_da_configuracao():
    cfg = ConfigAnalise()
    cfg.metas = {**cfg.metas, "assertividade": 0.90}  # meta inalcançável
    jet = analisar([META], [REUNIOES], cfg).jet
    ind = next(i for i in jet["indicadores"] if i["chave"] == "assert")
    assert ind["meta"] == pytest.approx(0.90)
    assert ind["atingimento"] < 100.0
