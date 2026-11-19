"""Cria, nos schemas de cliente que já existem, as tabelas que o código passou a usar.

Por que existe: o schema de uma empresa é criado uma única vez, quando a conta
nasce. Toda tabela acrescentada depois — `conexoes_crm` é a primeira — não
aparece sozinha nos clientes antigos, e a consulta que a cita devolve 500. O
`diagnosticar.py` sabe apontar o problema; este script resolve.

Só CRIA o que falta. Não altera, não apaga e não mexe em dado nenhum, então
pode rodar quantas vezes quiser. Rode da pasta backend:

    .venv\\Scripts\\python.exe scripts\\migrar_tabelas_novas.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.db import engine
from app.models import BaseTenant


def main() -> int:
    try:
        with engine.begin() as con:
            schemas = [
                r[0]
                for r in con.execute(
                    text(
                        "select schema_name from information_schema.schemata "
                        "where schema_name like 'tenant_%' order by 1"
                    )
                )
            ]
    except OperationalError as e:
        print(f"Não consegui conectar ao banco: {str(e.orig).strip().splitlines()[0]}")
        return 1

    if not schemas:
        print("Nenhum schema de cliente. Nada a fazer.")
        return 0

    esperadas = {n.split(".")[-1]: t for n, t in BaseTenant.metadata.tables.items()}
    criadas_total = 0
    for schema in schemas:
        motor = engine.execution_options(schema_translate_map={"tenant": schema})
        existentes = set(inspect(engine).get_table_names(schema=schema))
        faltando = [t for nome, t in esperadas.items() if nome not in existentes]
        if not faltando:
            print(f"  {schema}: completo")
            continue
        # `checkfirst` protege contra corrida; `tables=` evita tocar no resto.
        BaseTenant.metadata.create_all(motor, tables=faltando, checkfirst=True)
        nomes = ", ".join(sorted(t.name for t in faltando))
        print(f"  {schema}: criei {nomes}")
        criadas_total += len(faltando)

    print()
    print(f"Pronto. {criadas_total} tabela(s) criada(s) em {len(schemas)} schema(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
