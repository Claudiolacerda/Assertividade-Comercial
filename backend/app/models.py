"""Modelo de dados.

Três níveis:

* **schema `public`** — o cadastro global. Uma `Organizacao` é quem assina o Neriah:
  pode ser uma agência com vários clientes na carteira, ou uma empresa que usa
  para si. Cada cliente analisado é uma `Empresa`. Os usuários pertencem à
  organização, não à empresa — é isso que permite um gestor de tráfego abrir dez
  clientes com um login só.
* **schema `tenant_<slug>`** — os dados de cada `Empresa`: uploads e análises. Um
  `schema_translate_map` por requisição decide em qual schema a consulta cai, então
  nenhuma query de análise consegue ler outra empresa.
* **`AcessoEmpresa`** — a exceção: o cliente final da agência, que enxerga só o
  próprio painel.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --------------------------------------------------------------------------- #
# public: cadastro global
# --------------------------------------------------------------------------- #
class BasePublic(DeclarativeBase):
    metadata = MetaData(schema="public")


class Organizacao(BasePublic):
    """Quem assina o Neriah. Agência (vários clientes) ou empresa direta (um)."""

    __tablename__ = "organizacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), default="direta", nullable=False)  # agencia | direta
    plano: Mapped[str] = mapped_column(String(40), default="basico", nullable=False)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresas: Mapped[list["Empresa"]] = relationship(back_populates="organizacao", cascade="all, delete-orphan")
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="organizacao", cascade="all, delete-orphan")


class Empresa(BasePublic):
    """Um cliente analisado. Tem schema próprio no banco."""

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizacao_id: Mapped[int] = mapped_column(
        ForeignKey("public.organizacoes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    schema_banco: Mapped[str] = mapped_column(String(63), unique=True, nullable=False)
    segmento: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Destino do relatório mensal no WhatsApp
    whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Configuração da análise desta empresa (metas, vocabulário de status...)
    config_analise: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organizacao: Mapped[Organizacao] = relationship(back_populates="empresas")


class Usuario(BasePublic):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizacao_id: Mapped[int] = mapped_column(
        ForeignKey("public.organizacoes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # admin  = gerencia clientes, metas e usuários da organização
    # membro = analisa todos os clientes da carteira, não gerencia
    # cliente = enxerga só as empresas listadas em AcessoEmpresa, sem alterar nada
    papel: Mapped[str] = mapped_column(String(20), default="membro", nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organizacao: Mapped[Organizacao] = relationship(back_populates="usuarios")
    acessos: Mapped[list["AcessoEmpresa"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class AcessoEmpresa(BasePublic):
    """Quais empresas um usuário de papel 'cliente' pode ver.

    Para admin e membro esta tabela é ignorada: eles enxergam toda a carteira.
    """

    __tablename__ = "acessos_empresa"
    __table_args__ = (UniqueConstraint("usuario_id", "empresa_id", name="uq_acesso_usuario_empresa"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("public.usuarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("public.empresas.id", ondelete="CASCADE"), index=True, nullable=False
    )


# --------------------------------------------------------------------------- #
# tenant_<slug>: dados de cada cliente
# --------------------------------------------------------------------------- #
class BaseTenant(DeclarativeBase):
    """Tabelas sem schema fixo: o schema real é resolvido por requisição.

    `schema="tenant"` é apenas um apelido — `db.sessao_tenant()` traduz esse apelido
    para `tenant_<slug>` da empresa que está sendo consultada.
    """

    metadata = MetaData(schema="tenant")


class Arquivo(BaseTenant):
    """Um arquivo enviado (CSV da Meta ou planilha comercial)."""

    __tablename__ = "arquivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analise_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenant.analises.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # meta | reunioes
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    caminho: Mapped[str] = mapped_column(Text, nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hash_md5: Mapped[str] = mapped_column(String(32), nullable=False)
    enviado_por: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enviado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analise: Mapped["Analise"] = relationship(back_populates="arquivos")


class Analise(BaseTenant):
    """Uma rodada de análise de um mês — é o que dá o histórico mês a mês."""

    __tablename__ = "analises"
    __table_args__ = (UniqueConstraint("mes_referencia", "versao", name="uq_analise_mes_versao"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mes_referencia: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # "2026-09"
    versao: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="processando", nullable=False)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Resultado completo (KPIs, diagnóstico, tabelas) — o painel lê daqui
    # JSON e não JSONB: o JSONB normaliza o objeto e REORDENA as chaves por
    # tamanho, o que embaralha a ordem das colunas de toda tabela do resultado
    # ("Clientes" vinha antes de "Sinal na observação" porque é mais curto).
    # Aqui a ordem é informação: ela é a ordem de leitura da tabela na tela e
    # no Excel. O JSON guarda o texto como veio.
    resultado: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # KPIs achatados para o gráfico de evolução e para a carteira da agência
    kpis_resumo: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    config_usada: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    caminho_excel: Mapped[str | None] = mapped_column(Text, nullable=True)
    criada_por: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    arquivos: Mapped[list[Arquivo]] = relationship(back_populates="analise", cascade="all, delete-orphan")


class Cadencia(BaseTenant):
    """Um fluxo de cadência desenhado no canvas.

    O grafo inteiro vive em JSONB: o formato é do front (nós e ligações), e
    guardá-lo assim evita uma tabela de nós que só existiria para ser remontada
    a cada carregamento.
    """

    __tablename__ = "cadencias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    fluxo: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # de onde veio a sugestão, quando foi gerada a partir de uma análise
    origem: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criada_por: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
