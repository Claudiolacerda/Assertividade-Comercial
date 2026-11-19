"""Senhas e tokens."""

from __future__ import annotations

import base64
import hashlib
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

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


# --------------------------------------------------------------------------- #
# Segredos de terceiros guardados no banco (tokens de CRM)
# --------------------------------------------------------------------------- #
# Um token de CRM não é senha de usuário: o sistema precisa do valor de volta
# para fazer a chamada, então hash não serve. Fica cifrado, e a chave fica fora
# do banco — quem copiar um dump não leva as contas de CRM dos clientes junto.
#
# A chave vem de CHAVE_CRIPTOGRAFIA. Quando ela não existe, é derivada do
# JWT_SECRET, que todo ambiente já tem e já é obrigado a ser secreto. O preço
# dessa conveniência está escrito aqui para ninguém descobrir do jeito ruim:
# TROCAR O JWT_SECRET TORNA ILEGÍVEL TODO TOKEN DE CRM JÁ SALVO. Eles não se
# perdem calados — `decifrar` levanta erro e a tela pede a reconexão.
_SAL_CRIPTO = b"neriah-conexoes-crm-v1"


@lru_cache(maxsize=1)
def _cifrador() -> Fernet:
    bruta = (settings.chave_criptografia or "").strip()
    if bruta:
        material = bruta.encode("utf-8")
    else:
        material = settings.jwt_secret.encode("utf-8")
    chave = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", material, _SAL_CRIPTO, 200_000, dklen=32)
    )
    return Fernet(chave)


def cifrar(valor: str) -> str:
    if not valor:
        return ""
    return _cifrador().encrypt(valor.encode("utf-8")).decode("ascii")


class SegredoIlegivel(Exception):
    """A chave de hoje não abre o segredo salvo — normalmente o JWT_SECRET mudou."""


def decifrar(valor: str) -> str:
    if not valor:
        return ""
    try:
        return _cifrador().decrypt(valor.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as e:
        raise SegredoIlegivel(
            "Não consegui ler o token salvo desta conexão. Isso acontece quando a chave do "
            "servidor muda (JWT_SECRET ou CHAVE_CRIPTOGRAFIA). Informe o token de novo para "
            "religar a conexão."
        ) from e


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
