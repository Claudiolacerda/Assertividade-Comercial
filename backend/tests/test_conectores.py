"""Os conectores de CRM.

O que estes testes protegem não é a chamada HTTP — é a promessa que sustenta o
desenho: o arquivo que um conector escreve atravessa o motor como qualquer
planilha, sem caminho especial. Se um dia alguém precisar mexer no pipeline
para dado de API funcionar, a promessa quebrou e o teste de ponta a ponta
aqui embaixo acusa.

Nenhum teste toca a rede. As respostas do CRM são servidas por um transporte
falso do httpx, que é o ponto exato onde a rede entra.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import httpx
import pandas as pd
import pytest

from app.core.conectores import (
    COLUNAS_SAIDA,
    ConectorGenerico,
    ConectorPipedrive,
    Credencial,
    ErroDeConexao,
    Periodo,
    escrever_csv,
    montar,
)
from app.core.conectores import http as modulo_http


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Nenhum teste resolve nome nem espera: a conferência de IP e o backoff
    são exercitados nos testes próprios deles, não em todos os outros."""
    monkeypatch.setattr(modulo_http, "conferir_url", lambda url: url)
    monkeypatch.setattr(modulo_http.time, "sleep", lambda s: None)


def servir(rotas):
    """Troca o transporte do httpx por um que responde do dicionário `rotas`.

    A chave é o caminho da URL; o valor é uma função que recebe a requisição e
    devolve (status, corpo) — assim cada teste descreve só o que lhe importa.
    """
    def manipular(requisicao: httpx.Request) -> httpx.Response:
        resposta = rotas.get(requisicao.url.path)
        if resposta is None:
            return httpx.Response(404, json={"erro": "rota não servida no teste"})
        status, corpo = resposta(requisicao)
        return httpx.Response(status, json=corpo)

    return httpx.MockTransport(manipular)


@pytest.fixture
def cliente_falso(monkeypatch):
    def instalar(rotas):
        transporte = servir(rotas)
        original = httpx.Client

        def fabricar(*args, **kwargs):
            kwargs["transport"] = transporte
            return original(*args, **kwargs)

        monkeypatch.setattr(modulo_http.httpx, "Client", fabricar)

    return instalar


# --------------------------------------------------------------------- #
# A promessa: o CSV do conector é uma planilha como outra qualquer
# --------------------------------------------------------------------- #
def test_o_csv_do_conector_atravessa_o_motor_inteiro(tmp_path, cliente_falso):
    """O teste que justifica o desenho: nada no motor sabe que isto veio de API."""
    from app.core import ConfigAnalise, analisar

    negocios = [
        {
            "id": 100 + i,
            "title": f"Cliente {i}",
            "status": "won" if i < 4 else "open",
            "value": 1500 + i,
            "stage_id": 1,
            "user_id": {"name": "Juliana"},
            "add_time": "2026-09-02 09:00:00",
            "won_time": "2026-09-05 15:00:00" if i < 4 else None,
            "update_time": "2026-09-20 10:00:00",
        }
        for i in range(10)
    ]
    cliente_falso({
        "/api/v1/stages": lambda r: (200, {"data": [{"id": 1, "name": "Proposta"}]}),
        "/api/v1/deals": lambda r: (
            200,
            {"data": negocios if r.url.params.get("start") == "0" else [],
             "additional_data": {"pagination": {"more_items_in_collection": False}}},
        ),
    })

    conector = ConectorPipedrive(Credencial(token="tok"), {"dominio": "acme.pipedrive.com"})
    importacao = conector.buscar(Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30)))
    csv_reunioes = escrever_csv(importacao, tmp_path / "pipedrive.csv")

    meta = Path(__file__).resolve().parents[2] / "dados" / "meta"
    arquivo_meta = next(meta.glob("*.csv"), None)
    if arquivo_meta is None:
        pytest.skip("arquivo de exemplo da Meta não disponível")

    cfg = ConfigAnalise()
    cfg.mes_referencia = "2026-09"
    resultado = analisar([arquivo_meta], [csv_reunioes], cfg)

    assert resultado.kpis["fec"]["valor"] == 4, "os 4 negócios 'won' viraram 4 fechamentos"
    assert resultado.kpis["ag"]["valor"] == 10


def test_o_csv_sai_com_todas_as_colunas_mesmo_faltando_dado(tmp_path):
    from app.core.conectores import Importacao

    importacao = Importacao(linhas=[{"Cliente": "Só o nome"}])
    caminho = escrever_csv(importacao, tmp_path / "x.csv")
    lido = pd.read_csv(caminho)
    assert list(lido.columns) == COLUNAS_SAIDA
    assert lido.loc[0, "Cliente"] == "Só o nome"


