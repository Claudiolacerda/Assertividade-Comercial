"""Cadastro, login e gestão de usuários da empresa."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import criar_schema_empresa, get_db, nome_schema
from ..deps import Atual, admin_atual, usuario_atual
from ..models import Empresa, Usuario
from ..schemas import CadastroEmpresa, EmpresaOut, Login, NovoUsuario, TokenOut, UsuarioOut
from ..security import conferir_senha, criar_token, gerar_slug, hash_senha

router = APIRouter(prefix="/api/auth", tags=["autenticação"])


def _token_de(usuario: Usuario, empresa: Empresa) -> TokenOut:
    token = criar_token({"sub": str(usuario.id), "empresa": empresa.slug})
    return TokenOut(
        access_token=token,
        usuario=UsuarioOut(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            papel=usuario.papel,
            empresa=EmpresaOut.model_validate(empresa),
        ),
    )


def _slug_livre(db: Session, base: str) -> str:
    slug, n = base, 2
    while db.scalar(select(Empresa.id).where(Empresa.slug == slug)):
        slug = f"{base[:36]}_{n}"
        n += 1
    return slug


@router.post("/cadastro", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: CadastroEmpresa, db: Session = Depends(get_db)):
    """Cria a empresa, o schema dela no banco e o primeiro usuário (admin)."""
    if not settings.permitir_autocadastro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O autocadastro está desativado. Peça uma conta ao administrador.",
        )
    email = dados.email.lower().strip()
    if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este e-mail já tem conta.")

    slug = _slug_livre(db, gerar_slug(dados.empresa))
    empresa = Empresa(nome=dados.empresa.strip(), slug=slug, schema_banco=nome_schema(slug))
    db.add(empresa)
    db.flush()

    usuario = Usuario(
        empresa_id=empresa.id,
        email=email,
        nome=dados.nome.strip(),
        senha_hash=hash_senha(dados.senha),
        papel="admin",
    )
    db.add(usuario)
    db.flush()
    # O schema só é criado depois que empresa e usuário passaram na validação.
    criar_schema_empresa(empresa.schema_banco)
    db.commit()
    return _token_de(usuario, empresa)


@router.post("/login", response_model=TokenOut)
def login(dados: Login, db: Session = Depends(get_db)):
    email = dados.email.lower().strip()
    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == email))
    # Mensagem única para e-mail inexistente e senha errada (não revela quem tem conta).
    if usuario is None or not conferir_senha(dados.senha, usuario.senha_hash) or not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos.")
    empresa = db.get(Empresa, usuario.empresa_id)
    if empresa is None or not empresa.ativa:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa inativa. Fale com o suporte.")
    usuario.ultimo_acesso = datetime.now(timezone.utc)
    db.commit()
    return _token_de(usuario, empresa)


@router.get("/eu", response_model=UsuarioOut)
def eu(atual: Atual = Depends(usuario_atual)):
    return UsuarioOut(
        id=atual.usuario.id,
        nome=atual.usuario.nome,
        email=atual.usuario.email,
        papel=atual.usuario.papel,
        empresa=EmpresaOut.model_validate(atual.empresa),
    )


@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(atual: Atual = Depends(admin_atual), db: Session = Depends(get_db)):
    usuarios = db.scalars(
        select(Usuario).where(Usuario.empresa_id == atual.empresa.id).order_by(Usuario.nome)
    ).all()
    empresa = EmpresaOut.model_validate(atual.empresa)
    return [
        UsuarioOut(id=u.id, nome=u.nome, email=u.email, papel=u.papel, empresa=empresa) for u in usuarios
    ]


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def criar_usuario(dados: NovoUsuario, atual: Atual = Depends(admin_atual), db: Session = Depends(get_db)):
    """Adiciona um usuário à MESMA empresa do admin — não há como criar em outra."""
    email = dados.email.lower().strip()
    if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este e-mail já tem conta.")
    usuario = Usuario(
        empresa_id=atual.empresa.id,
        email=email,
        nome=dados.nome.strip(),
        senha_hash=hash_senha(dados.senha),
        papel=dados.papel,
    )
    db.add(usuario)
    db.commit()
    return UsuarioOut(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        papel=usuario.papel,
        empresa=EmpresaOut.model_validate(atual.empresa),
    )
