"""Modelo de dados.

Dois níveis, conforme a decisão de arquitetura:

* **schema `public`** — o cadastro global: empresas (tenants) e usuários. Precisa ser
  global porque o login acontece antes de sabermos de qual empresa o usuário é.
* **schema `tenant_<slug>`** — os dados de cada cliente: uploads e análises. Cada empresa
  tem o seu, no mesmo servidor Postgres. Um `schema_translate_map` por requisição decide
  em qual schema a consulta cai, então nenhuma query de análise consegue ler outra empresa.
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --------------------------------------------------------------------------- #
# public: cadastro global
# --------------------------------------------------------------------------- #
class BasePublic(DeclarativeBase):
    metadata = MetaData(schema="public")


class Empresa(BasePublic):
    """Um cliente seu (tenant)."""

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    schema_banco: Mapped[str] = mapped_column(String(63), unique=True, nullable=False)
    plano: Mapped[str] = mapped_column(String(40), default="basico", nullable=False)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Configuração da análise específica desta empresa (metas, vocabulário de status...)
    config_analise: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")


class Usuario(BasePublic):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("public.empresas.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[str] = mapped_column(String(20), default="membro", nullable=False)  # admin | membro
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    empresa: Mapped[Empresa] = relationship(back_populates="usuarios")


# --------------------------------------------------------------------------- #
# tenant_<slug>: dados de cada cliente
# --------------------------------------------------------------------------- #
class BaseTenant(DeclarativeBase):
    """Tabelas sem schema fixo: o schema real é resolvido por requisição.

    `schema="tenant"` é apenas um apelido — `db.sessao_tenant()` traduz esse apelido
    para `tenant_<slug>` da empresa do usuário autenticado.
    """

    metadata = MetaData(schema="tenant")


class Arquivo(BaseTenant):
    """Um arquivo enviado pelo cliente (CSV da Meta ou planilha comercial)."""

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
    # processando | concluida | erro
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Resultado completo (KPIs, diagnóstico, tabelas) — o painel lê daqui, sem reprocessar
    resultado: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # KPIs achatados para o gráfico de evolução entre meses
    kpis_resumo: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    config_usada: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    caminho_excel: Mapped[str | None] = mapped_column(Text, nullable=True)
    criada_por: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    arquivos: Mapped[list[Arquivo]] = relationship(back_populates="analise", cascade="all, delete-orphan")
