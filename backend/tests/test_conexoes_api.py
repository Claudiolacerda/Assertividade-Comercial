"""As conexões de CRM pela API.

Dois riscos justificam estes testes acima dos outros:

1. **O token.** Ele entra por aqui, fica cifrado no banco e NUNCA pode voltar.
   Um `from_attributes` distraído no esquema de saída bastaria para ele
   aparecer numa listagem, e ninguém notaria olhando a tela.
2. **O isolamento.** A conexão mora no schema da empresa. Se uma organização
   conseguir ler ou usar a conexão da outra, o vazamento não é de número: é da
   credencial do CRM de um cliente para outro cliente.
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text

from app.config import settings
from app.core.conectores import http as modulo_http
from app.db import engine, sessao_publica
from tests.test_api import META, REUNIOES, cab, client, org


def _banco_disponivel() -> bool:
    try:
        with engine.connect() as con:
            con.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _banco_disponivel(), reason="Postgres não disponível"),
    pytest.mark.skipif(not META.exists(), reason="arquivos de exemplo não disponíveis"),
]

CONFIG = {
    "url": "https://api.exemplo.com/v1/leads",
    "auth": {"tipo": "bearer"},
    "itens": "itens",
    "paginacao": {"tipo": "nenhuma"},
    "campos": {"Cliente": "nome", "Status": "situacao", "Data do lead": "criado_em",
               "Data de fechamento": "fechado_em"},
}


@pytest.fixture
def crm_falso(monkeypatch):
    """Serve um CRM de mentira no ponto exato em que a rede entraria."""
    estado = {"pedidos": [], "negocios": []}

    def manipular(requisicao: httpx.Request) -> httpx.Response:
        estado["pedidos"].append(requisicao)
        return httpx.Response(200, json={"itens": estado["negocios"]})

    transporte = httpx.MockTransport(manipular)
    original = httpx.Client
    monkeypatch.setattr(modulo_http, "conferir_url", lambda url: url)
    monkeypatch.setattr(
        modulo_http.httpx, "Client",
        lambda *a, **k: original(*a, **{**k, "transport": transporte}),
    )
    return estado


def criar_conexao(client, dados, **extra):
    corpo = {"nome": f"CRM {uuid.uuid4().hex[:6]}", "provedor": "generico",
             "token": "token-super-secreto", "config": CONFIG, **extra}
    return client.post("/api/conexoes", headers=cab(dados), json=corpo)


# --------------------------------------------------------------------- #
# O token não volta
# --------------------------------------------------------------------- #
def test_o_token_nunca_aparece_na_resposta(client, org):
    dados = org()
    criada = criar_conexao(client, dados)
    assert criada.status_code == 201, criada.text
    assert "token-super-secreto" not in criada.text
    assert criada.json()["tem_token"] is True

    listagem = client.get("/api/conexoes", headers=cab(dados))
    assert "token-super-secreto" not in listagem.text
    assert "token_cifrado" not in listagem.text


def test_o_token_fica_cifrado_no_banco(client, org):
    """Quem copiar um dump não leva as contas de CRM dos clientes junto."""
    dados = org()
    criar_conexao(client, dados)
    with sessao_publica() as db:
        slug = dados["usuario"]["empresas"][0]["slug"]
        guardado = db.execute(
            text(f'select token_cifrado from "tenant_{slug}".conexoes_crm')
        ).scalar()
    assert guardado and "token-super-secreto" not in guardado

    from app.security import decifrar

    assert decifrar(guardado) == "token-super-secreto", "e volta legível para o servidor"


def test_editar_sem_mandar_token_mantem_o_que_estava(client, org):
    """Senão, corrigir o endereço exigiria ir buscar o segredo de novo."""
    dados = org()
    conexao = criar_conexao(client, dados).json()
    resp = client.put(
        f"/api/conexoes/{conexao['id']}",
        headers=cab(dados),
        json={"nome": "Outro nome", "token": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Outro nome"
    assert resp.json()["tem_token"] is True


# --------------------------------------------------------------------- #
# Isolamento entre organizações
# --------------------------------------------------------------------- #
def test_uma_organizacao_nao_ve_nem_usa_a_conexao_da_outra(client, org):
    a, b = org("Dona do CRM"), org("Curiosa")
    conexao = criar_conexao(client, a).json()

    assert client.get("/api/conexoes", headers=cab(b)).json() == []
    assert client.put(f"/api/conexoes/{conexao['id']}", headers=cab(b),
                      json={"nome": "roubada"}).status_code == 404
    assert client.post(f"/api/conexoes/{conexao['id']}/testar",
                       headers=cab(b)).status_code == 404
    assert client.delete(f"/api/conexoes/{conexao['id']}", headers=cab(b)).status_code == 404


# --------------------------------------------------------------------- #
# Testar e importar
# --------------------------------------------------------------------- #
def test_testar_diz_quantos_vieram_e_o_que_ficou_vazio(client, org, crm_falso):
    """A tela precisa mostrar o que o mapa NÃO preencheu, senão a pessoa só
    descobre a coluna faltando quando o indicador some da análise."""
    dados = org()
    hoje = date.today()
    crm_falso["negocios"] = [
        {"nome": "Aurora", "situacao": "Venda", "criado_em": hoje.isoformat(),
         "fechado_em": hoje.isoformat()},
    ]
    conexao = criar_conexao(client, dados).json()
    resp = client.post(f"/api/conexoes/{conexao['id']}/testar", headers=cab(dados))
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["quantidade"] == 1
    assert "Cliente" in corpo["colunas_preenchidas"]
    assert "Valor" in corpo["colunas_vazias"]


def test_credencial_recusada_vira_422_com_a_mensagem(client, org, monkeypatch):
    dados = org()
    conexao = criar_conexao(client, dados).json()

    transporte = httpx.MockTransport(lambda r: httpx.Response(401, json={"erro": "nope"}))
    original = httpx.Client
    monkeypatch.setattr(modulo_http, "conferir_url", lambda url: url)
    monkeypatch.setattr(modulo_http.httpx, "Client",
                        lambda *a, **k: original(*a, **{**k, "transport": transporte}))

    resp = client.post(f"/api/conexoes/{conexao['id']}/testar", headers=cab(dados))
    assert resp.status_code == 422
    assert "credencial" in resp.json()["detail"]

    # E o motivo fica gravado, para a tela poder dizer desde quando parou.
    listada = client.get("/api/conexoes", headers=cab(dados)).json()[0]
    assert listada["ultimo_erro"] and "credencial" in listada["ultimo_erro"]


def test_importar_grava_o_csv_que_a_pessoa_pode_abrir(client, org, crm_falso):
    """A prova do que o CRM respondeu naquele dia tem de ficar em arquivo."""
    dados = org()
    crm_falso["negocios"] = [
        {"nome": "Aurora", "situacao": "Venda", "criado_em": "2026-09-01",
         "fechado_em": "2026-09-04"},
        {"nome": "Benedito", "situacao": "Perdido", "criado_em": "2026-09-02", "fechado_em": None},
    ]
    conexao = criar_conexao(client, dados).json()
    resp = client.post(
        f"/api/conexoes/{conexao['id']}/importar?mes=2026-09", headers=cab(dados)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["quantidade"] == 2

    slug = dados["usuario"]["empresas"][0]["slug"]
    arquivo = Path(settings.dir_uploads) / slug / "2026-09" / resp.json()["arquivo"]
    assert arquivo.exists()
    texto = arquivo.read_text(encoding="utf-8-sig")
    assert "Aurora" in texto and "Cliente" in texto.splitlines()[0]


def test_mes_sem_negocio_nenhum_e_erro_e_nao_analise_vazia(client, org, crm_falso):
    dados = org()
    crm_falso["negocios"] = []
    conexao = criar_conexao(client, dados).json()
    resp = client.post(f"/api/conexoes/{conexao['id']}/importar?mes=2026-09", headers=cab(dados))
    assert resp.status_code == 422 and "nenhum negócio" in resp.json()["detail"]


# --------------------------------------------------------------------- #
# A análise puxando do CRM
# --------------------------------------------------------------------- #
def _analisar_do_crm(client, dados, conexao_id, mes="2026-09"):
    with META.open("rb") as fm:
        return client.post(
            "/api/analises",
            headers=cab(dados),
            files=[("arquivos_meta", ("meta.csv", fm.read(), "text/csv"))],
            data={"mes_referencia": mes, "conexao_id": str(conexao_id)},
        )


def test_analise_do_mes_puxando_do_crm(client, org, crm_falso):
    """O caminho inteiro: CRM -> CSV -> motor -> análise gravada."""
    dados = org()
    crm_falso["negocios"] = [
        {"nome": f"Cliente {i}", "situacao": "Venda" if i < 3 else "Em negociação",
         "criado_em": "2026-09-02", "fechado_em": "2026-09-10" if i < 3 else None}
        for i in range(8)
    ]
    conexao = criar_conexao(client, dados).json()
    resp = _analisar_do_crm(client, dados, conexao["id"])
    assert resp.status_code == 201, resp.text
    kpis = resp.json()["resultado"]["kpis"]
    assert kpis["fec"]["valor"] == 3
    assert kpis["ag"]["valor"] == 8


def test_a_analise_do_crm_guarda_o_arquivo_para_reprocessar(client, org, crm_falso):
    dados = org()
    crm_falso["negocios"] = [
        {"nome": "Aurora", "situacao": "Venda", "criado_em": "2026-09-02", "fechado_em": "2026-09-10"}
    ]
    conexao = criar_conexao(client, dados).json()
    analise = _analisar_do_crm(client, dados, conexao["id"]).json()

    # Reprocessar não fala com o CRM de novo: lê o arquivo que ficou gravado.
    crm_falso["negocios"] = []
    resp = client.post(f"/api/analises/{analise['id']}/reprocessar", headers=cab(dados), json={})
    assert resp.status_code == 201, resp.text
    assert resp.json()["resultado"]["kpis"]["fec"]["valor"] == 1


def test_planilha_e_crm_ao_mesmo_tempo_e_recusado(client, org):
    dados = org()
    conexao = criar_conexao(client, dados).json()
    with META.open("rb") as fm, REUNIOES.open("rb") as fr:
        resp = client.post(
            "/api/analises",
            headers=cab(dados),
            files=[("arquivos_meta", ("meta.csv", fm.read(), "text/csv")),
                   ("arquivos_reunioes", ("r.csv", fr.read(), "text/csv"))],
            data={"mes_referencia": "2026-09", "conexao_id": str(conexao["id"])},
        )
    assert resp.status_code == 400 and "um dos dois" in resp.json()["detail"]


def test_sem_planilha_e_sem_crm_tambem_e_recusado(client, org):
    dados = org()
    with META.open("rb") as fm:
        resp = client.post(
            "/api/analises",
            headers=cab(dados),
            files=[("arquivos_meta", ("meta.csv", fm.read(), "text/csv"))],
        )
    assert resp.status_code == 400


def test_crm_sem_mes_e_recusado_antes_de_chamar_a_api(client, org, crm_falso):
    """"Tudo" não é período: seria o histórico inteiro da conta a cada análise."""
    dados = org()
    conexao = criar_conexao(client, dados).json()
    with META.open("rb") as fm:
        resp = client.post(
            "/api/analises",
            headers=cab(dados),
            files=[("arquivos_meta", ("meta.csv", fm.read(), "text/csv"))],
            data={"conexao_id": str(conexao["id"])},
        )
    assert resp.status_code == 400 and "qual mês" in resp.json()["detail"]
    assert not crm_falso["pedidos"], "nem chegou a bater no CRM"


def test_conexao_desligada_nao_roda_analise(client, org, crm_falso):
    dados = org()
    conexao = criar_conexao(client, dados).json()
    client.put(f"/api/conexoes/{conexao['id']}", headers=cab(dados), json={"ativa": False})
    resp = _analisar_do_crm(client, dados, conexao["id"])
    assert resp.status_code == 422 and "desligada" in resp.json()["detail"]


# --------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------- #
def test_o_catalogo_lista_os_crms_e_as_colunas(client, org):
    dados = org()
    corpo = client.get("/api/conexoes/provedores", headers=cab(dados)).json()
    nomes = [p["nome"] for p in corpo["provedores"]]
    assert "pipedrive" in nomes and "generico" in nomes
    assert "Cliente" in corpo["colunas"]
    assert all(p["ajuda"] for p in corpo["provedores"]), "cada CRM diz o que a pessoa precisa ter"


def test_crm_desconhecido_e_recusado_no_cadastro(client, org):
    dados = org()
    resp = criar_conexao(client, dados, provedor="salesforce")
    assert resp.status_code == 400 and "pipedrive" in resp.json()["detail"]


def test_mapa_sem_data_de_entrada_avisa_que_o_aberto_vai_sumir(client, org, crm_falso):
    """O erro silencioso mais caro desta tela: só mapear a data de fechamento.

    Quem fechou tem data e entra no mês; quem está em aberto não tem data
    nenhuma e some. A assertividade sobe porque o denominador encolheu, e o
    número parece ótimo justamente quando está errado.
    """
    dados = org()
    sem_entrada = {**CONFIG, "campos": {"Cliente": "nome", "Data de fechamento": "fechado_em"}}
    crm_falso["negocios"] = [{"nome": "Aurora", "fechado_em": "2026-09-04"}]
    conexao = criar_conexao(client, dados, config=sem_entrada).json()
    corpo = client.post(f"/api/conexoes/{conexao['id']}/testar", headers=cab(dados)).json()
    assert any("Data do lead" in a for a in corpo["avisos"])
