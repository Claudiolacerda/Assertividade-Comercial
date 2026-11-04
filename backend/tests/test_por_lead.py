"""Quantos leads custa cada resultado.

A taxa de agendamento responde "8,7%", e ninguém planeja mídia com isso. A
mesma medida de cabeça para baixo responde "11,4 leads por reunião", e essa
multiplica: três vendas no mês pedem tantos leads, que pedem tanto de
investimento. É o mesmo dado em formato de decisão.

Duas regras atravessam este arquivo:

1. Numerador e denominador no mesmo universo. Com o total de leads informado,
   é tudo que entrou contra todas as reuniões e vendas; sem ele, são os leads
   da Meta contra o que veio do tráfego pago. Leads só do anúncio divididos por
   vendas de qualquer origem dariam um número otimista e falso, que é o pior
   tipo de erro.
2. Sem denominador, o indicador não existe. "0 leads por venda" num mês sem
   venda nenhuma seria lido como o melhor mês da história.
"""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl
import pytest

from app.core import analisar
from app.core.modelo import ABA_FUNIL, gerar_planilha_modelo

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"
REUNIOES = DADOS / "reunioes" / "Controle_Comercial_Exemplo_-_Setembro.csv"

pytestmark = pytest.mark.skipif(
    not (META.exists() and REUNIOES.exists()), reason="exemplos indisponíveis"
)


@pytest.fixture(scope="module")
def sem_informar():
    """O caso de toda análise que já existe: ninguém informou o total de leads."""
    return analisar([META], [REUNIOES])


def _com_leads(tmp_path: Path, leads: int) -> Path:
    """Uma planilha-modelo só com a aba Funil preenchida, para somar ao CSV."""
    arq = tmp_path / "funil.xlsx"
    gerar_planilha_modelo(arq)
    wb = openpyxl.load_workbook(arq)
    ws = wb["Reuniões"]
    for linha in range(5, 30):
        for coluna in range(1, 20):
            ws.cell(linha, coluna).value = None
    wb[ABA_FUNIL].cell(5, 2).value = leads
    wb[ABA_FUNIL].cell(6, 2).value = None
    wb.save(arq)
    return arq


# --------------------------------------------------------------------- #
# A aritmética
# --------------------------------------------------------------------- #
def test_sem_o_total_informado_a_base_e_o_trafego_pago(sem_informar):
    """Leads da Meta contra reuniões e vendas do tráfego pago."""
    res = sem_informar
    leads, agp, fecp = res.kpi("leads"), res.kpi("agp"), res.kpi("fecp")
    assert leads > 0 and agp > 0 and fecp > 0, "o exemplo precisa ter os três"
    assert res.kpi("lpag") == pytest.approx(leads / agp)
    assert res.kpi("lpfec") == pytest.approx(leads / fecp)
    assert res.kpi("agfec") == pytest.approx(agp / fecp)


def test_com_o_total_informado_a_base_passa_a_ser_todas_as_origens(tmp_path):
    res = analisar([META], [REUNIOES, _com_leads(tmp_path, 412)])
    assert res.kpi("lpag") == pytest.approx(412 / res.kpi("ag"))
    assert res.kpi("lpfec") == pytest.approx(412 / res.kpi("fec"))
    assert res.kpi("agfec") == pytest.approx(res.kpi("ag") / res.kpi("fec"))


def test_a_razao_e_o_inverso_da_taxa(tmp_path):
    """São o mesmo dado: se as duas discordarem, uma delas está errada."""
    res = analisar([META], [REUNIOES, _com_leads(tmp_path, 412)])
    assert res.kpi("lpag") == pytest.approx(1 / res.kpi("txag"))


def test_o_custo_de_uma_venda_fecha_com_o_cac(sem_informar):
    """Os leads de uma venda vezes o CPL têm de dar o CAC.

    É a mesma conta por dois caminhos, e é por isso que o indicador de custo
    não foi duplicado nesta aba: o CAC já é ele.
    """
    res = sem_informar
    assert res.kpi("lpfec") * res.kpi("cpl") == pytest.approx(res.kpi("cac"))


# --------------------------------------------------------------------- #
# Ausência não é zero
# --------------------------------------------------------------------- #
def _csv(tmp_path: Path, linhas: list[list[str]]) -> Path:
    arq = tmp_path / "reunioes.csv"
    with arq.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Cliente", "Etapa do Funil", "Data da Reunião Realizada", "Valor", "Origem"])
        w.writerows(linhas)
    return arq


