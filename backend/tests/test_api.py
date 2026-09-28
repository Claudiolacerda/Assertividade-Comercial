"""Testes da API, com foco no isolamento entre empresas.

Precisam de um Postgres acessível (o isolamento por schema é recurso do Postgres).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.config import settings
from app.db import criar_schemas_base, engine, remover_schema_empresa, sessao_publica
from app.main import app
from app.models import Empresa, Usuario

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "_CA_-Conta-ilidade-Horizonte-Campanhas-1-de-set-de-2026-24-de-set-de-2026.csv"
REUNIOES = DADOS / "reunioes" / "Controle_Comercial_Horizonte_-_Setembro.csv"


def _banco_disponivel() -> bool:
    try:
        with engine.connect() as con:
            con.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _banco_disponivel(), reason="Postgres não disponível"),
    pytest.mark.skipif(not (META.exists() and REUNIOES.exists()), reason="arquivos de exemplo não disponíveis"),
]


@pytest.fixture(scope="module")
def client():
    criar_schemas_base()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def empresa(client):
    """Cria uma empresa nova e devolve (token, dados). Remove schema e registros no fim."""
    criadas: list[str] = []

    def criar(nome: str | None = None):
        sufixo = uuid.uuid4().hex[:8]
        nome = nome or f"Empresa {sufixo}"
        resp = client.post(
            "/api/auth/cadastro",
            json={
                "empresa": nome,
                "nome": "Dono da Conta",
                "email": f"dono_{sufixo}@exemplo.com.br",
                "senha": "senhaSegura123",
            },
        )
        assert resp.status_code == 201, resp.text
        dados = resp.json()
        criadas.append(dados["usuario"]["empresa"]["slug"])
        return dados

    yield criar

    for slug in criadas:
        remover_schema_empresa(f"tenant_{slug}")
        with sessao_publica() as db:
            emp = db.scalar(select(Empresa).where(Empresa.slug == slug))
            if emp:
                db.delete(emp)
        pasta = Path(settings.dir_uploads) / slug
        if pasta.exists():
            import shutil

            shutil.rmtree(pasta, ignore_errors=True)


def _cabecalho(dados) -> dict[str, str]:
    return {"Authorization": f"Bearer {dados['access_token']}"}


def _subir_analise(client, dados, mes: str | None = None):
    with META.open("rb") as fm, REUNIOES.open("rb") as fr:
        return client.post(
            "/api/analises",
            headers=_cabecalho(dados),
            files=[
                ("arquivos_meta", (META.name, fm, "text/csv")),
                ("arquivos_reunioes", (REUNIOES.name, fr, "text/csv")),
            ],
            data={"mes_referencia": mes} if mes else {},
        )


# --------------------------------------------------------------------- #
# Autenticação
# --------------------------------------------------------------------- #
def test_saude(client):
    assert client.get("/api/saude").json()["status"] == "ok"


def test_cadastro_cria_schema_proprio(client, empresa):
    dados = empresa("Contabilidade Horizonte")
    slug = dados["usuario"]["empresa"]["slug"]
    assert slug.startswith("contabilidade_conforme")
    with engine.connect() as con:
        existe = con.execute(
            text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"), {"s": f"tenant_{slug}"}
        ).first()
    assert existe, "o schema da empresa deveria existir"


def test_duas_empresas_com_mesmo_nome_ganham_schemas_diferentes(client, empresa):
    a = empresa("Mesma Razao Social")
    b = empresa("Mesma Razao Social")
    assert a["usuario"]["empresa"]["slug"] != b["usuario"]["empresa"]["slug"]


def test_email_duplicado_e_recusado(client, empresa):
    dados = empresa()
    resp = client.post(
        "/api/auth/cadastro",
        json={
            "empresa": "Outra",
            "nome": "Outro",
            "email": dados["usuario"]["email"],
            "senha": "senhaSegura123",
        },
    )
    assert resp.status_code == 409


def test_login_com_senha_errada(client, empresa):
    dados = empresa()
    resp = client.post("/api/auth/login", json={"email": dados["usuario"]["email"], "senha": "errada123"})
    assert resp.status_code == 401
    assert "incorretos" in resp.json()["detail"]


def test_senha_fraca_e_recusada(client):
    resp = client.post(
        "/api/auth/cadastro",
        json={"empresa": "X", "nome": "Y", "email": "z@exemplo.com", "senha": "12345678"},
    )
    assert resp.status_code == 422


def test_rota_protegida_sem_token(client):
    assert client.get("/api/analises").status_code == 401


def test_token_invalido(client):
    resp = client.get("/api/analises", headers={"Authorization": "Bearer nao-e-um-token"})
    assert resp.status_code == 401


# --------------------------------------------------------------------- #
# Análise
# --------------------------------------------------------------------- #
def test_upload_roda_analise_e_devolve_kpis(client, empresa):
    dados = empresa()
    resp = _subir_analise(client, dados)
    assert resp.status_code == 201, resp.text
    corpo = resp.json()
    assert corpo["mes_referencia"] == "2026-09"
    assert corpo["status"] == "concluida"
    kpis = corpo["resultado"]["kpis"]
    assert kpis["fec"]["valor"] == 9
    assert kpis["assert"]["texto"] == "25,7%"
    assert len(corpo["resultado"]["diagnostico"]) >= 15
    assert corpo["kpis_resumo"]["cac"] == pytest.approx(405.67, abs=0.01)


def test_arquivo_de_formato_invalido(client, empresa):
    dados = empresa()
    resp = client.post(
        "/api/analises",
        headers=_cabecalho(dados),
        files=[
            ("arquivos_meta", ("relatorio.pdf", b"%PDF-1.4", "application/pdf")),
            ("arquivos_reunioes", ("planilha.csv", b"Cliente,Status\nA,Fechado\n", "text/csv")),
        ],
    )
    assert resp.status_code == 400
    assert "não aceito" in resp.json()["detail"]


def test_planilha_sem_as_colunas_certas_da_erro_explicativo(client, empresa):
    dados = empresa()
    resp = client.post(
        "/api/analises",
        headers=_cabecalho(dados),
        files=[
            ("arquivos_meta", ("meta.csv", b"coisa,outra\n1,2\n", "text/csv")),
            ("arquivos_reunioes", ("reunioes.csv", b"Cliente,Etapa do Funil\nA,Fechado\n", "text/csv")),
        ],
    )
    assert resp.status_code == 422
    assert "Meta" in resp.json()["detail"]


def test_mes_invalido(client, empresa):
    dados = empresa()
    resp = _subir_analise(client, dados, mes="setembro")
    assert resp.status_code == 400


def test_segunda_analise_do_mesmo_mes_vira_nova_versao(client, empresa):
    dados = empresa()
    assert _subir_analise(client, dados).json()["versao"] == 1
    assert _subir_analise(client, dados).json()["versao"] == 2
    historico = client.get("/api/analises", headers=_cabecalho(dados)).json()
    assert len(historico) == 2


def test_evolucao_usa_a_ultima_versao_de_cada_mes(client, empresa):
    dados = empresa()
    _subir_analise(client, dados)
    _subir_analise(client, dados)
    evo = client.get("/api/analises/evolucao", headers=_cabecalho(dados)).json()
    assert len(evo["meses"]) == 1  # dois uploads, um mês
    assert evo["meses"][0]["mes_referencia"] == "2026-09"
    assert "assert" in evo["meses"][0]


def test_download_do_excel(client, empresa):
    dados = empresa()
    analise = _subir_analise(client, dados).json()
    resp = client.get(f"/api/analises/{analise['id']}/excel", headers=_cabecalho(dados))
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"
    assert "attachment" in resp.headers["content-disposition"]


def test_excel_regenerado_quando_o_arquivo_sai_do_disco(client, empresa):
    dados = empresa()
    analise = _subir_analise(client, dados).json()
    baixado = client.get(f"/api/analises/{analise['id']}/excel", headers=_cabecalho(dados))
    assert baixado.status_code == 200
    # apaga o xlsx em cache; as planilhas de origem continuam lá
    slug = dados["usuario"]["empresa"]["slug"]
    for x in (Path(settings.dir_uploads) / slug).rglob("*.xlsx"):
        if x.name.startswith("Assertividade_"):
            x.unlink()
    resp = client.get(f"/api/analises/{analise['id']}/excel", headers=_cabecalho(dados))
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"


# --------------------------------------------------------------------- #
# Isolamento entre empresas — o teste que sustenta a venda
# --------------------------------------------------------------------- #
def test_empresa_nao_ve_analise_de_outra(client, empresa):
    a, b = empresa("Cliente A"), empresa("Cliente B")
    analise_a = _subir_analise(client, a).json()

    assert client.get("/api/analises", headers=_cabecalho(b)).json() == []
    resp = client.get(f"/api/analises/{analise_a['id']}", headers=_cabecalho(b))
    assert resp.status_code == 404, "o id de outra empresa não pode ser lido nem por número igual"
    assert client.get(f"/api/analises/{analise_a['id']}/excel", headers=_cabecalho(b)).status_code == 404


def test_ids_reiniciam_por_empresa_e_nao_colidem(client, empresa):
    """Cada schema tem sua sequência: as duas empresas têm análise id=1, cada uma com seus dados."""
    a, b = empresa("Cliente C"), empresa("Cliente D")
    ida = _subir_analise(client, a).json()["id"]
    idb = _subir_analise(client, b).json()["id"]
    assert ida == idb == 1
    da = client.get(f"/api/analises/{ida}", headers=_cabecalho(a)).json()
    dbb = client.get(f"/api/analises/{idb}", headers=_cabecalho(b)).json()
    assert da["resultado"]["kpis"]["fec"]["valor"] == dbb["resultado"]["kpis"]["fec"]["valor"]
    assert da["id"] == dbb["id"]  # mesmo id, schemas diferentes


def test_exclusao_so_pelo_admin_e_so_da_propria_empresa(client, empresa):
    a, b = empresa("Cliente E"), empresa("Cliente F")
    analise = _subir_analise(client, a).json()
    assert client.delete(f"/api/analises/{analise['id']}", headers=_cabecalho(b)).status_code == 404
    assert client.delete(f"/api/analises/{analise['id']}", headers=_cabecalho(a)).status_code == 204
    assert client.get("/api/analises", headers=_cabecalho(a)).json() == []


def test_membro_nao_apaga_analise(client, empresa):
    dados = empresa()
    analise = _subir_analise(client, dados).json()
    sufixo = uuid.uuid4().hex[:8]
    novo = client.post(
        "/api/auth/usuarios",
        headers=_cabecalho(dados),
        json={"nome": "Analista", "email": f"membro_{sufixo}@exemplo.com", "senha": "senhaSegura123",
              "papel": "membro"},
    )
    assert novo.status_code == 201
    login = client.post(
        "/api/auth/login", json={"email": f"membro_{sufixo}@exemplo.com", "senha": "senhaSegura123"}
    ).json()
    assert client.get("/api/analises", headers=_cabecalho(login)).status_code == 200  # lê
    assert client.delete(f"/api/analises/{analise['id']}", headers=_cabecalho(login)).status_code == 403  # não apaga


def test_usuario_novo_entra_na_empresa_de_quem_criou(client, empresa):
    a, b = empresa("Cliente G"), empresa("Cliente H")
    sufixo = uuid.uuid4().hex[:8]
    client.post(
        "/api/auth/usuarios",
        headers=_cabecalho(a),
        json={"nome": "Alguem", "email": f"alguem_{sufixo}@exemplo.com", "senha": "senhaSegura123"},
    )
    lista_b = client.get("/api/auth/usuarios", headers=_cabecalho(b)).json()
    assert all(u["email"] != f"alguem_{sufixo}@exemplo.com" for u in lista_b)


# --------------------------------------------------------------------- #
# Configuração por empresa
# --------------------------------------------------------------------- #
def test_metas_da_empresa_valem_na_proxima_analise(client, empresa):
    dados = empresa()
    resp = client.put(
        "/api/configuracao", headers=_cabecalho(dados), json={"metas": {"assertividade": 0.40}}
    )
    assert resp.status_code == 200
    assert resp.json()["metas"]["assertividade"] == 0.40
    analise = _subir_analise(client, dados).json()
    assert analise["resultado"]["kpis"]["assert"]["dentro_da_meta"] is False  # 25,7% < 40%


def test_meta_desconhecida_e_recusada(client, empresa):
    dados = empresa()
    resp = client.put("/api/configuracao", headers=_cabecalho(dados), json={"metas": {"inventada": 1}})
    assert resp.status_code == 400


def test_marcacao_nao_paga_muda_o_cac(client, empresa):
    """Marcar 'Parceiro' como origem não paga tira esses fechamentos do CAC do anúncio."""
    dados = empresa()
    base = _subir_analise(client, dados).json()["resultado"]["kpis"]["cac"]["valor"]
    client.put("/api/configuracao", headers=_cabecalho(dados), json={"marcacoes_nao_pagas": ["Parceiro"]})
    depois = _subir_analise(client, dados).json()["resultado"]["kpis"]["cac"]["valor"]
    assert depois > base, "com menos fechamentos atribuídos ao anúncio, o CAC sobe"


def test_config_so_o_admin_altera(client, empresa):
    dados = empresa()
    sufixo = uuid.uuid4().hex[:8]
    client.post(
        "/api/auth/usuarios",
        headers=_cabecalho(dados),
        json={"nome": "Analista", "email": f"m_{sufixo}@exemplo.com", "senha": "senhaSegura123", "papel": "membro"},
    )
    login = client.post(
        "/api/auth/login", json={"email": f"m_{sufixo}@exemplo.com", "senha": "senhaSegura123"}
    ).json()
    assert client.get("/api/configuracao", headers=_cabecalho(login)).status_code == 200
    resp = client.put("/api/configuracao", headers=_cabecalho(login), json={"metas": {"roas": 5}})
    assert resp.status_code == 403


def test_usuario_inativo_nao_acessa(client, empresa):
    dados = empresa()
    with sessao_publica() as db:
        u = db.scalar(select(Usuario).where(Usuario.email == dados["usuario"]["email"]))
        u.ativo = False
    assert client.get("/api/analises", headers=_cabecalho(dados)).status_code == 401
