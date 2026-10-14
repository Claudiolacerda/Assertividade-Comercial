"""`npm run dev` tem de funcionar da raiz do projeto.

O `package.json` mora em `frontend/`, e por quatro vezes nesta instalação o
comando foi digitado na raiz e respondeu com um ENOENT que não ensina nada:

    npm error code ENOENT
    npm error path C:\\...\\sistema_assertividade\\package.json

A raiz tem um `package.json` só de atalhos para encerrar isso. Os testes aqui
guardam as duas maneiras de ele apodrecer em silêncio:

1. um atalho apontando para um script que não existe mais em frontend/ — o
   comando passa a falhar DEPOIS de entrar na pasta, o que é pior que antes;
2. alguém trocar `cd frontend && ...` por `npm --prefix frontend ...`, que é o
   que parece certo e não é: na máquina deste usuário o `--prefix` procurou o
   package.json na pasta ACIMA e falhou. O `cd` funciona igual no cmd.exe (que
   é o shell que o npm usa no Windows) e no shell do Linux.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ATALHOS = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))
SITE = json.loads((RAIZ / "frontend" / "package.json").read_text(encoding="utf-8"))

ESSENCIAIS = ["dev", "build", "typecheck"]


def test_a_raiz_tem_os_atalhos_essenciais():
    for nome in ESSENCIAIS:
        assert nome in ATALHOS["scripts"], f"'npm run {nome}' não funciona da raiz"


@pytest.mark.parametrize("nome", sorted(ATALHOS["scripts"]))
def test_todo_atalho_aponta_para_um_script_que_existe(nome: str):
    """Atalho para script inexistente falha depois do `cd`: pior que o ENOENT."""
    comando = ATALHOS["scripts"][nome]
    if "npm run " not in comando:
        return  # install:site chama `npm install`, que não é script do site
    alvo = comando.split("npm run ")[1].strip()
    assert alvo in SITE["scripts"], f"o atalho '{nome}' chama 'npm run {alvo}', que frontend/ não tem"


@pytest.mark.parametrize("nome", sorted(ATALHOS["scripts"]))
def test_nenhum_atalho_usa_prefix(nome: str):
    """`npm --prefix` parece a forma certa e falhou na máquina do usuário."""
    assert "--prefix" not in ATALHOS["scripts"][nome], (
        "use `cd frontend && ...`: o --prefix procurou o package.json na pasta de cima"
    )


def test_a_raiz_nao_vira_um_segundo_projeto_de_verdade():
    """Sem dependências aqui: duas árvores de node_modules é confusão garantida."""
    assert "dependencies" not in ATALHOS and "devDependencies" not in ATALHOS
    assert ATALHOS.get("private") is True
