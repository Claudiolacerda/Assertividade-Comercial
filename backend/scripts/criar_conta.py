"""Cria uma conta pela linha de comando.

Em produção o autocadastro fica desligado — é você quem abre as contas. Sem este
script não haveria como entrar no sistema recém-instalado, porque a tela de
cadastro responde 403.

Uso:
    python scripts/criar_conta.py --organizacao "Agência Ponto Verde" \
        --nome "Cláudio" --email claudio@agencia.com.br --tipo agencia \
        --cliente "Contabilidade Horizonte"

A senha é pedida no terminal, sem eco. Se omitida, o script gera uma e mostra.
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import criar_schemas_base, sessao_publica  # noqa: E402
from app.models import Organizacao, Usuario  # noqa: E402
from app.routers.auth import _slug_livre, criar_empresa  # noqa: E402
from app.security import gerar_slug, hash_senha  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Cria organização e usuário administrador.")
    p.add_argument("--organizacao", required=True, help="Nome da agência ou da empresa")
    p.add_argument("--nome", required=True, help="Nome da pessoa que vai administrar")
    p.add_argument("--email", required=True)
    p.add_argument("--tipo", choices=["agencia", "direta"], default="direta")
    p.add_argument("--cliente", help="Primeiro cliente da carteira (padrão: o nome da organização)")
    p.add_argument("--senha", help="Se omitida, é pedida no terminal ou gerada")
    args = p.parse_args()

    email = args.email.lower().strip()
    if "@" not in email:
        print("E-mail inválido.", file=sys.stderr)
        return 1

    senha = args.senha
    gerada = False
    if not senha:
        if sys.stdin.isatty():
            senha = getpass.getpass("Senha (mínimo 8, letras e números): ")
            if senha != getpass.getpass("Confirme a senha: "):
                print("As senhas não conferem.", file=sys.stderr)
                return 1
        else:
            senha = secrets.token_urlsafe(9) + "7a"
            gerada = True
    if len(senha) < 8 or senha.isdigit() or senha.isalpha():
        print("Senha fraca: mínimo 8 caracteres, misturando letras e números.", file=sys.stderr)
        return 1

    try:
        criar_schemas_base()
    except OperationalError:
        # Sem isto o operador recebe 60 linhas de traceback quando o banco ainda
        # não subiu — que é o erro mais provável logo depois do deploy.
        print(
            "Não consegui falar com o banco. Confira se ele está no ar e se DATABASE_URL "
            "aponta para ele.\nNo Docker: docker compose up -d banco",
            file=sys.stderr,
        )
        return 2

    with sessao_publica() as db:
        if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == email)):
            print(f"Já existe conta com o e-mail {email}.", file=sys.stderr)
            return 1

        organizacao = Organizacao(
            nome=args.organizacao.strip(),
            slug=_slug_livre(db, gerar_slug(args.organizacao), Organizacao),
            tipo=args.tipo,
        )
        db.add(organizacao)
        db.flush()

        usuario = Usuario(
            organizacao_id=organizacao.id,
            email=email,
            nome=args.nome.strip(),
            senha_hash=hash_senha(senha),
            papel="admin",
        )
        db.add(usuario)
        db.flush()

        empresa = criar_empresa(db, organizacao, (args.cliente or args.organizacao).strip())

    print(f"✔ Organização '{organizacao.nome}' ({args.tipo}) criada")
    print(f"✔ Cliente '{empresa.nome}' criado — schema {empresa.schema_banco}")
    print(f"✔ Administrador: {email}")
    if gerada:
        print(f"\n  SENHA GERADA: {senha}")
        print("  Anote agora: ela não será mostrada de novo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
