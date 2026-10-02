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


def ler_metas_da_planilha(caminhos) -> dict[str, float]:
    """Lê a aba 'Metas' da planilha de reuniões, se ela existir.

    A aba é opcional, e tem de ser: planilha antiga, CSV e export de outro
    sistema nenhum tem essa aba, e todos continuam analisando igual. Linha
    vazia ou valor não numérico é ignorado em silêncio — meta em branco é um
    estado previsto, que o JET trata tirando o indicador do Score.

    O casamento é pelo rótulo normalizado da coluna A, contra a mesma lista
    que a planilha-modelo escreve. Por isso os dois lados importam de
    `modelo.METAS_DA_PLANILHA`: mudar um rótulo lá muda os dois juntos.
    """
    from .modelo import ABA_METAS, METAS_DA_PLANILHA

    por_rotulo = {normalizar(rot): (chave, fmt) for chave, rot, fmt, _, _ in METAS_DA_PLANILHA}
    achadas: dict[str, float] = {}

    for caminho in caminhos if isinstance(caminhos, (list, tuple)) else [caminhos]:
        caminho = Path(caminho)
        if caminho.suffix.lower() not in (".xlsx", ".xlsm", ".xls"):
            continue
        try:
            abas = pd.read_excel(caminho, sheet_name=None, header=None, dtype=object)
        except Exception:
            continue
        nome_aba = next((n for n in abas if normalizar(n) == normalizar(ABA_METAS)), None)
        if nome_aba is None:
            continue
        for _, linha in abas[nome_aba].iterrows():
            valores = list(linha)
            if len(valores) < 2:
                continue
            alvo = por_rotulo.get(normalizar(valores[0]))
            if not alvo:
                continue
            chave, formato = alvo
            numero = _para_numero_meta(valores[1])
            if numero is None:
                continue
            if numero <= 0:
                continue
            # O Excel guarda porcentagem como fração (25% = 0,25), mas quem
            # digita "25" numa célula sem formato quer 25%. Acima de 1 numa
            # meta percentual só pode ser a segunda leitura.
            if formato == "pct" and numero > 1:
                numero = numero / 100
            achadas[chave] = numero
    return achadas


def _para_numero_meta(valor) -> float | None:
    """Converte a célula de meta em número, aceitando o que o Excel e o humano dão.

    O Excel entrega float ou int, e esses passam direto: tratá-los como texto
    e aplicar a limpeza de separadores quebraria 0,25 em 25. Só quando a célula
    é texto é que vale remover "R$", "%" e o ponto de milhar.
    """
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return None if pd.isna(valor) else float(valor)
    texto = str(valor).strip()
    if not texto:
        return None
    texto = texto.replace("R$", "").replace("%", "").replace("x", "").strip()
    # "1.234,56" é milhar + decimal; "1234.56" é só decimal. A vírgula decide.
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None
