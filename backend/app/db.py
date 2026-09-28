"""Conexão com o banco e isolamento por schema.

O ponto sensível do multi-tenant está aqui: `sessao_tenant()` abre uma sessão cujo
`schema_translate_map` aponta o apelido "tenant" para o schema real da empresa. Nenhuma
consulta de análise nomeia o schema, então não existe caminho para uma empresa ler a outra
— e uma requisição sem empresa resolvida simplesmente não tem schema para consultar.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import BasePublic, BaseTenant

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionPublic = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

SLUG_VALIDO = re.compile(r"^[a-z0-9_]{2,40}$")


def nome_schema(slug: str) -> str:
    """Converte o slug da empresa no nome do schema, validando para nunca montar SQL sujo."""
    if not SLUG_VALIDO.match(slug):
        raise ValueError(f"Slug de empresa inválido: {slug!r}")
    return f"tenant_{slug}"


def criar_schemas_base() -> None:
    """Cria as tabelas do schema public (cadastro global)."""
    with engine.begin() as con:
        con.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
    BasePublic.metadata.create_all(engine)


def criar_schema_empresa(schema: str) -> None:
    """Cria o schema da empresa e as tabelas de análise dentro dele."""
    if not schema.startswith("tenant_") or not SLUG_VALIDO.match(schema[len("tenant_"):]):
        raise ValueError(f"Nome de schema inválido: {schema!r}")
    with engine.begin() as con:
        # O nome já foi validado pelo regex acima; identificadores não aceitam bind parameter.
        con.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    motor = engine.execution_options(schema_translate_map={"tenant": schema})
    BaseTenant.metadata.create_all(motor)


def remover_schema_empresa(schema: str) -> None:
    """Remove o schema de uma empresa (usado em testes e no offboarding de cliente)."""
    if not schema.startswith("tenant_") or not SLUG_VALIDO.match(schema[len("tenant_"):]):
        raise ValueError(f"Nome de schema inválido: {schema!r}")
    with engine.begin() as con:
        con.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


@contextmanager
def sessao_publica() -> Iterator[Session]:
    sessao = SessionPublic()
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()


@contextmanager
def sessao_tenant(schema: str) -> Iterator[Session]:
    """Sessão restrita ao schema de uma empresa."""
    if not schema:
        raise ValueError("Schema da empresa não informado.")
    motor = engine.execution_options(schema_translate_map={"tenant": schema})
    sessao = Session(bind=motor, autoflush=False, expire_on_commit=False, future=True)
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()


# ---- dependências do FastAPI ------------------------------------------------ #
def get_db() -> Iterator[Session]:
    with sessao_publica() as s:
        yield s
