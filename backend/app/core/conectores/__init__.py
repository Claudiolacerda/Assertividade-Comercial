"""Conectores de CRM: trazem os negócios por API e escrevem a planilha de sempre."""

from __future__ import annotations

import csv
from pathlib import Path

from .base import (
    COLUNAS_SAIDA,
    Conector,
    Credencial,
    ErroDeConexao,
    Importacao,
    Periodo,
)
from .generico import ConectorGenerico
from .pipedrive import ConectorPipedrive

CONECTORES: dict[str, type[Conector]] = {
    c.nome: c for c in (ConectorPipedrive, ConectorGenerico)
}


def montar(provedor: str, credencial: Credencial, config: dict | None = None) -> Conector:
    try:
        classe = CONECTORES[provedor]
    except KeyError:
        raise ErroDeConexao(
            f"Não conheço o CRM {provedor!r}. Os disponíveis são: "
            + ", ".join(sorted(CONECTORES))
            + "."
        ) from None
    return classe(credencial, config)


def escrever_csv(importacao: Importacao, destino: Path) -> Path:
    """Grava o que veio do CRM como a planilha que o Neriah já sabe ler.

    UTF-8 com BOM: é o que faz o Excel no Windows abrir acento corretamente, e
    este arquivo existe justamente para a pessoa poder abrir e conferir.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS_SAIDA, extrasaction="ignore")
        escritor.writeheader()
        for linha in importacao.linhas:
            escritor.writerow({c: linha.get(c) for c in COLUNAS_SAIDA})
    return destino


__all__ = [
    "COLUNAS_SAIDA",
    "CONECTORES",
    "Conector",
    "ConectorGenerico",
    "ConectorPipedrive",
    "Credencial",
    "ErroDeConexao",
    "Importacao",
    "Periodo",
    "escrever_csv",
    "montar",
]