def test_mes_sem_venda_nao_ganha_zero_leads_por_venda(tmp_path):
    """"0 leads por cliente" seria lido como o melhor mês da história."""
    arq = _csv(
        tmp_path,
        [
            ["Cliente A", "Agendado", "05/09/2026", "0", "Facebook Ads"],
            ["Cliente B", "Follow Up", "06/09/2026", "0", "Facebook Ads"],
        ],
    )
    res = analisar([META], [arq])
    assert "lpag" in res.kpis, "houve reunião marcada, então essa razão existe"
    assert "lpfec" not in res.kpis and "agfec" not in res.kpis


def test_mes_em_que_o_anuncio_nao_marcou_nada_nao_tem_razao_nenhuma(tmp_path):
    """Sem o total informado, a base é paga: nada pago, nada a dividir.

    Um mês em que todas as reuniões vieram de indicação não diz nada sobre
    quantos leads de anúncio custa uma reunião, e a aba inteira desaparece em
    vez de dividir leads pagos por reuniões que não são deles.
    """
    arq = _csv(
        tmp_path,
        [
            ["Cliente A", "Fechado", "05/09/2026", "2500,00", "Indicação"],
            ["Cliente B", "Agendado", "06/09/2026", "0", "Indicação"],
        ],
    )
    res = analisar([META], [arq])
    assert res.kpi("agp") == 0, "nenhuma reunião do tráfego pago"
    assert "lpag" not in res.kpis and "lpfec" not in res.kpis
    assert not any("QUANTOS LEADS" in titulo for titulo, _ in res.blocos)


def test_informar_o_total_de_leads_resgata_o_mes_sem_trafego_pago(tmp_path):
    """Com a base de todas as origens, o mesmo mês volta a ter razão.

    É o que o número informado compra: ele mede a operação inteira, não só o
    que o anúncio trouxe.
    """
    arq = _csv(
        tmp_path,
        [
            ["Cliente A", "Fechado", "05/09/2026", "2500,00", "Indicação"],
            ["Cliente B", "Agendado", "06/09/2026", "0", "Indicação"],
        ],
    )
    res = analisar([META], [arq, _com_leads(tmp_path, 40)])
    assert res.kpi("lpag") == pytest.approx(40 / 2)
    assert res.kpi("lpfec") == pytest.approx(40 / 1)


# --------------------------------------------------------------------- #
# Meta e apresentação
# --------------------------------------------------------------------- #
def test_a_meta_de_agendamento_entra_invertida_e_como_maximo(sem_informar):
    """20% de agendamento é uma reunião a cada 5 leads, e aqui menos é melhor."""
    k = sem_informar.kpis["lpag"]
    meta_taxa = sem_informar.config.metas["lead_para_reuniao"]
    assert k["meta_tipo"] == "max"
    assert k["meta_valor"] == pytest.approx(1 / meta_taxa)


def test_o_bloco_aparece_na_lista_de_blocos(sem_informar):
    titulo, chaves = next(
        (t, ks) for t, ks in sem_informar.blocos if "QUANTOS LEADS" in t
    )
    assert chaves == ["lpag", "agfec", "lpfec"]


def test_o_numero_sai_com_a_pontuacao_brasileira(sem_informar):
    """Um "11.4" numa tela em português é um número de 11 mil e 4 décimos."""
    texto = sem_informar.kpis["lpag"]["texto"]
    assert "," in texto and "." not in texto.split(",")[-1]


def test_a_planilha_entregue_nao_quebra_com_o_formato_novo(sem_informar):
    """A aba de KPIs lê FMT[formato] direto: um formato sem entrada derruba tudo."""
    import io

    from app.core.excel import gerar_excel

    wb = openpyxl.load_workbook(io.BytesIO(gerar_excel(sem_informar)))
    ws = wb["Resumo Executivo"]
    texto = " ".join(str(c.value) for linha in ws.iter_rows() for c in linha if c.value)
    assert "Leads para 1 reunião marcada" in texto


# --------------------------------------------------------------------- #
# Qual base foi usada: a tela precisa saber
# --------------------------------------------------------------------- #
def test_o_resultado_diz_qual_base_usou(sem_informar, tmp_path):
    """Nos dois casos a razão está certa, mas só uma multiplica pelo CPL.

    Com os leads informados, eles contam indicação e orgânico, que não têm
    custo de mídia. A tela só pode escrever "leads a gerar (todas as origens)"
    e tirar o orçamento do CAC se souber disso.
    """
    assert sem_informar.base_esforco == "paga"
    com = analisar([META], [REUNIOES, _com_leads(tmp_path, 412)])
    assert com.base_esforco == "informada"
    assert com.to_payload()["base_esforco"] == "informada"


def test_sem_razao_nenhuma_a_base_fica_vazia(tmp_path):
    """Para a tela não anunciar uma base que não foi usada para nada."""
    arq = _csv(tmp_path, [["Cliente A", "Agendado", "05/09/2026", "0", "Indicação"]])
    assert analisar([META], [arq]).base_esforco == ""
