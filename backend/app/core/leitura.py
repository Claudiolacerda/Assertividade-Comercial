"""Leitura de arquivos "como o cliente manda".

Acha o cabeçalho real dentro do arquivo (inclusive painéis em blocos
"Semana 1 / Semana 2"), reconhece as colunas por apelido e descarta
arquivos duplicados para não contar investimento em dobro.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd

from .texto import normalizar


def ler_bruto(caminho: str | Path) -> pd.DataFrame:
    """Lê o arquivo SEM assumir que a 1ª linha é o cabeçalho (tudo como texto)."""
    caminho = Path(caminho)
    if caminho.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(caminho, header=None, dtype=object)
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(
                caminho,
                sep=None,
                engine="python",
                encoding=enc,
                header=None,
                dtype=str,
                skip_blank_lines=False,
                keep_default_na=False,
                na_values=[""],
            )
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não consegui ler {caminho.name}")


def eh_vazia(linha) -> bool:
    return all(pd.isna(v) or str(v).strip() == "" for v in linha)


def montar_tabela(bruto: pd.DataFrame, apelidos_obrigatorios) -> tuple[pd.DataFrame | None, bool]:
    """Encontra o(s) cabeçalho(s) dentro do arquivo e monta uma tabela única.

    - Tabela simples: cabeçalho na 1ª linha.
    - Painel em blocos (Semana 1, Semana 2...): cada bloco tem seu cabeçalho; lê até a
      próxima linha vazia e guarda de qual semana veio a linha. Totais e legendas
      abaixo dos blocos são ignorados.
    """
    alvos = [[normalizar(a) for a in grupo] for grupo in apelidos_obrigatorios]

    def eh_cabecalho(linha) -> bool:
        cels = [normalizar(v) for v in linha if pd.notna(v)]
        return all(any(c == a or c.startswith(a) for c in cels for a in grupo) for grupo in alvos)

    linhas = bruto.values.tolist()
    cabecalhos = [i for i, l in enumerate(linhas) if eh_cabecalho(l)]
    if not cabecalhos:
        return None, False
    partes = []
    for i in cabecalhos:
        nomes = [
            str(v).strip() if pd.notna(v) and str(v).strip() else f"coluna_{j + 1}"
            for j, v in enumerate(linhas[i])
        ]
        semana = None
        for k in range(i - 1, max(i - 4, -1), -1):  # título do bloco logo acima do cabeçalho
            t = str(linhas[k][0]).strip() if pd.notna(linhas[k][0]) else ""
            if re.match(r"(?i)^semana\s*\d+", t):
                semana = t
                break
        dados = []
        for l in linhas[i + 1:]:
            if eh_vazia(l) or eh_cabecalho(l):
                break
            dados.append(l)
        bloco = pd.DataFrame(dados, columns=nomes)
        bloco["semana_planilha"] = semana
        partes.append(bloco)
    em_blocos = len(cabecalhos) > 1 or cabecalhos[0] > 0
    return pd.concat(partes, ignore_index=True), em_blocos


def ler_arquivos(
    arquivos: list[str | Path],
    extensoes: set[str],
    apelidos_obrigatorios,
    avisos: list[str],
) -> tuple[pd.DataFrame, bool]:
    """Lê vários arquivos enviados e empilha num único DataFrame.

    Equivale ao `ler_pasta` do notebook, mas recebe a lista de arquivos (é o que
    a API tem em mãos depois do upload) e acumula avisos em vez de imprimir.
    """
    arquivos = [Path(a) for a in arquivos]
    validos = sorted(a for a in arquivos if a.suffix.lower() in extensoes and not a.name.startswith("~$"))
    if not validos:
        raise FileNotFoundError(f"Nenhum arquivo {sorted(extensoes)} entre os enviados.")
    partes: list[pd.DataFrame] = []
    vistos: dict[str, str] = {}
    em_blocos = False
    for arq in validos:
        h = hashlib.md5(arq.read_bytes()).hexdigest()
        if h in vistos:
            avisos.append(
                f"Arquivo '{arq.name}' é idêntico a '{vistos[h]}' e foi ignorado "
                "(evita contar investimento/reuniões em dobro)."
            )
            continue
        vistos[h] = arq.name
        df, blocos = montar_tabela(ler_bruto(arq), apelidos_obrigatorios)
        if df is None:
            avisos.append(f"Arquivo '{arq.name}' ignorado: nenhum cabeçalho reconhecido.")
            continue
        em_blocos |= blocos
        df["arquivo_origem"] = arq.name
        partes.append(df)
    if not partes:
        raise ValueError(
            "Nenhum arquivo válido: não encontrei as colunas obrigatórias em nenhum dos arquivos enviados."
        )
    return pd.concat(partes, ignore_index=True), em_blocos


def encontrar_coluna(df: pd.DataFrame, apelidos: list[str]) -> str | None:
    cols = {normalizar(c): c for c in df.columns}
    for a in apelidos:  # 1º: nome exato
        if normalizar(a) in cols:
            return cols[normalizar(a)]
    for a in apelidos:  # 2º: começa com o apelido
        for nc, c in cols.items():
            if nc.startswith(normalizar(a)):
                return c
    return None


def padronizar(df: pd.DataFrame, mapa: dict[str, list[str]], nome_base: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Renomeia as colunas do cliente para os campos internos e devolve o log do mapeamento."""
    novo, log = pd.DataFrame(index=df.index), []
    usadas: set[str] = set()
    for padrao, apelidos in mapa.items():
        col = encontrar_coluna(df.drop(columns=list(usadas), errors="ignore"), apelidos)
        if col is not None:
            novo[padrao] = df[col]
            usadas.add(col)
        log.append(
            {
                "Base": nome_base,
                "Campo do sistema": padrao,
                "Coluna encontrada no arquivo": col if col else "— NÃO ENCONTRADA —",
            }
        )
    extras = [c for c in df.columns if c not in usadas and c not in ("arquivo_origem", "semana_planilha")]
    for c in extras:
        log.append({"Base": nome_base, "Campo do sistema": "(não usada)", "Coluna encontrada no arquivo": c})
    for c in ["arquivo_origem", "semana_planilha"]:
        if c in df:
            novo[c] = df[c]
    return novo, pd.DataFrame(log)
