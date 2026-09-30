"""Cadastro, login e gestão de usuários da organização."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import criar_schema_empresa, get_db, nome_schema
from ..deps import Sessao, admin_sessao, empresas_visiveis, sessao_atual
from ..models import AcessoEmpresa, Empresa, Organizacao, Usuario
from ..schemas import (
    CadastroOrganizacao,
    EmpresaOut,
    Login,
    NovoUsuario,
    OrganizacaoOut,
    TokenOut,
    UsuarioOut,
)
from ..security import conferir_senha, criar_token, gerar_slug, hash_senha

router = APIRouter(prefix="/api/auth", tags=["autenticação"])


def _saida(db: Session, sessao: Sessao) -> UsuarioOut:
    return UsuarioOut(
        id=sessao.usuario.id,
        nome=sessao.usuario.nome,
        email=sessao.usuario.email,
        papel=sessao.usuario.papel,
        organizacao=OrganizacaoOut.model_validate(sessao.organizacao),
        empresas=[EmpresaOut.model_validate(e) for e in empresas_visiveis(db, sessao)],
    )


def _slug_livre(db: Session, base: str, modelo) -> str:
    """Slug único no banco inteiro — ele vira nome de schema, que é global."""
    slug, n = base, 2
    while db.scalar(select(modelo.id).where(modelo.slug == slug)):
        slug = f"{base[:36]}_{n}"
        n += 1
    return slug


def criar_empresa(
    db: Session,
    organizacao: Organizacao,
    nome: str,
    segmento: str | None = None,
    whatsapp: str | None = None,
) -> Empresa:
    """Cria o cliente e o schema dele. Usado no cadastro e ao adicionar à carteira."""
    slug = _slug_livre(db, gerar_slug(nome), Empresa)
    empresa = Empresa(
        organizacao_id=organizacao.id,
        nome=nome.strip(),
        slug=slug,
        schema_banco=nome_schema(slug),
        segmento=segmento,
        whatsapp=whatsapp,
    )
    db.add(empresa)
    db.flush()
    criar_schema_empresa(empresa.schema_banco)
    return empresa


@router.post("/cadastro", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: CadastroOrganizacao, db: Session = Depends(get_db)):
    """Cria a organização, o primeiro cliente da carteira e o usuário administrador."""
    if not settings.permitir_autocadastro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O autocadastro está desativado. Peça uma conta ao administrador.",
        )
    email = dados.email.lower().strip()
    if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este e-mail já tem conta.")

    organizacao = Organizacao(
        nome=dados.organizacao.strip(),
        slug=_slug_livre(db, gerar_slug(dados.organizacao), Organizacao),
        tipo=dados.tipo,
    )
    db.add(organizacao)
    db.flush()

    usuario = Usuario(
        organizacao_id=organizacao.id,
        email=email,
        nome=dados.nome.strip(),
        senha_hash=hash_senha(dados.senha),
        papel="admin",
    )
    db.add(usuario)
    db.flush()

    # Empresa direta analisa a si mesma; agência começa com o primeiro cliente.
    criar_empresa(db, organizacao, (dados.empresa or dados.organizacao).strip())
    db.commit()

    sessao = Sessao(usuario=usuario, organizacao=organizacao)
    return TokenOut(access_token=criar_token({"sub": str(usuario.id)}), usuario=_saida(db, sessao))


@router.post("/login", response_model=TokenOut)
def login(dados: Login, db: Session = Depends(get_db)):
    email = dados.email.lower().strip()
    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == email))
    # Mensagem única para e-mail inexistente e senha errada (não revela quem tem conta).
    if usuario is None or not conferir_senha(dados.senha, usuario.senha_hash) or not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos.")
    organizacao = db.get(Organizacao, usuario.organizacao_id)
    if organizacao is None or not organizacao.ativa:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organização inativa. Fale com o suporte.")
    usuario.ultimo_acesso = datetime.now(timezone.utc)
    db.commit()

    sessao = Sessao(usuario=usuario, organizacao=organizacao)
    return TokenOut(access_token=criar_token({"sub": str(usuario.id)}), usuario=_saida(db, sessao))


@router.get("/eu", response_model=UsuarioOut)
def eu(sessao: Sessao = Depends(sessao_atual), db: Session = Depends(get_db)):
    return _saida(db, sessao)


@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(sessao: Sessao = Depends(admin_sessao), db: Session = Depends(get_db)):
    usuarios = db.scalars(
        select(Usuario).where(Usuario.organizacao_id == sessao.organizacao.id).order_by(Usuario.nome)
    ).all()
    org = OrganizacaoOut.model_validate(sessao.organizacao)
    saida = []
    for u in usuarios:
        liberadas = empresas_visiveis(db, Sessao(usuario=u, organizacao=sessao.organizacao))
        saida.append(
            UsuarioOut(
                id=u.id, nome=u.nome, email=u.email, papel=u.papel, organizacao=org,
                empresas=[EmpresaOut.model_validate(e) for e in liberadas],
            )
        )
    return saida


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def criar_usuario(dados: NovoUsuario, sessao: Sessao = Depends(admin_sessao), db: Session = Depends(get_db)):
    """Adiciona um usuário à MESMA organização do admin — não há como criar em outra."""
    email = dados.email.lower().strip()
    if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este e-mail já tem conta.")
    if dados.papel == "cliente" and not dados.empresas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuário do tipo cliente precisa de pelo menos um cliente liberado.",
        )

    usuario = Usuario(
        organizacao_id=sessao.organizacao.id,
        email=email,
        nome=dados.nome.strip(),
        senha_hash=hash_senha(dados.senha),
        papel=dados.papel,
    )
    db.add(usuario)
    db.flush()

    if dados.papel == "cliente":
        # Só aceita empresas da própria organização.
        da_org = set(
            db.scalars(
                select(Empresa.id).where(
                    Empresa.organizacao_id == sessao.organizacao.id, Empresa.id.in_(dados.empresas)
                )
            ).all()
        )
        invalidas = set(dados.empresas) - da_org
        if invalidas:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
        for eid in da_org:
            db.add(AcessoEmpresa(usuario_id=usuario.id, empresa_id=eid))
    db.commit()

    return UsuarioOut(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        papel=usuario.papel,
        organizacao=OrganizacaoOut.model_validate(sessao.organizacao),
        empresas=[
            EmpresaOut.model_validate(e)
            for e in empresas_visiveis(db, Sessao(usuario=usuario, organizacao=sessao.organizacao))
        ],
    )
