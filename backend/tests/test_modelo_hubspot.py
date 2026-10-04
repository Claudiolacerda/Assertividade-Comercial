"""O gabarito de exportação do HubSpot.

Um modelo que o próprio motor não lê é pior que nenhum modelo: a pessoa segue a
instrução, sobe o arquivo e leva um erro. O teste central aqui fecha esse
circuito — gera a planilha, preenche como um usuário preencheria e manda para
`analisar()`. Se alguém renomear um cabeçalho no modelo sem mexer na tabela de
apelidos (ou o contrário), o teste cai antes de chegar no cliente.
"""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl
import pytest

from app.core import analisar
from app.core.config_analise import COLUNAS_REUNIOES
from app.core.modelo_hubspot import ABA, ETAPAS_HUBSPOT, EXEMPLOS, PROPRIEDADES, gerar_planilha_hubspot
from app.core.texto import normalizar

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"

pytestmark = pytest.mark.skipif(not META.exists(), reason="exemplo da Meta indisponível")


@pytest.fixture(scope="module")
def planilha(tmp_path_factory):
    arq = tmp_path_factory.mktemp("hs") / "Modelo_HubSpot.xlsx"
    gerar_planilha_hubspot(arq)
    return arq


def test_a_planilha_tem_as_tres_abas(planilha):
    wb = openpyxl.load_workbook(planilha)
    assert wb.sheetnames == [ABA, "Metas", "Como exportar"]


def test_o_cabecalho_e_a_propriedade_do_hubspot(planilha):
    """Os nomes são os que a pessoa vê no CRM dela, não os internos do Neriah."""
    ws = openpyxl.load_workbook(planilha)[ABA]
    cabecalho = [c.value for c in ws[4]]
    assert cabecalho[:3] == ["Deal Name", "Deal Stage", "Close Date"]
    assert cabecalho == [p for p, *_ in PROPRIEDADES]


def test_todo_cabecalho_do_modelo_e_reconhecido_pelo_motor():
    """O elo que arrebenta em silêncio: modelo e tabela de apelidos divergirem.

    A correspondência do motor é por prefixo normalizado, então é assim que o
    teste confere — do contrário ele passaria achando que precisa de igualdade
    exata, e reprovaria apelidos que funcionam.
    """
    apelidos = [normalizar(a) for lista in COLUNAS_REUNIOES.values() for a in lista]
    for propriedade, obrigatoria, *_ in PROPRIEDADES:
        alvo = normalizar(propriedade)
        casou = any(alvo == a or alvo.startswith(a) for a in apelidos)
        assert casou, f"o modelo oferece '{propriedade}' e o motor não reconhece"


def test_as_etapas_do_modelo_sao_todas_classificaveis():
    """Nenhuma etapa da lista suspensa pode cair em 'Não classificado'.

    Um negócio ali não entra em taxa nenhuma: some da conta sem avisar.
    """
    from app.core.config_analise import ConfigAnalise
    from app.core.pipeline import _classificar_status

    cfg = ConfigAnalise()
    for etapa in ETAPAS_HUBSPOT:
        assert _classificar_status(etapa, cfg) != "Não classificado", etapa


def test_closed_won_e_closed_lost_caem_nos_lados_certos():
    """As duas únicas etapas que decidem dinheiro.

    "closed won" contém "won", e "closed lost" contém "lost": se a ordem das
    regras invertesse, todo negócio perdido viraria ganho.
    """
    from app.core.config_analise import ConfigAnalise
    from app.core.pipeline import _classificar_status

    cfg = ConfigAnalise()
    assert _classificar_status("Closed Won", cfg) == "Fechado"
    assert _classificar_status("Closed Lost", cfg) == "Perdido"


def test_a_planilha_preenchida_volta_funcionando_pelo_motor(planilha, tmp_path):
    """O circuito fechado: gerar o modelo, preencher, analisar.

    É o teste que impede entregar ao cliente um modelo que o próprio sistema
    não lê.
    """
    ws = openpyxl.load_workbook(planilha)[ABA]
    cabecalho = [c.value for c in ws[4]]

    # Preenche como um usuário preencheria: três negócios decididos e um aberto.
    linhas = [
        ["Padaria do Zé", "Closed Won", "2026-09-05", "2500.00", "Marina", "Paid Social",
         "2026-09-01", "Fechou na call", ""],
        ["Mercado Sul", "Closed Lost", "2026-09-06", "1800.00", "Marina", "Paid Social",
         "2026-09-02", "Achou caro", "Preço"],
        ["Bar do João", "Closed Won", "2026-09-09", "3200.00", "Rafael", "Paid Social",
         "2026-09-04", "Assinou no mesmo dia", ""],
        ["Café Central", "Presentation Scheduled", "2026-09-12", "1500.00", "Rafael",
         "Organic Search", "2026-09-08", "Reunião marcada para o dia 12", ""],
    ]
    arq = tmp_path / "exportado.csv"
    with arq.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        w.writerows(linhas)

    res = analisar([META], [arq])
    assert int(res.kpi("fec")) == 2, "dois Closed Won"
    assert int(res.kpi("per")) == 1, "um Closed Lost"
    assert int(res.kpi("fut")) == 1, "o Presentation Scheduled ainda vai acontecer"
    assert res.kpi("rec") == 5700.0, "2500 + 3200"
    # só os de Paid Social contam para o CAC; o Organic Search não fechou mesmo
    assert int(res.kpi("fecp")) == 2


def test_os_exemplos_da_planilha_tambem_passam_pelo_motor(tmp_path):
    """As três linhas de exemplo são o que a pessoa olha para conferir.

    Se elas não forem analisáveis, o exemplo ensina errado.
    """
    arq = tmp_path / "exemplos.csv"
    with arq.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([p for p, *_ in PROPRIEDADES])
        w.writerows(EXEMPLOS)
    res = analisar([META], [arq])
    assert len(res.tabelas["base_reunioes"]) == len(EXEMPLOS)
    assert int(res.kpi("fec")) == 1 and int(res.kpi("per")) == 1


def test_a_rota_entrega_o_arquivo():
    from fastapi.testclient import TestClient

    from app.main import app

    resp = TestClient(app).get("/api/modelo/planilha-hubspot.xlsx")
    assert resp.status_code == 200
    assert "Modelo_HubSpot_Neriah.xlsx" in resp.headers["content-disposition"]
    assert resp.content[:2] == b"PK", "um .xlsx é um zip"


def test_o_modelo_padrao_continua_em_portugues():
    """O gabarito do HubSpot é um ADICIONAL, não uma troca.

    Quem não tem CRM continua recebendo a planilha em português para preencher.
    """
    from app.core.modelo import gerar_planilha_modelo

    import io

    wb = openpyxl.load_workbook(io.BytesIO(gerar_planilha_modelo()))
    assert "Reuniões" in wb.sheetnames
    assert [c.value for c in wb["Reuniões"][4]][0] == "Cliente"
