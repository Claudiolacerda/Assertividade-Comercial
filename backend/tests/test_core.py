"""Testes do motor de análise usando os dados reais de setembro/2026.

Estes números são a referência: se um refactor mudar qualquer um deles, o teste
quebra. É o que permite mexer no motor sem medo de entregar número errado ao cliente.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.core import ConfigAnalise, analisar, gerar_excel
from app.core.leitura import montar_tabela
from app.core.pipeline import ErroDeAnalise
from app.core.texto import para_data, para_numero

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "_CA_-Conta-ilidade-Horizonte-Campanhas-1-de-set-de-2026-24-de-set-de-2026.csv"
REUNIOES = DADOS / "reunioes" / "Controle_Comercial_Horizonte_-_Setembro.csv"

pytestmark = pytest.mark.skipif(
    not (META.exists() and REUNIOES.exists()), reason="arquivos de exemplo não disponíveis"
)


@pytest.fixture(scope="module")
def res():
    return analisar([META], [REUNIOES])


# --------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------- #
def test_periodo_detectado_automaticamente(res):
    assert res.mes_referencia == "2026-09"
    assert res.nome_mes == "setembro/2026"


def test_planilha_sem_coluna_de_valor(res):
    """Sem coluna de valor o sistema omite receita/ROAS em vez de mostrar zero."""
    assert res.tem_valor is False
    assert "roas" not in res.kpis
    assert "rec" not in res.kpis


def test_le_painel_em_blocos_por_semana(res):
    """As 4 'Semana N' da planilha viram um campo, e as linhas de legenda são descartadas."""
    semanas = set(res.tabelas["por_semana"]["Semana"])
    assert semanas == {"Semana 1", "Semana 2", "Semana 3", "Semana 4"}
    assert res.kpis["ag"]["valor"] == 36


def test_para_numero_aceita_formato_brasileiro():
    s = para_numero(pd.Series(["R$ 1.500,00", "1,5", "12%", "2.252,05", "", None]))
    assert list(s[:4]) == [1500.0, 1.5, 12.0, 2252.05]
    assert s[4:].isna().all()


def test_para_data_aceita_datas_sujas():
    s = para_data(pd.Series(["08/09/ 2026", "17/09/", "2026-09-01", "31/08"]), ano_padrao=2026)
    assert [d.strftime("%Y-%m-%d") for d in s] == ["2026-09-08", "2026-09-17", "2026-09-01", "2026-08-31"]


def test_montar_tabela_sem_cabecalho_reconhecido():
    bruto = pd.DataFrame([["qualquer", "coisa"], ["1", "2"]])
    df, blocos = montar_tabela(bruto, [["cliente"], ["status"]])
    assert df is None and blocos is False


# --------------------------------------------------------------------- #
# KPIs — números de referência
# --------------------------------------------------------------------- #
def test_kpis_de_trafego(res):
    assert res.kpi("inv") == pytest.approx(3651.02, abs=0.01)
    assert res.kpi("imp") == 144456
    assert res.kpi("clq") == 516
    assert res.kpi("leads") == 81
    assert res.kpi("cpl") == pytest.approx(45.07, abs=0.01)
    assert res.kpi("ctr") == pytest.approx(0.00357, abs=0.0001)


def test_kpis_comerciais(res):
    assert res.kpi("ag") == 36
    assert res.kpi("real") == 35
    assert res.kpi("fec") == 9
    assert res.kpi("neg") == 4
    assert res.kpi("sd") == 22
    assert res.kpi("fut") == 1  # 'Agendado' fica fora das taxas


def test_assertividade_nao_repete_o_erro_da_planilha(res):
    """A planilha do cliente calcula 400% na semana 4; o motor calcula 25,7% no mês."""
    assert res.kpi("assert") == pytest.approx(9 / 35, abs=0.001)
    assert res.kpi("assert") < 1.0


def test_cac_cruza_meta_com_comercial(res):
    assert res.kpi("cac") == pytest.approx(3651.02 / 9, abs=0.01)
    assert res.kpi("cpr") == pytest.approx(3651.02 / 35, abs=0.01)


def test_metas_marcam_situacao(res):
    assert res.kpis["ctr"]["dentro_da_meta"] is False  # 0,4% < 1,0%
    assert res.kpis["cpl"]["dentro_da_meta"] is False  # R$ 45,07 > R$ 40,00
    assert res.kpis["assert"]["dentro_da_meta"] is True  # 25,7% >= 25,0%
    assert res.kpis["cac"]["dentro_da_meta"] is True  # R$ 405,67 <= R$ 800,00


def test_metas_customizadas_mudam_a_avaliacao():
    cfg = ConfigAnalise(metas={**ConfigAnalise().metas, "assertividade": 0.40})
    r = analisar([META], [REUNIOES], cfg)
    assert r.kpis["assert"]["dentro_da_meta"] is False


# --------------------------------------------------------------------- #
# Diagnóstico automático
# --------------------------------------------------------------------- #
def test_diagnostico_aponta_campanha_sem_resultado_e_cpl(res):
    textos = " ".join(res.diagnostico["Diagnóstico"])
    assert "Menor CPL" in textos
    assert "Nenhuma reunião está marcada como perdida" in textos
    assert "sem coluna de valor" in textos or "não tem coluna de valor" in textos


def test_diagnostico_desconfia_de_fechamento_inconsistente(res):
    """Fechados cuja observação diz 'vai decidir' viram alerta com a assertividade corrigida."""
    alerta = [d for d in res.diagnostico["Diagnóstico"] if "marcados como Fechado" in d]
    assert alerta, "esperava o alerta de fechamento suspeito"
    assert "17,1%" in alerta[0]


def test_diagnostico_separa_marcacao_do_cac(res):
    alerta = [d for d in res.diagnostico["Diagnóstico"] if "Parceiro" in d]
    assert alerta, "esperava o alerta de marcação no nome afetando o CAC"


def test_pipeline_classifica_temperatura(res):
    pipe = res.tabelas["pipeline"]
    assert len(pipe) == 26
    assert (pipe["Temperatura"] == "🔥 Quente").sum() == 7


def test_qualidade_lista_problemas_linha_a_linha(res):
    assert len(res.qualidade) > 0
    assert set(res.resumo_qualidade.columns) == {"Problema", "Ocorrências"}
    assert "Fechado, mas a observação sugere que ainda não fechou" in set(res.qualidade["Problema"])


def test_mapeamento_mostra_colunas_reconhecidas(res):
    mapa = res.mapeamento
    linha = mapa[(mapa["Base"] == "Reuniões") & (mapa["Campo do sistema"] == "responsavel")]
    assert linha.iloc[0]["Coluna encontrada no arquivo"] == "Quem fez"


# --------------------------------------------------------------------- #
# Saídas
# --------------------------------------------------------------------- #
def test_payload_e_serializavel(res):
    import json

    payload = res.to_payload()
    texto = json.dumps(payload)  # não deve levantar
    assert '"kpis"' in texto
    assert payload["kpis"]["assert"]["texto"] == "25,7%"


def test_excel_gerado_tem_as_abas_e_formulas(res):
    dados = gerar_excel(res)
    assert dados[:2] == b"PK"  # xlsx é um zip
    with zipfile.ZipFile(BytesIO(dados)) as z:
        nomes = z.namelist()
        assert any("worksheets/sheet1.xml" in n for n in nomes)
        conteudo = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "IFERROR" in conteudo  # taxas vão como fórmula viva, não número congelado


# --------------------------------------------------------------------- #
# Erros com mensagem para o usuário final
# --------------------------------------------------------------------- #
def test_arquivo_invalido_gera_erro_explicativo(tmp_path):
    ruim = tmp_path / "qualquer.csv"
    ruim.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ErroDeAnalise) as e:
        analisar([ruim], [REUNIOES])
    assert "Meta" in str(e.value)


def test_mes_sem_reunioes_gera_erro_explicativo():
    """Com filtro por data ligado, um mês sem reuniões é erro e não relatório vazio."""
    cfg = ConfigAnalise(mes_referencia="2025-01", filtrar_reunioes_por_data=True)
    with pytest.raises(ErroDeAnalise) as e:
        analisar([META], [REUNIOES], cfg)
    assert "Nenhuma reunião" in str(e.value)


def test_mes_errado_em_painel_por_semanas_gera_aviso():
    """Painel por semanas não filtra por data — então o mês errado tem que ser avisado."""
    r = analisar([META], [REUNIOES], ConfigAnalise(mes_referencia="2025-01"))
    assert any("confirme se o mês está certo" in a for a in r.avisos)
