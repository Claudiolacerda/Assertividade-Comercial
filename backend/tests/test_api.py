"""Testes da API, com foco no isolamento.

São duas fronteiras a defender, não uma:
  * entre organizações — uma agência não alcança a carteira de outra;
  * entre clientes da mesma organização — um usuário do tipo "cliente" só vê
    o próprio painel, mesmo estando na mesma agência.

Precisam de um Postgres acessível (o isolamento por schema é recurso do Postgres).
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.config import settings
from app.db import criar_schemas_base, engine, remover_schema_empresa, sessao_publica
from app.main import app
from app.models import Empresa, Organizacao, Usuario

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"
REUNIOES = DADOS / "reunioes" / "Controle_Comercial_Exemplo_-_Setembro.csv"


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
def org(client):
    """Cria organizações novas e limpa schemas e registros no fim."""
    criadas: list[str] = []

    def criar(nome: str | None = None, tipo: str = "direta", empresa: str | None = None):
        sufixo = uuid.uuid4().hex[:8]
        nome = nome or f"Org {sufixo}"
        resp = client.post(
            "/api/auth/cadastro",
            json={
                "organizacao": nome,
                "tipo": tipo,
                "empresa": empresa,
                "nome": "Dono da Conta",
                "email": f"dono_{sufixo}@exemplo.com.br",
                "senha": "senhaSegura123",
            },
        )
        assert resp.status_code == 201, resp.text
        dados = resp.json()
        criadas.append(dados["usuario"]["organizacao"]["slug"])
        return dados

    yield criar

    for slug in criadas:
        with sessao_publica() as db:
            o = db.scalar(select(Organizacao).where(Organizacao.slug == slug))
            if o:
                for e in db.scalars(select(Empresa).where(Empresa.organizacao_id == o.id)).all():
                    remover_schema_empresa(e.schema_banco)
                    pasta = Path(settings.dir_uploads) / e.slug
                    if pasta.exists():
                        shutil.rmtree(pasta, ignore_errors=True)
                db.delete(o)


def cab(dados, empresa_id: int | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {dados['access_token']}"}
    if empresa_id is not None:
        h["X-Empresa"] = str(empresa_id)
    return h


def empresa_id(dados, indice: int = 0) -> int:
    return dados["usuario"]["empresas"][indice]["id"]


def subir(client, dados, empresa: int | None = None, mes: str | None = None):
    with META.open("rb") as fm, REUNIOES.open("rb") as fr:
        return client.post(
            "/api/analises",
            headers=cab(dados, empresa),
            files=[
                ("arquivos_meta", (META.name, fm, "text/csv")),
                ("arquivos_reunioes", (REUNIOES.name, fr, "text/csv")),
            ],
            data={"mes_referencia": mes} if mes else {},
        )


# --------------------------------------------------------------------- #
# Cadastro e sessão
# --------------------------------------------------------------------- #
def test_saude(client):
    assert client.get("/api/saude").json()["status"] == "ok"


def test_cadastro_cria_organizacao_com_primeiro_cliente(client, org):
    dados = org("Contabilidade Horizonte")
    u = dados["usuario"]
    assert u["organizacao"]["tipo"] == "direta"
    assert len(u["empresas"]) == 1
    assert u["empresas"][0]["nome"] == "Contabilidade Horizonte"
    slug = u["empresas"][0]["slug"]
    with engine.connect() as con:
        existe = con.execute(
            text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"), {"s": f"tenant_{slug}"}
        ).first()
    assert existe, "o schema do cliente deveria existir"


def test_agencia_nomeia_o_primeiro_cliente_separadamente(client, org):
    dados = org("Agência Ponto Verde", tipo="agencia", empresa="Padaria do Zé")
    assert dados["usuario"]["organizacao"]["nome"] == "Agência Ponto Verde"
    assert dados["usuario"]["empresas"][0]["nome"] == "Padaria do Zé"


def test_email_duplicado_e_recusado(client, org):
    dados = org()
    resp = client.post(
        "/api/auth/cadastro",
        json={
            "organizacao": "Outra", "nome": "Outro",
            "email": dados["usuario"]["email"], "senha": "senhaSegura123",
        },
    )
    assert resp.status_code == 409


def test_login_com_senha_errada(client, org):
    dados = org()
    resp = client.post("/api/auth/login", json={"email": dados["usuario"]["email"], "senha": "errada123"})
    assert resp.status_code == 401
    assert "incorretos" in resp.json()["detail"]


def test_senha_fraca_e_recusada(client):
    resp = client.post(
        "/api/auth/cadastro",
        json={"organizacao": "X", "nome": "Yz", "email": "z@exemplo.com", "senha": "12345678"},
    )
    assert resp.status_code == 422


def test_rota_protegida_sem_token(client):
    assert client.get("/api/analises").status_code == 401


def test_token_invalido(client):
    assert client.get("/api/analises", headers={"Authorization": "Bearer nada"}).status_code == 401


# --------------------------------------------------------------------- #
# Carteira
# --------------------------------------------------------------------- #
def test_agencia_adiciona_clientes_a_carteira(client, org):
    ag = org("Agência Alfa", tipo="agencia", empresa="Cliente 1")
    for nome in ["Cliente 2", "Cliente 3"]:
        r = client.post("/api/empresas", headers=cab(ag), json={"nome": nome, "segmento": "contabilidade"})
        assert r.status_code == 201, r.text
    lista = client.get("/api/empresas", headers=cab(ag)).json()
    assert {e["nome"] for e in lista} == {"Cliente 1", "Cliente 2", "Cliente 3"}
    # cada cliente ganhou schema próprio
    with engine.connect() as con:
        for e in lista:
            achou = con.execute(
                text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
                {"s": f"tenant_{e['slug']}"},
            ).first()
            assert achou, f"faltou schema de {e['nome']}"


def test_cliente_repetido_na_mesma_carteira_e_recusado(client, org):
    ag = org("Agência Beta", tipo="agencia", empresa="Padaria")
    r = client.post("/api/empresas", headers=cab(ag), json={"nome": "padaria"})
    assert r.status_code == 409


def test_mesmo_nome_em_agencias_diferentes_ganha_schema_proprio(client, org):
    a = org("Agência Um", tipo="agencia", empresa="Padaria do Zé")
    b = org("Agência Dois", tipo="agencia", empresa="Padaria do Zé")
    slug_a = a["usuario"]["empresas"][0]["slug"]
    slug_b = b["usuario"]["empresas"][0]["slug"]
    assert slug_a != slug_b, "dois clientes homônimos não podem dividir schema"


def test_carteira_traz_kpis_e_variacao(client, org):
    ag = org("Agência Gama", tipo="agencia", empresa="Cliente A")
    outro = client.post("/api/empresas", headers=cab(ag), json={"nome": "Cliente B"}).json()
    a = empresa_id(ag)
    assert subir(client, ag, a).status_code == 201
    assert subir(client, ag, a, mes="2026-08").status_code == 201

    carteira = client.get("/api/empresas/carteira", headers=cab(ag)).json()
    por_nome = {i["empresa"]["nome"]: i for i in carteira}
    assert set(por_nome) == {"Cliente A", "Cliente B"}

    ca = por_nome["Cliente A"]
    assert ca["total_analises"] == 2
    assert ca["ultimo_mes"] == "2026-09"
    assert ca["kpis"]["fec"] == 9
    assert ca["variacao"] is not None and "assert" in ca["variacao"]

    cb = por_nome["Cliente B"]
    assert cb["total_analises"] == 0 and cb["ultimo_mes"] is None
    assert cb["empresa"]["id"] == outro["id"]


def test_nao_da_para_esvaziar_a_carteira(client, org):
    d = org("Agência Delta", tipo="agencia", empresa="Único")
    r = client.delete(f"/api/empresas/{empresa_id(d)}", headers=cab(d))
    assert r.status_code == 400
    assert "vazia" in r.json()["detail"]


def test_arquivar_tira_o_cliente_da_carteira(client, org):
    ag = org("Agência Épsilon", tipo="agencia", empresa="Fica")
    sai = client.post("/api/empresas", headers=cab(ag), json={"nome": "Sai"}).json()
    assert client.delete(f"/api/empresas/{sai['id']}", headers=cab(ag)).status_code == 204
    nomes = {e["nome"] for e in client.get("/api/empresas", headers=cab(ag)).json()}
    assert nomes == {"Fica"}


# --------------------------------------------------------------------- #
# Análise
# --------------------------------------------------------------------- #
def test_upload_roda_analise_e_devolve_kpis(client, org):
    dados = org()
    resp = subir(client, dados)
    assert resp.status_code == 201, resp.text
    corpo = resp.json()
    assert corpo["mes_referencia"] == "2026-09"
    kpis = corpo["resultado"]["kpis"]
    assert kpis["fec"]["valor"] == 9
    assert kpis["assert"]["texto"] == "25,7%"
    assert corpo["kpis_resumo"]["cac"] == pytest.approx(405.67, abs=0.01)


def test_analise_traz_a_nota_da_planilha(client, org):
    """A cobertura vira tarefa para o cliente: o que falta e o que aquilo destrava."""
    dados = org()
    cob = subir(client, dados).json()["resultado"]["cobertura"]
    assert cob["total"] == 13
    assert cob["encontrados"] == 6
    assert set(cob["faltando_alto_impacto"]) == {"Valor", "Campanha", "Origem", "Motivo da perda"}
    valor = next(c for c in cob["campos"] if c["campo"] == "valor")
    assert valor["encontrado"] is False and "ROAS" in valor["destrava"]
    cliente = next(c for c in cob["campos"] if c["campo"] == "cliente")
    assert cliente["encontrado"] is True and cliente["coluna"] == "Cliente"


def test_sem_cabecalho_x_empresa_usa_o_primeiro_cliente(client, org):
    ag = org("Agência Zeta", tipo="agencia", empresa="Aa Primeiro")
    client.post("/api/empresas", headers=cab(ag), json={"nome": "Zz Segundo"})
    assert subir(client, ag).status_code == 201  # sem X-Empresa
    lista = client.get("/api/analises", headers=cab(ag)).json()
    assert len(lista) == 1


def test_analise_vai_para_o_cliente_escolhido(client, org):
    ag = org("Agência Eta", tipo="agencia", empresa="Cliente X")
    y = client.post("/api/empresas", headers=cab(ag), json={"nome": "Cliente Y"}).json()
    assert subir(client, ag, y["id"]).status_code == 201
    assert client.get("/api/analises", headers=cab(ag, y["id"])).json() != []
    assert client.get("/api/analises", headers=cab(ag, empresa_id(ag))).json() == []


def test_arquivo_de_formato_invalido(client, org):
    dados = org()
    resp = client.post(
        "/api/analises",
        headers=cab(dados),
        files=[
            ("arquivos_meta", ("relatorio.pdf", b"%PDF-1.4", "application/pdf")),
            ("arquivos_reunioes", ("p.csv", b"Cliente,Status\nA,Fechado\n", "text/csv")),
        ],
    )
    assert resp.status_code == 400


def test_planilha_sem_as_colunas_certas_da_erro_explicativo(client, org):
    dados = org()
    resp = client.post(
        "/api/analises",
        headers=cab(dados),
        files=[
            ("arquivos_meta", ("meta.csv", b"coisa,outra\n1,2\n", "text/csv")),
            ("arquivos_reunioes", ("r.csv", b"Cliente,Etapa do Funil\nA,Fechado\n", "text/csv")),
        ],
    )
    assert resp.status_code == 422
    assert "Meta" in resp.json()["detail"]


def test_segunda_analise_do_mesmo_mes_vira_nova_versao(client, org):
    dados = org()
    assert subir(client, dados).json()["versao"] == 1
    assert subir(client, dados).json()["versao"] == 2


def test_download_do_excel(client, org):
    dados = org()
    a = subir(client, dados).json()
    resp = client.get(f"/api/analises/{a['id']}/excel", headers=cab(dados))
    assert resp.status_code == 200 and resp.content[:2] == b"PK"


# --------------------------------------------------------------------- #
# Isolamento entre organizações
# --------------------------------------------------------------------- #
def test_agencia_nao_ve_analise_de_outra(client, org):
    a, b = org("Agência A"), org("Agência B")
    analise = subir(client, a).json()

    assert client.get("/api/analises", headers=cab(b)).json() == []
    assert client.get(f"/api/analises/{analise['id']}", headers=cab(b)).status_code == 404
    assert client.get(f"/api/analises/{analise['id']}/excel", headers=cab(b)).status_code == 404


def test_cabecalho_com_empresa_de_outra_organizacao_e_recusado(client, org):
    """O ataque mais óbvio: mandar o id da empresa alheia no X-Empresa."""
    a, b = org("Agência C"), org("Agência D")
    alheia = empresa_id(a)
    resp = client.get("/api/analises", headers=cab(b, alheia))
    assert resp.status_code == 404, "id de outra organização não pode ser aceito"
    assert subir(client, b, alheia).status_code == 404


def test_carteira_mostra_so_a_propria_organizacao(client, org):
    a, b = org("Agência E", tipo="agencia", empresa="Cliente de A"), org("Agência F")
    nomes_b = {i["empresa"]["nome"] for i in client.get("/api/empresas/carteira", headers=cab(b)).json()}
    assert "Cliente de A" not in nomes_b


def test_ids_reiniciam_por_cliente_e_nao_colidem(client, org):
    a, b = org("Agência G"), org("Agência H")
    ida = subir(client, a).json()["id"]
    idb = subir(client, b).json()["id"]
    assert ida == idb == 1  # mesma numeração, schemas diferentes
    da = client.get(f"/api/analises/{ida}", headers=cab(a)).json()
    dbb = client.get(f"/api/analises/{idb}", headers=cab(b)).json()
    assert da["id"] == dbb["id"]


# --------------------------------------------------------------------- #
# Papéis
# --------------------------------------------------------------------- #
def _criar_usuario(client, dados, papel, empresas=None):
    sufixo = uuid.uuid4().hex[:8]
    email = f"u_{sufixo}@exemplo.com"
    corpo = {"nome": "Fulano de Tal", "email": email, "senha": "senhaSegura123", "papel": papel}
    if empresas:
        corpo["empresas"] = empresas
    r = client.post("/api/auth/usuarios", headers=cab(dados), json=corpo)
    assert r.status_code == 201, r.text
    return client.post("/api/auth/login", json={"email": email, "senha": "senhaSegura123"}).json()


def test_membro_ve_a_carteira_inteira_mas_nao_gerencia(client, org):
    ag = org("Agência Iota", tipo="agencia", empresa="Cliente 1")
    client.post("/api/empresas", headers=cab(ag), json={"nome": "Cliente 2"})
    membro = _criar_usuario(client, ag, "membro")
    assert len(membro["usuario"]["empresas"]) == 2
    assert client.post("/api/empresas", headers=cab(membro), json={"nome": "Cliente 3"}).status_code == 403


def test_cliente_final_ve_so_o_proprio_painel(client, org):
    """O caso que justifica o papel: a agência libera o painel para o cliente dela."""
    ag = org("Agência Kappa", tipo="agencia", empresa="Cliente Um")
    dois = client.post("/api/empresas", headers=cab(ag), json={"nome": "Cliente Dois"}).json()
    final = _criar_usuario(client, ag, "cliente", empresas=[dois["id"]])

    liberadas = final["usuario"]["empresas"]
    assert [e["nome"] for e in liberadas] == ["Cliente Dois"]
    # não alcança o outro cliente da mesma agência
    assert client.get("/api/analises", headers=cab(final, empresa_id(ag))).status_code == 404
    assert {i["empresa"]["nome"] for i in client.get("/api/empresas/carteira", headers=cab(final)).json()} == {
        "Cliente Dois"
    }


def test_cliente_sem_empresa_liberada_e_recusado(client, org):
    ag = org("Agência Lambda", tipo="agencia", empresa="Cliente Só")
    sufixo = uuid.uuid4().hex[:8]
    r = client.post(
        "/api/auth/usuarios",
        headers=cab(ag),
        json={"nome": "Sem Acesso", "email": f"s_{sufixo}@e.com", "senha": "senhaSegura123", "papel": "cliente"},
    )
    assert r.status_code == 400


def test_usuario_criado_entra_na_organizacao_de_quem_criou(client, org):
    a, b = org("Agência Mu"), org("Agência Nu")
    novo = _criar_usuario(client, a, "membro")
    assert novo["usuario"]["organizacao"]["id"] == a["usuario"]["organizacao"]["id"]
    lista_b = client.get("/api/auth/usuarios", headers=cab(b)).json()
    assert all(u["email"] != novo["usuario"]["email"] for u in lista_b)


def test_membro_nao_apaga_analise(client, org):
    dados = org()
    analise = subir(client, dados).json()
    membro = _criar_usuario(client, dados, "membro")
    assert client.delete(f"/api/analises/{analise['id']}", headers=cab(membro)).status_code == 403
    assert client.delete(f"/api/analises/{analise['id']}", headers=cab(dados)).status_code == 204


def test_usuario_inativo_nao_acessa(client, org):
    dados = org()
    with sessao_publica() as db:
        u = db.scalar(select(Usuario).where(Usuario.email == dados["usuario"]["email"]))
        u.ativo = False
    assert client.get("/api/analises", headers=cab(dados)).status_code == 401


# --------------------------------------------------------------------- #
# Configuração por cliente
# --------------------------------------------------------------------- #
def test_metas_sao_por_cliente_e_nao_por_organizacao(client, org):
    """Dois clientes da mesma agência têm metas independentes."""
    ag = org("Agência Xi", tipo="agencia", empresa="Cliente Meta A")
    b = client.post("/api/empresas", headers=cab(ag), json={"nome": "Cliente Meta B"}).json()
    a_id = empresa_id(ag)

    r = client.put("/api/configuracao", headers=cab(ag, a_id), json={"metas": {"assertividade": 0.40}})
    assert r.status_code == 200
    assert client.get("/api/configuracao", headers=cab(ag, a_id)).json()["metas"]["assertividade"] == 0.40
    assert client.get("/api/configuracao", headers=cab(ag, b["id"])).json()["metas"]["assertividade"] == 0.25

    assert subir(client, ag, a_id).json()["resultado"]["kpis"]["assert"]["dentro_da_meta"] is False
    assert subir(client, ag, b["id"]).json()["resultado"]["kpis"]["assert"]["dentro_da_meta"] is True


def test_marcacao_nao_paga_muda_o_cac(client, org):
    dados = org()
    base = subir(client, dados).json()["resultado"]["kpis"]["cac"]["valor"]
    client.put("/api/configuracao", headers=cab(dados), json={"marcacoes_nao_pagas": ["Parceiro"]})
    depois = subir(client, dados).json()["resultado"]["kpis"]["cac"]["valor"]
    assert depois > base


def test_config_so_o_admin_altera(client, org):
    dados = org()
    membro = _criar_usuario(client, dados, "membro")
    assert client.get("/api/configuracao", headers=cab(membro)).status_code == 200
    assert client.put("/api/configuracao", headers=cab(membro), json={"metas": {"roas": 5}}).status_code == 403


# --------------------------------------------------------------------- #
# Planilha-modelo
# --------------------------------------------------------------------- #
def test_modelo_baixa_sem_login(client):
    """É isca de site: quem baixa o modelo está a um passo de subir a planilha."""
    resp = client.get("/api/modelo/planilha-comercial.xlsx")
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"
    assert "Modelo_Comercial_Neriah.xlsx" in resp.headers["content-disposition"]


def test_modelo_lista_os_campos(client):
    corpo = client.get("/api/modelo/campos").json()
    assert len(corpo["campos"]) == 13
    assert "Fechado" in corpo["etapas"]
    valor = next(c for c in corpo["campos"] if c["campo"] == "valor")
    assert valor["impacto"] == "alto"


def test_planilha_modelo_e_lida_pelo_proprio_motor(client, org, tmp_path):
    """O modelo tem que destravar os 13 campos — senão ele não resolve nada."""
    dados = org()
    modelo = client.get("/api/modelo/planilha-comercial.xlsx").content
    caminho = tmp_path / "modelo.xlsx"
    caminho.write_bytes(modelo)
    with META.open("rb") as fm, caminho.open("rb") as fr:
        resp = client.post(
            "/api/analises",
            headers=cab(dados),
            files=[
                ("arquivos_meta", (META.name, fm, "text/csv")),
                ("arquivos_reunioes", ("modelo.xlsx", fr,
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ],
        )
    assert resp.status_code == 201, resp.text
    cob = resp.json()["resultado"]["cobertura"]
    assert cob["encontrados"] == 13, f"o modelo deveria destravar tudo, destravou {cob['encontrados']}"
    assert cob["faltando_alto_impacto"] == []
    assert resp.json()["resultado"]["kpis"]["roas"]["valor"] > 0


# --------------------------------------------------------------------- #
# Modo agência: desligado por padrão, ligável depois
# --------------------------------------------------------------------- #
def test_conta_nasce_sem_modo_agencia(client, org):
    """Quem não marcou agência no cadastro não vê carteira nenhuma."""
    dados = org("Empresa Simples")
    assert dados["usuario"]["organizacao"]["tipo"] == "direta"
    assert len(dados["usuario"]["empresas"]) == 1


def test_ligar_modo_agencia_libera_a_carteira(client, org):
    """A saída para quem passa a atender outros clientes depois de assinar."""
    dados = org("Vira Agência")
    assert client.get("/api/organizacao", headers=cab(dados)).json()["tipo"] == "direta"

    r = client.put("/api/organizacao/tipo", headers=cab(dados), json={"tipo": "agencia"})
    assert r.status_code == 200 and r.json()["tipo"] == "agencia"

    novo = client.post("/api/empresas", headers=cab(dados), json={"nome": "Cliente Novo"})
    assert novo.status_code == 201
    assert client.get("/api/auth/eu", headers=cab(dados)).json()["organizacao"]["tipo"] == "agencia"


def test_desligar_agencia_com_carteira_cheia_e_recusado(client, org):
    ag = org("Agência Ômicron", tipo="agencia", empresa="Cliente 1")
    client.post("/api/empresas", headers=cab(ag), json={"nome": "Cliente 2"})
    r = client.put("/api/organizacao/tipo", headers=cab(ag), json={"tipo": "direta"})
    assert r.status_code == 400
    assert "Arquive" in r.json()["detail"]


def test_so_admin_liga_modo_agencia(client, org):
    dados = org("Agência Pi")
    membro = _criar_usuario(client, dados, "membro")
    assert client.put("/api/organizacao/tipo", headers=cab(membro), json={"tipo": "agencia"}).status_code == 403


def test_tipo_invalido_e_recusado(client, org):
    dados = org()
    assert client.put("/api/organizacao/tipo", headers=cab(dados), json={"tipo": "qualquer"}).status_code == 422


# --------------------------------------------------------------------- #
# Relatório de WhatsApp
# --------------------------------------------------------------------- #
def test_previa_do_relatorio_de_whatsapp(client, org):
    dados = org("Contabilidade Horizonte")
    analise = subir(client, dados).json()
    r = client.get(f"/api/analises/{analise['id']}/whatsapp", headers=cab(dados))
    assert r.status_code == 200
    corpo = r.json()
    t = corpo["texto"]
    assert "Contabilidade Horizonte — setembro/2026" in t
    assert "*R$ 3.651,02*" in t  # negrito do WhatsApp, não markdown
    assert "Assertividade" in t and "25,7%" in t
    # sem credencial o link wa.me sempre funciona
    assert corpo["link"].startswith("https://wa.me/")
    assert corpo["envio_automatico"] is False


def test_relatorio_nao_leva_recado_tecnico_ao_cliente(client, org):
    """Avisos sobre a planilha são de quem opera; o cliente recebe o resultado."""
    dados = org()
    analise = subir(client, dados).json()
    t = client.get(f"/api/analises/{analise['id']}/whatsapp", headers=cab(dados)).json()["texto"]
    assert "sem gasto e sem impressões" not in t
    assert "REGRAS_STATUS" not in t and "coluna" not in t.lower()


def test_relatorio_completo_traz_a_nota_da_planilha(client, org):
    dados = org()
    analise = subir(client, dados).json()
    t = client.get(
        f"/api/analises/{analise['id']}/whatsapp?completo=true", headers=cab(dados)
    ).json()["texto"]
    assert "6/13 campos" in t


def test_relatorio_compara_com_o_mes_anterior(client, org):
    dados = org()
    subir(client, dados, mes="2026-08")
    atual = subir(client, dados).json()
    t = client.get(f"/api/analises/{atual['id']}/whatsapp", headers=cab(dados)).json()["texto"]
    # mesmos dados nos dois meses: variação abaixo de 3% não vira notícia
    assert "mês passado" not in t


def test_salvar_whatsapp_do_cliente(client, org):
    dados = org()
    r = client.put("/api/whatsapp", headers=cab(dados), json={"numero": "(83) 99853-9248"})
    assert r.status_code == 200 and r.json()["numero"] == "(83) 99853-9248"
    analise = subir(client, dados).json()
    link = client.get(f"/api/analises/{analise['id']}/whatsapp", headers=cab(dados)).json()["link"]
    assert link.startswith("https://wa.me/5583998539248?text=")


def test_numero_invalido_e_recusado(client, org):
    dados = org()
    r = client.put("/api/whatsapp", headers=cab(dados), json={"numero": "123"})
    assert r.status_code == 400
    assert "não parece válido" in r.json()["detail"] or "dígitos" in r.json()["detail"]


def test_envio_sem_provedor_explica_o_caminho(client, org):
    """Sem credencial o sistema não finge que enviou — diz o que fazer."""
    dados = org()
    analise = subir(client, dados).json()
    r = client.post(
        f"/api/analises/{analise['id']}/whatsapp/enviar",
        headers=cab(dados),
        json={"numero": "83998539248"},
    )
    assert r.status_code == 400
    assert "Abrir no WhatsApp" in r.json()["detail"]


def test_relatorio_de_outra_organizacao_e_recusado(client, org):
    a, b = org("Agência Rho"), org("Agência Sigma")
    analise = subir(client, a).json()
    assert client.get(f"/api/analises/{analise['id']}/whatsapp", headers=cab(b)).status_code == 404
