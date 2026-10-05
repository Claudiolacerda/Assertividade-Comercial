"""Converte as colunas de resultado de JSONB para JSON em todos os schemas.

Por que: o JSONB normaliza o objeto e reordena as chaves por tamanho. A ordem
das chaves de cada linha é a ordem das colunas da tabela — na tela e no Excel.
Com JSONB, "Clientes" aparecia antes de "Sinal na observação" só por ser mais
curto, e o usuário lia o número antes de saber do que ele era.

Idempotente: pode rodar quantas vezes quiser.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402

COLUNAS = ("resultado", "kpis_resumo", "config_usada")


def main() -> None:
    with engine.begin() as con:
        schemas = [
            r[0]
            for r in con.execute(
                text(
                    "select schema_name from information_schema.schemata "
                    "where schema_name like 'tenant_%'"
                )
            )
        ]
        if not schemas:
            print("Nenhum schema de cliente encontrado.")
            return

        total = 0
        for schema in schemas:
            for coluna in COLUNAS:
                tipo = con.execute(
                    text(
                        "select data_type from information_schema.columns "
                        "where table_schema = :s and table_name = 'analises' "
                        "and column_name = :c"
                    ),
                    {"s": schema, "c": coluna},
                ).scalar()
                if tipo is None:
                    continue
                if tipo == "json":
                    continue
                con.execute(
                    text(
                        f'alter table "{schema}".analises '
                        f'alter column {coluna} type json using {coluna}::text::json'
                    )
                )
                print(f"  {schema}.analises.{coluna}: {tipo} -> json")
                total += 1

        print(
            f"\n{total} coluna(s) convertida(s) em {len(schemas)} schema(s)."
            if total
            else f"\nNada a fazer: {len(schemas)} schema(s) já estão em json."
        )
        print(
            "\nAtenção: análises gravadas ANTES desta migração continuam com a "
            "ordem embaralhada, porque a ordem original se perdeu na gravação. "
            "Refaça a análise do mês para que ela saia na ordem certa."
        )


if __name__ == "__main__":
    # Falha de conexão aqui saía como traceback cru do SQLAlchemy, e o que a
    # pessoa via era "Traceback (most recent call last)" sem nenhuma pista de
    # que o problema era o banco não estar no ar ou o DATABASE_URL apontar para
    # o lugar errado. O traceback continua disponível com --debug.
    try:
        main()
    except OperationalError as e:
        from sqlalchemy.engine.url import make_url

        url = make_url(settings.database_url)
        print(
            f"Não consegui falar com o banco em {url.host}:{url.port}, "
            f"base '{url.database}', usuário '{url.username}'.\n"
            "\nAs causas prováveis, em ordem:\n"
            "  1. O Postgres ainda está subindo. Espere uns segundos e rode de novo.\n"
            "  2. O contêiner não está no ar:  docker start pg-assertividade\n"
            "  3. O DATABASE_URL do backend/.env aponta para outro lugar.\n"
            f"\nO que o driver respondeu: {str(e.orig).strip().splitlines()[0]}",
            file=sys.stderr,
        )
        if "--debug" in sys.argv:
            raise
        sys.exit(1)
