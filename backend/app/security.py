"""Senhas e tokens."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from .config import settings

# bcrypt direto, sem passlib: passlib não tem manutenção e quebra com bcrypt >= 4.1.
CUSTO_BCRYPT = 12


def hash_senha(senha: str) -> str:
    bruto = senha.encode("utf-8")
    # bcrypt ignora o que passa de 72 bytes; recusar é melhor que truncar calado
    if len(bruto) > 72:
        raise ValueError("A senha é longa demais (máximo 72 bytes).")
    return bcrypt.hashpw(bruto, bcrypt.gensalt(rounds=CUSTO_BCRYPT)).decode("utf-8")


def conferir_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def criar_token(dados: dict[str, Any], expira_minutos: int | None = None) -> str:
    conteudo = dados.copy()
    expira = datetime.now(timezone.utc) + timedelta(minutes=expira_minutos or settings.jwt_expira_minutos)
    conteudo.update({"exp": expira})
    return jwt.encode(conteudo, settings.jwt_secret, algorithm=settings.jwt_algoritmo)


def ler_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algoritmo])
    except jwt.PyJWTError:
        return None


def gerar_slug(nome: str) -> str:
    """Nome da empresa -> slug usável como nome de schema Postgres."""
    base = unicodedata.normalize("NFKD", nome.strip().lower()).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")[:34]
    if not base:
        base = "empresa"
    if base[0].isdigit():  # schema não pode começar com número
        base = f"e_{base}"
    return base
