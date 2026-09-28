"""Migra um banco do modelo antigo (usuário preso a uma empresa) para o modo agência.

Antes:  Usuario -> Empresa
Depois: Usuario -> Organizacao -> várias Empresas

Cada empresa existente vira uma organização do tipo "direta" com um cliente só,
preservando análises, schemas e logins. Ninguém perde acesso a nada.

Uso:
    python scripts/migrar_para_agencia.py            # mostra o que faria
    python scripts/migrar_para_agencia.py --aplicar  # executa
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import criar_schemas_base, engine  # noqa: E402
from app.security import gerar_slug  # noqa: E402


def coluna_existe(con, tabela: str, coluna: str) -> bool:
    return bool(
        con.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
            ),
            {"t": tabela, "c": coluna},
        ).first()
    )


def tabela_existe(con, tabela: str) -> bool:
    return bool(
        con.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=:t"),
            {"t": tabela},
        ).first()
    )


def main(aplicar: bool) -> int:
    with engine.connect() as con:
        if not tabela_existe(con, "empresas"):
            print("Banco vazio — nada a migrar. Suba a API que ela cria tudo.")
            return 0
        ja_migrado = coluna_existe(con, "empresas", "organizacao_id") and tabela_existe(con, "organizacoes")
        precisa = coluna_existe(con, "usuarios", "empresa_id")
        if ja_migrado and not precisa:
            print("Banco já está no modo agência. Nada a fazer.")
            return 0

        empresas = con.execute(text("SELECT id, nome, slug FROM public.empresas ORDER BY id")).fetchall()
        usuarios = con.execute(text("SELECT count(*) FROM public.usuarios")).scalar()

    print(f"Encontrei {len(empresas)} empresa(s) e {usuarios} usuário(s).")
    print("Cada empresa vira uma organização 'direta' com ela mesma na carteira:\n")
    for e in empresas:
        print(f"  • {e.nome}  ->  organização '{e.nome}' (cliente: {e.nome})")

    if not aplicar:
        print("\nNada foi alterado. Rode de novo com --aplicar para executar.")
        return 0

    # Cria as tabelas novas (organizacoes, acessos_empresa) sem tocar nas antigas
    criar_schemas_base()

    with engine.begin() as con:
        if not coluna_existe(con, "empresas", "organizacao_id"):
            con.execute(text("ALTER TABLE public.empresas ADD COLUMN organizacao_id INTEGER"))
        if not coluna_existe(con, "empresas", "segmento"):
            con.execute(text("ALTER TABLE public.empresas ADD COLUMN segmento VARCHAR(80)"))
        if not coluna_existe(con, "usuarios", "organizacao_id"):
            con.execute(text("ALTER TABLE public.usuarios ADD COLUMN organizacao_id INTEGER"))

        usados: set[str] = set()
        for e in empresas:
            base = gerar_slug(e.nome) or f"org_{e.id}"
            slug, n = base, 2
            while slug in usados or con.execute(
                text("SELECT 1 FROM public.organizacoes WHERE slug=:s"), {"s": slug}
            ).first():
                slug = f"{base[:36]}_{n}"
                n += 1
            usados.add(slug)

            org_id = con.execute(
                text(
                    "INSERT INTO public.organizacoes (nome, slug, tipo, plano, ativa) "
                    "VALUES (:nome, :slug, 'direta', 'basico', true) RETURNING id"
                ),
                {"nome": e.nome, "slug": slug},
            ).scalar()

            con.execute(
                text("UPDATE public.empresas SET organizacao_id=:o WHERE id=:e"), {"o": org_id, "e": e.id}
            )
            con.execute(
                text("UPDATE public.usuarios SET organizacao_id=:o WHERE empresa_id=:e"),
                {"o": org_id, "e": e.id},
            )
            print(f"  ✔ {e.nome}: organização {org_id}")

        orfaos = con.execute(text("SELECT count(*) FROM public.usuarios WHERE organizacao_id IS NULL")).scalar()
        if orfaos:
            raise RuntimeError(
                f"{orfaos} usuário(s) ficaram sem organização — migração abortada, nada foi gravado."
            )

        con.execute(text("ALTER TABLE public.empresas ALTER COLUMN organizacao_id SET NOT NULL"))
        con.execute(text("ALTER TABLE public.usuarios ALTER COLUMN organizacao_id SET NOT NULL"))
        con.execute(text("ALTER TABLE public.usuarios DROP COLUMN IF EXISTS empresa_id"))

    print("\n✔ Migração concluída. Análises e schemas ficaram como estavam.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--aplicar" in sys.argv))
