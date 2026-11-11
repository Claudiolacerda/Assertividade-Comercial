"""Fechamentos com etiqueta no nome, separados do resto.

"Rosana - Tayron" na planilha quer dizer que o lead veio por um parceiro. Esses
fechamentos não deveriam entrar na conta do anúncio, e num mês real foram 4 das
10 vendas: 40% do resultado vindo de fora do funil pago, somados ao CAC como se
fossem dele.

O sistema já separava a marcação numa tabela de apoio. O que faltava era o
número na cara de quem lê, e a etiqueta ao lado do nome na lista de
fechamentos — que é como a pergunta chega: "quais vendas vieram pelo parceiro?"
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.core import analisar

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"

pytestmark = pytest.mark.skipif(not META.exists(), reason="exemplo da Meta indisponível")


def _planilha(tmp_path: Path, linhas) -> Path:
    arq = tmp_path / "reunioes.csv"
    with arq.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Cliente", "Etapa do Funil", "Data da Reunião Realizada", "Valor", "Origem"])
        w.writerows(linhas)
    return arq


COM_PARCEIRO = [
    ("Rosana - Tayron", "Fechado", "05/09/2026", "2500", "Facebook Ads"),
    ("Pollyana - Tayron", "Fechado", "08/09/2026", "2500", "Facebook Ads"),
    ("Mercado Sul", "Fechado", "06/09/2026", "1800", "Facebook Ads"),
    ("Bar do João", "Reunião Feita", "07/09/2026", "0", "Facebook Ads"),
    ("Padaria", "Perdido", "09/09/2026", "0", "Facebook Ads"),
]


def test_os_fechados_com_etiqueta_viram_indicador_proprio(tmp_path):
    res = analisar([META], [_planilha(tmp_path, COM_PARCEIRO)])
    assert int(res.kpi("fec")) == 3
    assert int(res.kpi("fecm")) == 2, "os dois do parceiro"
    assert int(res.kpi("fecsm")) == 1, "o que o funil trouxe sozinho"
    assert res.kpi("fecmpct") == pytest.approx(2 / 3)


def test_o_rotulo_nomeia_a_etiqueta_encontrada(tmp_path):
    """Quem lê precisa saber de QUAL parceiro se está falando."""
    res = analisar([META], [_planilha(tmp_path, COM_PARCEIRO)])
    assert "Tayron" in res.kpis["fecm"]["rotulo"]


def test_a_lista_de_fechamentos_mostra_a_etiqueta(tmp_path):
    """É assim que a pergunta chega: "quais vendas vieram pelo parceiro?"."""
    lista = analisar([META], [_planilha(tmp_path, COM_PARCEIRO)]).tabelas["fechamentos"]
    assert "Marcação" in lista.columns
    assert sorted(lista[lista["Marcação"] == "Tayron"]["Cliente"]) == ["Pollyana", "Rosana"]


def test_sem_etiqueta_nenhuma_nada_disso_aparece(tmp_path):
    """Coluna e indicadores que só diriam "(sem marcação)" são ruído."""
    limpa = [("Mercado Sul", "Fechado", "06/09/2026", "1800", "Facebook Ads")]
    res = analisar([META], [_planilha(tmp_path, limpa)])
    assert "fecm" not in res.kpis and "fecsm" not in res.kpis
    assert "Marcação" not in res.tabelas["fechamentos"].columns


def test_o_sistema_avisa_do_efeito_no_cac(tmp_path):
    """O aviso que já existia continua, e agora tem indicador ao lado dele."""
    res = analisar([META], [_planilha(tmp_path, COM_PARCEIRO)])
    texto = " ".join(res.diagnostico["Diagnóstico"])
    assert "Tayron" in texto and "CAC real do anúncio" in texto


def test_marcar_a_etiqueta_como_nao_paga_tira_ela_do_cac(tmp_path):
    """O caminho de correção que o aviso indica tem de funcionar."""
    from dataclasses import replace

    from app.core.config_analise import ConfigAnalise

    cfg = replace(ConfigAnalise(), marcacoes_nao_pagas=["Tayron"])
    com = analisar([META], [_planilha(tmp_path, COM_PARCEIRO)], cfg)
    sem = analisar([META], [_planilha(tmp_path, COM_PARCEIRO)])
    assert int(com.kpi("fecp")) == 1, "só o fechamento sem etiqueta conta como pago"
    assert com.kpi("cac") > sem.kpi("cac"), "o CAC real do anúncio é mais alto"
