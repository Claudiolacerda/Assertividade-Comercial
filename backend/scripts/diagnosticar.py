"""Diz, em uma tela, por que o sistema não está funcionando.

Existe porque um 500 na tela de entrada não diz nada: pode ser banco fora do ar,
base vazia, tabela que falta, schema de cliente desalinhado ou simplesmente
nenhuma conta criada. Cada um desses tem uma causa e uma cura diferentes, e
caçá-las uma a uma custa várias idas e vindas.

Ele só lê. Não cria, não apaga, não migra. Rode da RAIZ do projeto:

    backend\\.venv\\Scripts\\python.exe backend\\scripts\\diagnosticar.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.engine.url import make_url  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import BasePublic, BaseTenant  # noqa: E402

OK, FALTA, AVISO = "  ok  ", "  --  ", "  !   "


def sem_schema(nomes) -> set[str]:
    """"public.usuarios" -> "usuarios".

    As chaves de `metadata.tables` vem qualificadas com o schema e o inspector
    devolve o nome puro. Comparar os dois direto acusava TODAS as tabelas como
    faltando, num banco que estava inteiro.
    """
    return {n.split(".")[-1] for n in nomes}


def main() -> int:
    url = make_url(settings.database_url)
    print()
    print("NERIAH - diagnostico")
    print("=" * 62)
    print(f"  ambiente   {settings.ambiente}")
    print(f"  banco      {url.host}:{url.port}/{url.database} (usuario {url.username})")
    print(f"  autocad.   {'ligado' if settings.permitir_autocadastro else 'desligado'}")
    print()

    # ---------------------------------------------------------- 1. conexao
    try:
        with engine.connect() as con:
            versao = con.execute(text("select version()")).scalar() or ""
        print(f"{OK}conexao com o Postgres ({versao.split(',')[0]})")
    except OperationalError as e:
        print(f"{FALTA}NAO CONSEGUI CONECTAR")
        print(f"      {str(e.orig).strip().splitlines()[0]}")
        print()
        print("  O que fazer, em ordem:")
        print("    1. docker start pg-assertividade")
        print("    2. espere uns segundos e rode de novo")
        print("    3. confira o DATABASE_URL em backend/.env")
        return 1

    insp = inspect(engine)

    # ------------------------------------------------- 2. tabelas globais
    esperadas = sem_schema(BasePublic.metadata.tables)
    existentes = set(insp.get_table_names(schema="public"))
    faltando = sorted(esperadas - existentes)
    if faltando:
        print(f"{FALTA}tabelas globais FALTANDO: {', '.join(faltando)}")
        print("      O banco esta vazio ou de uma versao anterior.")
        print("      Elas nascem quando voce cria a conta:")
        print('        backend\\.venv\\Scripts\\python.exe backend\\scripts\\criar_conta.py --help')
    else:
        print(f"{OK}tabelas globais presentes ({len(esperadas)})")

    # ------------------------------------------------------- 3. contas
    total_usuarios = None
    if "usuarios" in existentes:
        with engine.connect() as con:
            total_usuarios = con.execute(text("select count(*) from public.usuarios")).scalar()
            emails = [
                r[0] for r in con.execute(text("select email from public.usuarios order by id limit 5"))
            ]
        if total_usuarios:
            print(f"{OK}{total_usuarios} conta(s) cadastrada(s): {', '.join(emails)}")
        else:
            print(f"{AVISO}NENHUMA conta cadastrada — e por isso que o login falha")
            print("      Crie a sua com:")
            print('        backend\\.venv\\Scripts\\python.exe backend\\scripts\\criar_conta.py \\')
            print('          --organizacao "Sua Agencia" --nome "Claudio" --email voce@email.com \\')
            print('          --tipo agencia --cliente "Nome do Cliente"')

    # --------------------------------------------- 4. schemas de cliente
    with engine.connect() as con:
        schemas = [
            r[0]
            for r in con.execute(
                text(
                    "select schema_name from information_schema.schemata "
                    "where schema_name like 'tenant_%' order by 1"
                )
            )
        ]
    if not schemas:
        print(f"{AVISO}nenhum schema de cliente (normal se ainda nao criou conta)")
    else:
        esperadas_t = sem_schema(BaseTenant.metadata.tables)
        for schema in schemas:
            tem = set(insp.get_table_names(schema=schema))
            falta_t = sorted(esperadas_t - tem)
            if falta_t:
                print(f"{FALTA}{schema}: faltam as tabelas {', '.join(falta_t)}")
            else:
                with engine.connect() as con:
                    n = con.execute(text(f'select count(*) from "{schema}".analises')).scalar()
                print(f"{OK}{schema}: completo, {n} analise(s) gravada(s)")

    # ----------------------------------------- 5. colunas que divergiram
    # Modelo com coluna que a tabela nao tem e a causa classica de 500 num
    # banco antigo: a consulta cita a coluna e o Postgres recusa.
    divergencias = []
    for nome_tabela, tabela in BasePublic.metadata.tables.items():
        curto = nome_tabela.split(".")[-1]
        if curto not in existentes:
            continue
        no_banco = {c["name"] for c in insp.get_columns(curto, schema="public")}
        faltam = sorted({c.name for c in tabela.columns} - no_banco)
        if faltam:
            divergencias.append(f"public.{curto}: faltam {', '.join(faltam)}")
    for schema in schemas:
        tem = set(insp.get_table_names(schema=schema))
        for nome_tabela, tabela in BaseTenant.metadata.tables.items():
            curto = nome_tabela.split(".")[-1]
            if curto not in tem:
                continue
            no_banco = {c["name"] for c in insp.get_columns(curto, schema=schema)}
            faltam = sorted({c.name for c in tabela.columns} - no_banco)
            if faltam:
                divergencias.append(f"{schema}.{curto}: faltam {', '.join(faltam)}")

    if divergencias:
        print()
        print(f"{FALTA}COLUNAS QUE O CODIGO ESPERA E O BANCO NAO TEM:")
        for d in divergencias:
            print(f"      {d}")
        print()
        print("      E a causa classica de erro 500: a consulta cita a coluna e o")
        print("      Postgres recusa. O banco e de uma versao anterior do sistema.")
    else:
        print(f"{OK}nenhuma coluna divergente entre o codigo e o banco")

    print()
    print("=" * 62)
    if faltando or divergencias:
        print("  Ha trabalho a fazer: veja as linhas marcadas com --")
        return 1
    if not total_usuarios:
        print("  Banco saudavel. Falta so criar a conta.")
        return 0
    print("  Tudo certo por aqui. Se o login ainda falhar, o erro esta na")
    print("  janela da API — copie as ultimas linhas dela.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