def test_os_cabecalhos_do_csv_sao_apelidos_que_o_motor_conhece():
    """Se um nome daqui sair do mapa de apelidos, a coluna some da análise calada."""
    from app.core.config_analise import COLUNAS_REUNIOES
    from app.core.texto import normalizar

    conhecidos = {normalizar(a) for apelidos in COLUNAS_REUNIOES.values() for a in apelidos}
    # "ID no CRM" é o único que não vira campo do sistema, e é de propósito.
    for coluna in COLUNAS_SAIDA:
        if coluna == "ID no CRM":
            continue
        assert normalizar(coluna) in conhecidos, f"{coluna!r} não está no mapa de apelidos"


# --------------------------------------------------------------------- #
# Pipedrive
# --------------------------------------------------------------------- #
def test_pipedrive_pagina_ate_acabar(cliente_falso):
    paginas = {
        "0": {"data": [{"id": i, "title": f"A{i}", "update_time": "2026-09-20 10:00:00"}
                       for i in range(100)],
              "additional_data": {"pagination": {"more_items_in_collection": True}}},
        "100": {"data": [{"id": 200, "title": "B", "update_time": "2026-09-20 10:00:00"}],
                "additional_data": {"pagination": {"more_items_in_collection": False}}},
    }
    cliente_falso({
        "/api/v1/stages": lambda r: (200, {"data": []}),
        "/api/v1/deals": lambda r: (200, paginas[r.url.params.get("start")]),
    })
    conector = ConectorPipedrive(Credencial(token="t"), {"dominio": "a.pipedrive.com"})
    resultado = conector.buscar(Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30)))
    assert resultado.quantidade == 101 and resultado.paginas == 2


def test_pipedrive_para_quando_a_pagina_inteira_e_anterior_ao_periodo(cliente_falso):
    """Sem isto, cada importação varreria o histórico inteiro da conta."""
    chamadas = []

    def deals(r):
        chamadas.append(r.url.params.get("start"))
        return 200, {
            "data": [{"id": 1, "title": "Velho", "update_time": "2024-01-01 10:00:00"}],
            "additional_data": {"pagination": {"more_items_in_collection": True}},
        }

    cliente_falso({"/api/v1/stages": lambda r: (200, {"data": []}), "/api/v1/deals": deals})
    conector = ConectorPipedrive(Credencial(token="t"), {"dominio": "a.pipedrive.com"})
    conector.buscar(Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30)))
    assert len(chamadas) == 1, "parou na primeira página, toda anterior ao período"


def test_pipedrive_traduz_a_etapa_pelo_nome(cliente_falso):
    cliente_falso({
        "/api/v1/stages": lambda r: (200, {"data": [{"id": 7, "name": "Negociação"}]}),
        "/api/v1/deals": lambda r: (
            200,
            {"data": [{"id": 1, "title": "X", "stage_id": 7, "update_time": "2026-09-10 00:00:00"}]
             if r.url.params.get("start") == "0" else []},
        ),
    })
    conector = ConectorPipedrive(Credencial(token="t"), {"dominio": "a.pipedrive.com"})
    linha = conector.buscar(Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))).linhas[0]
    assert linha["Etapa"] == "Negociação"


def test_pipedrive_segue_sem_as_etapas_se_elas_falharem(cliente_falso):
    """Nome de etapa é detalhe; o desfecho vem do campo status."""
    cliente_falso({
        "/api/v1/deals": lambda r: (
            200,
            {"data": [{"id": 1, "title": "X", "status": "won", "stage_id": 7,
                       "update_time": "2026-09-10 00:00:00"}]
             if r.url.params.get("start") == "0" else []},
        ),
    })  # /stages não servido: devolve 404
    conector = ConectorPipedrive(Credencial(token="t"), {"dominio": "a.pipedrive.com"})
    linha = conector.buscar(Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))).linhas[0]
    assert linha["Etapa"] is None and linha["Status"] == "won"


def test_pipedrive_recusa_dominio_de_fora():
    """Domínio livre aqui contornaria a conferência de rede pela porta lateral."""
    conector = ConectorPipedrive(Credencial(token="t"), {"dominio": "api.interno.local"})
    with pytest.raises(ErroDeConexao, match="pipedrive.com"):
        _ = conector.base


def test_pipedrive_nao_inventa_data_de_reuniao(cliente_falso):
    """Negócio de CRM não tem data de reunião; fingir que tem embaralharia o mês."""
    cliente_falso({
        "/api/v1/stages": lambda r: (200, {"data": []}),
        "/api/v1/deals": lambda r: (
            200,
            {"data": [{"id": 1, "title": "X", "add_time": "2026-09-02 09:00:00",
                       "won_time": "2026-09-05 15:00:00", "update_time": "2026-09-10 00:00:00"}]
             if r.url.params.get("start") == "0" else []},
        ),
    })
    conector = ConectorPipedrive(Credencial(token="t"), {"dominio": "a.pipedrive.com"})
    linha = conector.buscar(Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))).linhas[0]
    assert linha["Data da reunião"] is None
    assert linha["Data do lead"] == "2026-09-02", "a hora não entra em conta nenhuma"
    assert linha["Data de fechamento"] == "2026-09-05"


