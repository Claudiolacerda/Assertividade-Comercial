"""Dependências compartilhadas: quem é o usuário, de qual organização, e qual
empresa da carteira ele está olhando agora.

A fronteira do isolamento mora aqui. Duas regras que nunca podem ser afrouxadas:

1. A organização vem do banco, a partir do id do usuário no token — nunca do
   token em si. Token adulterado não muda de organização.
2. A empresa pedida no cabeçalho `X-Empresa` só é aceita depois de confirmada
   como pertencente à organização do usuário (e, para papel "cliente", à lista
   de acessos dele).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db, nome_schema
from .models import AcessoEmpresa, Empresa, Organizacao, Usuario
from .security import ler_token

esquema_bearer = HTTPBearer(auto_error=False)

NAO_AUTORIZADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sessão inválida ou expirada. Faça login novamente.",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class Sessao:
    """Usuário autenticado e a organização dele."""

    usuario: Usuario
    organizacao: Organizacao

    @property
    def ve_tudo(self) -> bool:
        """admin e membro enxergam a carteira inteira; cliente, só o que foi liberado."""
        return self.usuario.papel in ("admin", "membro")


@dataclass
class Atual(Sessao):
    """Sessão + a empresa que está sendo consultada nesta requisição."""

    empresa: Empresa
    schema: str


def empresas_visiveis(db: Session, sessao: Sessao) -> list[Empresa]:
    """A carteira que este usuário pode abrir, já filtrada pelo papel."""
    consulta = (
        select(Empresa)
        .where(Empresa.organizacao_id == sessao.organizacao.id, Empresa.ativa.is_(True))
        .order_by(Empresa.nome)
    )
    if not sessao.ve_tudo:
        consulta = consulta.join(
            AcessoEmpresa,
            (AcessoEmpresa.empresa_id == Empresa.id) & (AcessoEmpresa.usuario_id == sessao.usuario.id),
        )
    return list(db.scalars(consulta).all())


def sessao_atual(
    credencial: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Sessao:
    if credencial is None or not credencial.credentials:
        raise NAO_AUTORIZADO
    dados = ler_token(credencial.credentials)
    if not dados or "sub" not in dados:
        raise NAO_AUTORIZADO

    usuario = db.get(Usuario, int(dados["sub"]))
    if usuario is None or not usuario.ativo:
        raise NAO_AUTORIZADO
    # A organização vem do banco, não do token.
    organizacao = db.get(Organizacao, usuario.organizacao_id)
    if organizacao is None or not organizacao.ativa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Organização inativa. Fale com o suporte."
        )
    return Sessao(usuario=usuario, organizacao=organizacao)


def usuario_atual(
    x_empresa: int | None = Header(default=None, alias="X-Empresa"),
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
) -> Atual:
    """Resolve a empresa em foco.

    Sem o cabeçalho, usa a primeira da carteira — o caso de quem só tem um cliente.
    """
    visiveis = empresas_visiveis(db, sessao)
    if not visiveis:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta ainda não tem nenhum cliente liberado. Fale com o administrador.",
        )

    if x_empresa is None:
        empresa = visiveis[0]
    else:
        empresa = next((e for e in visiveis if e.id == x_empresa), None)
        if empresa is None:
            # 404 e não 403: quem não pode ver não descobre que o id existe
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")

    return Atual(
        usuario=sessao.usuario,
        organizacao=sessao.organizacao,
        empresa=empresa,
        schema=nome_schema(empresa.slug),
    )


def admin_atual(atual: Atual = Depends(usuario_atual)) -> Atual:
    if atual.usuario.papel != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só o administrador da organização pode fazer isso.",
        )
    return atual


def admin_sessao(sessao: Sessao = Depends(sessao_atual)) -> Sessao:
    """Para rotas que gerenciam a organização e não dependem de uma empresa em foco."""
    if sessao.usuario.papel != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só o administrador da organização pode fazer isso.",
        )
    return sessao
