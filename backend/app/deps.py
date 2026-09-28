"""Dependências compartilhadas: quem é o usuário e em qual schema ele pode mexer."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db, nome_schema
from .models import Empresa, Usuario
from .security import ler_token

esquema_bearer = HTTPBearer(auto_error=False)


@dataclass
class Atual:
    """O usuário autenticado e o schema da empresa dele — a fronteira do isolamento."""

    usuario: Usuario
    empresa: Empresa
    schema: str


def usuario_atual(
    credencial: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Atual:
    nao_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credencial is None or not credencial.credentials:
        raise nao_autorizado
    dados = ler_token(credencial.credentials)
    if not dados or "sub" not in dados:
        raise nao_autorizado

    usuario = db.get(Usuario, int(dados["sub"]))
    if usuario is None or not usuario.ativo:
        raise nao_autorizado
    empresa = db.get(Empresa, usuario.empresa_id)
    if empresa is None or not empresa.ativa:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa inativa. Fale com o suporte.")
    # O schema vem do banco, nunca do token — um token adulterado não muda de empresa.
    return Atual(usuario=usuario, empresa=empresa, schema=nome_schema(empresa.slug))


def admin_atual(atual: Atual = Depends(usuario_atual)) -> Atual:
    if atual.usuario.papel != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só o administrador da empresa pode fazer isso.",
        )
    return atual
