"""Os scripts .ps1 têm de ser ASCII puro.

O Windows PowerShell 5.1, que é o que vem no Windows, lê um arquivo .ps1 sem
BOM como Windows-1252, não UTF-8. Um travessão escrito em UTF-8 são os bytes
E2 80 94, e em Windows-1252 esses três bytes são lidos como `â€"`. A terceira
letra é uma aspa dupla, e ela FECHA a string ali no meio: o resto da linha vira
código solto e o resto do arquivo vira lixo.

Foi o que aconteceu com o configurar.ps1 na primeira vez que ele rodou de
verdade: a instalação parou no meio, o npm install não executou, e o terminal
imprimiu o código-fonte do script em vez de executá-lo. O sintoma não aponta
para a causa, e por isso este teste existe.

ASCII puro é idêntico nas duas codificações, então resolve sem depender de BOM
nem de qual PowerShell a pessoa tem. O preço é escrever "instalacao" em vez de
"instalação" dentro dos scripts, e é um preço baixo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SCRIPTS = sorted(RAIZ.glob("*.ps1"))


def test_existe_pelo_menos_um_script():
    """Se alguém mover os .ps1, o teste abaixo passaria vazio sem avisar."""
    assert SCRIPTS, "nenhum .ps1 na raiz: o teste de ASCII não estaria cobrindo nada"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_o_script_e_ascii_puro(script: Path):
    dados = script.read_bytes()
    problemas = []
    for linha_n, linha in enumerate(dados.split(b"\n"), 1):
        for coluna, byte in enumerate(linha, 1):
            if byte > 127:
                trecho = linha.decode("utf-8", "replace")[max(0, coluna - 25):coluna + 15]
                problemas.append(f"linha {linha_n}, coluna {coluna}: ...{trecho}...")
    assert not problemas, (
        f"{script.name} tem {len(problemas)} byte(s) nao-ASCII. O PowerShell 5.1 le o "
        f"arquivo como Windows-1252 e o travessao vira uma aspa que fecha a string.\n"
        + "\n".join(problemas[:5])
    )


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_a_crase_de_continuacao_termina_a_linha(script: Path):
    """No PowerShell a crase de continuação tem de ser o último caractere.

    Um comentário depois dela é erro de sintaxe, e eu já escrevi um.
    """
    for n, linha in enumerate(script.read_text(encoding="ascii").splitlines(), 1):
        sem_comentario = linha.split("#")[0] if linha.lstrip().startswith("#") else linha
        if "` " in sem_comentario and sem_comentario.rstrip().endswith("`") is False:
            # crase seguida de espaço no meio da linha só é válida dentro de string
            if sem_comentario.count('"') % 2 == 0 and "`n" not in sem_comentario:
                pytest.fail(f"{script.name} linha {n}: crase de continuacao nao termina a linha:\n  {linha}")
