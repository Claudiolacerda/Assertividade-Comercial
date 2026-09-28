"""Motor de métricas.

Cada taxa é definida uma única vez (numerador ÷ denominador). A mesma definição
calcula o número na API e escreve a fórmula viva no Excel — é o que garante que
o gráfico da tela e a planilha exportada nunca divirjam.
"""

from __future__ import annotations

import pandas as pd

from .config_analise import STATUS_REALIZADA
from .texto import div

TAXAS_COMERCIAIS = [
    {"nome": "Comparecimento (%)", "num": ["Reuniões realizadas"], "den": ["Reuniões realizadas", "No-show"]},
    {
        "nome": "Agendamento → realização (%)",
        "num": ["Reuniões realizadas"],
        "den": ["Reuniões realizadas", "No-show", "Remarcadas", "Canceladas"],
    },
    {
        "nome": "Assertividade - fechamento s/ realizadas (%)",
        "num": ["Fechados"],
        "den": ["Reuniões realizadas"],
    },
    {"nome": "Win rate - fechados s/ decididas (%)", "num": ["Fechados"], "den": ["Fechados", "Perdidos"]},
    {"nome": "Fechamento s/ agendadas (%)", "num": ["Fechados"], "den": ["Reuniões agendadas"]},
    {"nome": "Taxa de perda (%)", "num": ["Perdidos"], "den": ["Reuniões realizadas"]},
    {"nome": "Ainda em negociação (%)", "num": ["Em negociação"], "den": ["Reuniões realizadas"]},
    {"nome": "Sem desfecho registrado (%)", "num": ["Reunião feita sem desfecho"], "den": ["Reuniões realizadas"]},
    {"nome": "No-show (%)", "num": ["No-show"], "den": ["Reuniões agendadas"]},
    {"nome": "Ticket médio (R$)", "num": ["Receita fechada (R$)"], "den": ["Fechados"]},
    {"nome": "Participação na receita (%)", "num": ["Receita fechada (R$)"], "den": "__TOTAL__"},
]

TAXAS_META = [
    {"nome": "% do investimento (%)", "num": ["Investimento (R$)"], "den": "__TOTAL__"},
    {"nome": "CTR no link (%)", "num": ["Cliques no link"], "den": ["Impressões"]},
    {"nome": "CPC (R$)", "num": ["Investimento (R$)"], "den": ["Cliques no link"]},
    {"nome": "CPM (R$)", "num": ["Investimento (R$)"], "den": ["Impressões"], "mult": 1000},
    {"nome": "Frequência (x)", "num": ["Impressões"], "den": ["Alcance"]},
    {"nome": "Clique → lead (%)", "num": ["Leads / resultados"], "den": ["Cliques no link"]},
    {"nome": "Custo por lead (R$)", "num": ["Investimento (R$)"], "den": ["Leads / resultados"]},
]

TAXAS_CRUZADAS = [
    {"nome": "Custo por lead (R$)", "num": ["Investimento (R$)"], "den": ["Leads Meta"]},
    {"nome": "Lead → reunião (%)", "num": ["Reuniões agendadas"], "den": ["Leads Meta"]},
    {"nome": "Comparecimento (%)", "num": ["Reuniões realizadas"], "den": ["Reuniões realizadas", "No-show"]},
    {"nome": "Assertividade (%)", "num": ["Fechados"], "den": ["Reuniões realizadas"]},
    {"nome": "Lead → cliente (%)", "num": ["Fechados"], "den": ["Leads Meta"]},
    {"nome": "Custo por reunião realizada (R$)", "num": ["Investimento (R$)"], "den": ["Reuniões realizadas"]},
    {"nome": "CAC (R$)", "num": ["Investimento (R$)"], "den": ["Fechados"]},
    {"nome": "ROAS (x)", "num": ["Receita fechada (R$)"], "den": ["Investimento (R$)"]},
]


def g(serie: pd.Series, chave: str) -> float:
    """Pega um valor da série, 0 se a coluna não existir (ex.: planilha sem valor)."""
    return serie.get(chave, 0.0)


def contagens(df: pd.DataFrame, tem_valor: bool = True) -> pd.Series:
    """Contagens base de um grupo de reuniões."""
    s = df["status_padrao"]
    fechados = df[s == "Fechado"]
    neg = df[s == "Em negociação"]
    base = {
        "Reuniões agendadas": len(df),
        "Reuniões realizadas": s.isin(STATUS_REALIZADA).sum(),
        "Fechados": (s == "Fechado").sum(),
        "Em negociação": (s == "Em negociação").sum(),
        "Reunião feita sem desfecho": (s == "Reunião feita").sum(),
        "Perdidos": (s == "Perdido").sum(),
        "No-show": (s == "No-show").sum(),
        "Remarcadas": (s == "Remarcado").sum(),
        "Canceladas": (s == "Cancelado").sum(),
        "Ainda vão acontecer": (s == "Agendado").sum(),
        "Não classificadas": s.isin(["Não classificado", "Sem status"]).sum(),
        "Receita fechada (R$)": fechados["valor"].sum(),
        "Valor em negociação (R$)": neg["valor"].sum(),
        "Valor perdido (R$)": df.loc[s == "Perdido", "valor"].sum(),
    }
    if not tem_valor:  # planilha sem coluna de valor: não inventa receita zerada
        base = {k: v for k, v in base.items() if "(R$)" not in k}
    return pd.Series(base)


def aplicar_taxas(df: pd.DataFrame, taxas: list[dict], linha_total: float | None = None) -> pd.DataFrame:
    df = df.copy()
    for t in taxas:
        if not all(c in df for c in t["num"]):
            continue
        num = df[t["num"]].sum(axis=1)
        if t["den"] == "__TOTAL__":
            den = num.sum() if linha_total is None else linha_total
        else:
            if not all(c in df for c in t["den"]):
                continue
            den = df[t["den"]].sum(axis=1)
        df[t["nome"]] = div(num, den) * t.get("mult", 1)
    return df


def tabela_comercial(
    df: pd.DataFrame, coluna: str, rotulo: str, tem_valor: bool = True, ordem: list[str] | None = None
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[rotulo])
    t = df.groupby(coluna, dropna=False).apply(lambda x: contagens(x, tem_valor), include_groups=False)
    t = t.reset_index().rename(columns={coluna: rotulo})
    if ordem is not None:
        t[rotulo] = pd.Categorical(t[rotulo], ordem, ordered=True)
        t = t.sort_values(rotulo)
        t[rotulo] = t[rotulo].astype(str)
    else:
        t = t.sort_values(["Fechados", "Reuniões agendadas"], ascending=False)
    return t.reset_index(drop=True)


def agrupar_meta(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    grupo = (
        df.groupby(chaves, dropna=False)
        .agg(
            **{
                "Investimento (R$)": ("investimento", "sum"),
                "Impressões": ("impressoes", "sum"),
                "Alcance": ("alcance", "sum"),
                "Cliques no link": ("cliques", "sum"),
                "Leads / resultados": ("resultados", "sum"),
                "Tipo de resultado": ("tipo_resultado", lambda s: ", ".join(sorted(set(s)))),
            }
        )
        .reset_index()
    )
    return grupo.sort_values("Investimento (R$)", ascending=False).reset_index(drop=True)
