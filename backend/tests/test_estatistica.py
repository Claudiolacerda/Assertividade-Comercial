"""Quanto de uma taxa é medição e quanto é sorteio.

O sistema dizia "assertividade 25,7%, meta 30%, FORA DA META" sobre 9
fechamentos em 35 reuniões. Com essa amostra, a taxa real está entre 14% e 42%:
a meta cabe inteira dentro da faixa, e a reprovação não se sustenta.

O erro que isso causa é caro e silencioso — o cliente troca vendedor ou corta
verba por causa de uma oscilação que é sorteio, e no mês seguinte ela "melhora"
sozinha, o que confirma a decisão errada e ensina a repetir.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core import analisar
from app.core.estatistica import MINIMO_PARA_COMPARAR, frase_do_veredito, veredito, wilson

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"
REUNIOES = DADOS / "reunioes" / "Controle_Comercial_Exemplo_-_Setembro.csv"


# --------------------------------------------------------------------- #
# A conta
# --------------------------------------------------------------------- #
def test_a_faixa_cerca_a_taxa_medida():
    f = wilson(9, 35)
    assert f.taxa == pytest.approx(9 / 35)
    assert f.minimo < f.taxa < f.maximo


def test_amostra_maior_estreita_a_faixa():
    """A mesma taxa com dez vezes mais casos é um número muito mais firme."""
    estreita, larga = wilson(90, 350), wilson(9, 35)
    assert estreita.largura < larga.largura / 2


def test_a_faixa_nunca_sai_de_zero_a_um():
    """É onde o intervalo normal simples falha, e por isso aqui é Wilson.

    Com 35 de 35, o normal devolveria limite acima de 100%, que não existe.
    """
    cheia, vazia = wilson(35, 35), wilson(0, 35)
    assert cheia.maximo <= 1.0 and cheia.minimo < 1.0
    assert vazia.minimo >= 0.0 and vazia.maximo > 0.0


def test_sem_denominador_nao_ha_faixa():
    """Zero a zero não é uma taxa de 0%: é ausência de medição."""
    assert wilson(0, 0) is None
    assert wilson(5, 0) is None


# --------------------------------------------------------------------- #
# O veredito
# --------------------------------------------------------------------- #
def test_meta_dentro_da_faixa_e_indistinguivel():
    """O caso que motivou tudo: 9 em 35 contra meta de 30%."""
    assert veredito(wilson(9, 35), 0.30, "min") == "indistinguivel"


def test_meta_acima_da_faixa_inteira_e_reprovacao_de_verdade():
    assert veredito(wilson(9, 350), 0.30, "min") == "fora"


def test_meta_abaixo_da_faixa_inteira_e_aprovacao_de_verdade():
    assert veredito(wilson(140, 350), 0.30, "min") == "dentro"


def test_meta_de_teto_inverte_a_leitura():
    """Numa meta de máximo, ficar ABAIXO é que é estar dentro."""
    assert veredito(wilson(10, 350), 0.10, "max") == "dentro"
    assert veredito(wilson(140, 350), 0.10, "max") == "fora"


def test_amostra_minuscula_nem_tenta_comparar():
    f = wilson(2, MINIMO_PARA_COMPARAR - 1)
    assert veredito(f, 0.30, "min") == "amostra_pequena"


def test_sem_meta_nao_ha_veredito():
    assert veredito(wilson(9, 35), None, None) == "sem_meta"


def test_a_frase_so_aparece_quando_acrescenta():
    """Aprovação e reprovação claras não precisam de nota; dúvida precisa."""
    f = wilson(9, 35)
    assert frase_do_veredito("indistinguivel", f, "Assertividade")
    assert frase_do_veredito("dentro", f, "Assertividade") is None


# --------------------------------------------------------------------- #
# Ligado no motor
# --------------------------------------------------------------------- #
@pytest.mark.skipif(not (META.exists() and REUNIOES.exists()), reason="exemplos indisponíveis")
def test_as_taxas_da_analise_saem_com_faixa_e_veredito():
    res = analisar([META], [REUNIOES])
    for chave in ("assert", "fag", "comp", "l2r"):
        faixa = res.kpis[chave].get("faixa")
        assert faixa, f"{chave} saiu sem faixa"
        assert faixa["n"] > 0
        assert faixa["min"] <= res.kpi(chave) <= faixa["max"]


@pytest.mark.skipif(not (META.exists() and REUNIOES.exists()), reason="exemplos indisponíveis")
def test_a_assertividade_do_exemplo_nao_e_mais_reprovada_sem_base():
    """9 fechamentos em 35 reuniões não reprovam uma meta de 30%.

    A meta vem da configuração do cliente, então o teste fixa 30% para
    reproduzir exatamente o caso: o número cru reprova, a amostra não.
    """
    from dataclasses import replace

    from app.core.config_analise import ConfigAnalise

    cfg = ConfigAnalise()
    cfg = replace(cfg, metas={**cfg.metas, "assertividade": 0.30})
    k = analisar([META], [REUNIOES], cfg).kpis["assert"]
    assert k["dentro_da_meta"] is False, "o número cru continua abaixo da meta"
    assert k["faixa"]["veredito"] == "indistinguivel", "mas a diferença cabe no sorteio"
    assert k["faixa"]["nota"]


@pytest.mark.skipif(not (META.exists() and REUNIOES.exists()), reason="exemplos indisponíveis")
def test_indicador_que_nao_e_proporcao_nao_ganha_faixa():
    """CAC e receita não têm amostra: inventar faixa ali seria falso rigor."""
    res = analisar([META], [REUNIOES])
    assert res.kpis["cac"].get("faixa") is None
    assert res.kpis["cpl"].get("faixa") is None
    assert res.kpis["ag"].get("faixa") is None, "contagem não é proporção"


@pytest.mark.skipif(not (META.exists() and REUNIOES.exists()), reason="exemplos indisponíveis")
def test_o_whatsapp_nao_marca_o_que_nao_da_para_afirmar():
    """No WhatsApp o emoji é lido antes do número."""
    from app.core.relatorio_zap import gerar_texto

    res = analisar([META], [REUNIOES])
    linha = [
        l
        for l in gerar_texto(res.to_payload(), "Cliente", "2026-09").splitlines()
        if "Assertividade" in l
    ]
    assert linha and "⚠️" not in linha[0] and "✅" not in linha[0]


@pytest.mark.skipif(not (META.exists() and REUNIOES.exists()), reason="exemplos indisponíveis")
def test_a_planilha_entregue_nao_contradiz_a_tela():
    """Se o painel diz "não dá para dizer", o Excel não pode dizer "fora".

    A planilha é o que o cliente arquiva e relê depois, então ela é a versão
    que sobrevive. A meta continua editável: os limites da faixa são números
    fixos, porque dependem só dos dados, e a fórmula sabe comparar a meta nova
    com eles.
    """
    import io

    import openpyxl

    from app.core.excel import gerar_excel

    wb = openpyxl.load_workbook(io.BytesIO(gerar_excel(analisar([META], [REUNIOES]))))
    ws = wb["Resumo Executivo"]
    # O título da aba também contém "Assertividade"; a linha do indicador é a
    # que tem explicação preenchida.
    linhas = [
        [c.value for c in linha[:5]]
        for linha in ws.iter_rows()
        if linha[0].value
        and "ASSERTIVIDADE" in str(linha[0].value).upper()
        and linha[2].value
    ]
    assert linhas, "a assertividade tem de estar na planilha"
    rotulo, _valor, explicacao, _meta, situacao = linhas[0]
    assert "faixa provável" in explicacao and "casos" in explicacao
    assert "14,2%" in explicacao, "a planilha é em português"
    assert "Ainda não dá para dizer" in situacao
    assert "IF(AND(D" in situacao, "a fórmula tem de continuar viva quando a meta mudar"