# --------------------------------------------------------------------- #
# Conector genérico — o que vai servir ao Datalitics
# --------------------------------------------------------------------- #
CONFIG_GENERICA = {
    "url": "https://api.exemplo.com/v1/leads",
    "auth": {"tipo": "bearer"},
    "itens": "data.itens",
    "paginacao": {"tipo": "deslocamento", "param": "offset", "param_tamanho": "limite",
                  "tamanho": 2, "caminho_tem_mais": "data.tem_mais"},
    "periodo": {"param_de": "desde", "param_ate": "ate", "formato": "%Y-%m-%d"},
    "campos": {"Cliente": "nome", "Status": "situacao", "Valor": "valor",
               "Responsável": "vendedor.nome", "Data de fechamento": "fechado_em"},
}


def test_generico_le_a_lista_dentro_do_envelope(cliente_falso):
    cliente_falso({
        "/v1/leads": lambda r: (
            200,
            {"data": {"itens": [{"nome": "Aurora", "situacao": "Venda", "valor": 1364.82,
                                 "vendedor": {"nome": "Rafael"}, "fechado_em": "2026-09-01"}],
                      "tem_mais": False}},
        ),
    })
    conector = ConectorGenerico(Credencial(token="t"), CONFIG_GENERICA)
    linha = conector.buscar(Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))).linhas[0]
    assert linha["Cliente"] == "Aurora"
    assert linha["Responsável"] == "Rafael", "campo aninhado pelo caminho com ponto"
    assert linha["Valor"] == 1364.82


def test_generico_manda_o_periodo_e_o_token_como_pedido(cliente_falso):
    visto = {}

    def rota(r):
        visto["params"] = dict(r.url.params)
        visto["auth"] = r.headers.get("authorization")
        return 200, {"data": {"itens": [], "tem_mais": False}}

    cliente_falso({"/v1/leads": rota})
    ConectorGenerico(Credencial(token="segredo"), CONFIG_GENERICA).buscar(
        Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
    )
    assert visto["params"]["desde"] == "2026-09-01"
    assert visto["params"]["ate"] == "2026-09-30"
    assert visto["auth"] == "Bearer segredo"


def test_generico_autentica_por_parametro_quando_o_crm_exige(cliente_falso):
    visto = {}

    def rota(r):
        visto.update(dict(r.url.params))
        return 200, {"itens": []}

    cliente_falso({"/v1/leads": rota})
    config = {**CONFIG_GENERICA, "itens": "itens", "paginacao": {"tipo": "nenhuma"},
              "auth": {"tipo": "parametro", "nome": "api_key"}}
    ConectorGenerico(Credencial(token="abc"), config).buscar(
        Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
    )
    assert visto["api_key"] == "abc"


def test_generico_segue_o_cursor(cliente_falso):
    paginas = {
        None: {"itens": [{"nome": "A"}], "proximo": "c2"},
        "c2": {"itens": [{"nome": "B"}], "proximo": None},
    }
    cliente_falso({"/v1/leads": lambda r: (200, paginas[r.url.params.get("cursor")])})
    config = {**CONFIG_GENERICA, "itens": "itens",
              "paginacao": {"tipo": "cursor", "param": "cursor", "caminho_proximo": "proximo"}}
    resultado = ConectorGenerico(Credencial(token="t"), config).buscar(
        Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
    )
    assert [l["Cliente"] for l in resultado.linhas] == ["A", "B"]


def test_generico_exige_saber_qual_campo_e_o_cliente():
    config = {**CONFIG_GENERICA, "campos": {"Valor": "valor"}}
    with pytest.raises(ErroDeConexao, match="nome do cliente"):
        ConectorGenerico(Credencial(token="t"), config).buscar(
            Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
        )


def test_generico_recusa_coluna_que_nao_existe_no_neriah():
    """Erro de digitação no mapa viraria coluna fantasma, e ninguém perceberia."""
    config = {**CONFIG_GENERICA, "campos": {"Cliente": "nome", "Faturamento": "x"}}
    with pytest.raises(ErroDeConexao, match="Faturamento"):
        ConectorGenerico(Credencial(token="t"), config).buscar(
            Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
        )


