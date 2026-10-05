"""O .env tem de ser achado a partir do código, não do diretório atual.

Com o caminho relativo ".env", o pydantic procurava no diretório de onde o
processo foi lançado. O uvicorn sobe de dentro de backend/ e achava; qualquer
script rodado da raiz do projeto não achava e caía nos valores padrão, em
silêncio. O diagnóstico chegou a relatar um banco que ninguém tinha
configurado, e a mentira parecia defeito do banco.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from app.config import ARQUIVO_ENV

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"


def test_o_caminho_do_env_e_absoluto_e_fica_no_backend():
    assert ARQUIVO_ENV.is_absolute(), "caminho relativo depende de onde o processo foi lançado"
    assert ARQUIVO_ENV.parent == BACKEND
    assert ARQUIVO_ENV.name == ".env"


def test_a_configuracao_e_a_mesma_de_qualquer_diretorio(tmp_path):
    """Lê a config de três lugares diferentes e exige o mesmo resultado."""
    codigo = (
        f"import sys; sys.path.insert(0, {str(BACKEND)!r});"
        "from app.config import settings; print(settings.database_url)"
    )
    lidos = {}
    for lugar in [RAIZ, BACKEND, tmp_path]:
        saida = subprocess.run(
            [sys.executable, "-c", codigo], cwd=lugar, capture_output=True, text=True, check=True
        )
        lidos[str(lugar)] = saida.stdout.strip()
    assert len(set(lidos.values())) == 1, f"a config mudou com o diretório: {lidos}"


def test_a_troca_do_banco_no_configurar_ps1_sobrevive_a_quebra_de_linha_do_windows():
    """A expressão não pode terminar em `$`.

    No Windows o arquivo tem quebra de linha CRLF, e o \\r fica entre o texto e
    o fim da linha: com `$` ancorado a troca nunca casa. O .env saía apontando
    para um servidor chamado "host", que não existe, e o sintoma aparecia três
    passos adiante como erro 500 na tela de entrada.
    """
    script = (RAIZ / "configurar.ps1").read_text(encoding="ascii")
    linha = next(l for l in script.splitlines() if "usuario:senha@host" in l and "-replace" in l)
    padrao = linha.split("'")[1]
    assert not padrao.endswith("$"), f"a âncora `$` quebra em CRLF: {padrao}"

    # e a troca tem de funcionar de verdade num texto com CRLF
    exemplo = (RAIZ / "backend" / ".env.example").read_text(encoding="utf-8").replace("\n", "\r\n")
    assert re.search(padrao, exemplo), "a expressão não casa com o .env.example em CRLF"
    # sem pegar a linha local, que está comentada logo acima
    assert len(re.findall(padrao, exemplo)) == 1


def test_o_configurar_ps1_confere_o_env_depois_de_escrever():
    """Escrever e não conferir foi o que deixou o defeito passar."""
    script = (RAIZ / "configurar.ps1").read_text(encoding="ascii")
    assert "localhost:5432/assertividade" in script
    assert "o .env saiu com o banco errado" in script