def test_generico_explica_quando_o_caminho_nao_da_em_lista(cliente_falso):
    cliente_falso({"/v1/leads": lambda r: (200, {"data": {"itens": {"nome": "um só"}}})})
    with pytest.raises(ErroDeConexao, match="não aponta para uma lista"):
        ConectorGenerico(Credencial(token="t"), CONFIG_GENERICA).buscar(
            Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
        )


def test_generico_resolve_objeto_no_lugar_de_valor(cliente_falso):
    """O engano mais comum ao preencher o mapa: apontar para o objeto, não o campo."""
    cliente_falso({
        "/v1/leads": lambda r: (
            200, {"data": {"itens": [{"nome": {"name": "Aurora Ltda"}}], "tem_mais": False}},
        ),
    })
    config = {**CONFIG_GENERICA, "campos": {"Cliente": "nome"}}
    linha = ConectorGenerico(Credencial(token="t"), config).buscar(
        Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
    ).linhas[0]
    assert linha["Cliente"] == "Aurora Ltda"


# --------------------------------------------------------------------- #
# Erros que o usuário resolve
# --------------------------------------------------------------------- #
@pytest.mark.parametrize("status,trecho", [(401, "recusou a credencial"), (403, "recusou a credencial"), (404, "404")])
def test_erro_de_credencial_vira_mensagem_e_nao_traceback(cliente_falso, status, trecho):
    cliente_falso({"/v1/leads": lambda r: (status, {"erro": "x"})})
    with pytest.raises(ErroDeConexao, match=trecho):
        ConectorGenerico(Credencial(token="t"), CONFIG_GENERICA).buscar(
            Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
        )


def test_o_429_e_repetido_e_nao_derruba_a_importacao(cliente_falso):
    tentativas = {"n": 0}

    def rota(r):
        tentativas["n"] += 1
        if tentativas["n"] == 1:
            return 429, {"erro": "devagar"}
        return 200, {"data": {"itens": [{"nome": "A"}], "tem_mais": False}}

    cliente_falso({"/v1/leads": rota})
    resultado = ConectorGenerico(Credencial(token="t"), CONFIG_GENERICA).buscar(
        Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
    )
    assert resultado.quantidade == 1 and tentativas["n"] == 2


def test_periodo_invertido_e_recusado_na_origem():
    with pytest.raises(ValueError):
        Periodo(de=date(2026, 9, 30), ate=date(2026, 9, 1))


def test_crm_desconhecido_diz_quais_existem():
    with pytest.raises(ErroDeConexao, match="pipedrive"):
        montar("salesforce", Credencial(token="t"))


# --------------------------------------------------------------------- #
# Endereço: a conferência que impede o servidor de buscar a rede interna
# --------------------------------------------------------------------- #
@pytest.mark.parametrize("url", [
    "http://api.exemplo.com/v1",      # sem TLS
    "https://localhost/v1",
    "https://127.0.0.1/v1",
    "https://[::1]/v1",
])
def test_endereco_perigoso_e_recusado(url, monkeypatch):
    monkeypatch.undo()  # este teste precisa da conferência de verdade
    from app.core.conectores.http import conferir_url

    with pytest.raises(ErroDeConexao):
        conferir_url(url)


# --------------------------------------------------------------------- #
# A tela
# --------------------------------------------------------------------- #
def _fonte(caminho: str) -> str:
    return (Path(__file__).resolve().parents[2] / "frontend" / "src" / caminho).read_text(
        encoding="utf-8"
    )


def test_a_tela_de_conexoes_existe_e_esta_no_menu():
    app = _fonte("App.tsx")
    assert "/conexoes" in app and "Conexoes" in app


def test_a_tela_nunca_pede_para_exibir_o_token():
    """O campo é de senha e o tipo da conexão não tem token: as duas pontas fechadas."""
    pagina = _fonte("pages/Conexoes.tsx")
    assert 'type="password"' in pagina
    bloco = _fonte("tipos.ts").split("export interface Conexao {")[1].split("}")[0]
    # Campo declarado, não a palavra: o comentário ali explica justamente que
    # o token não vem, e casar com a palavra solta reprovava o comentário.
    declarados = re.findall(r"^\s*(\w+)\??:", bloco, re.M)
    assert "token" not in declarados, "o token não pode chegar ao navegador"
    assert "tem_token" in declarados


def test_a_nova_analise_oferece_o_crm_sem_tirar_a_planilha():
    pagina = _fonte("pages/Upload.tsx")
    assert "conexaoId" in pagina
    assert "Enviar planilha" in pagina, "a planilha continua sendo a opção padrão"


def test_o_front_so_mostra_a_escolha_quando_ha_conexao_ligada():
    """Quem não usa CRM não precisa saber que isso existe para enviar planilha."""
    pagina = _fonte("pages/Upload.tsx")
    assert "conexoes.length > 0" in pagina
    assert "c.ativa" in pagina
