"""Normalização de texto, números e datas — a base de toda comparação.

Extraído do notebook sem mudança de comportamento: é o que faz o sistema
aceitar planilha de cliente escrita "à mão" (R$ 1.500,00, "08/09/ 2026", "17/09/").
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd


def normalizar(txt) -> str:
    """Minúsculo, sem acentos e sem espaços duplicados."""
    if txt is None or (isinstance(txt, float) and np.isnan(txt)):
        return ""
    txt = unicodedata.normalize("NFKD", str(txt).strip().lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", txt)


def para_numero(serie: pd.Series) -> pd.Series:
    """Converte 'R$ 1.500,00', '1,5', '12%', 1500 etc. em float."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)

    def conv(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, (int, float, np.number)):
            return float(v)
        s = re.sub(r"[^\d,.\-]", "", str(v))
        if s in ("", "-", ".", ","):
            return np.nan
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
        elif s.count(",") > 1:
            s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        elif re.fullmatch(r"-?[1-9]\d{0,2}(\.\d{3})+", s):
            s = s.replace(".", "")
        try:
            return float(s)
        except ValueError:
            return np.nan

    return serie.map(conv).astype(float)


def para_data(serie: pd.Series, ano_padrao: int | None = None) -> pd.Series:
    """Datas em qualquer formato brasileiro, inclusive sem ano ('31/08') e sujas ('17/09/')."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie.dt.normalize()
    # A hora é cortada ANTES de tirar os espaços. Removendo espaço primeiro,
    # "05/09/2026 09:12" virava "05/09/202609:12" e não parseava — e um CRM de
    # WhatsApp exporta data com hora em toda linha, então a planilha inteira
    # ficava sem nenhuma data válida e a análise nem rodava.
    txt = serie.astype("string").str.strip()
    txt = txt.str.replace(r"[T ]\s*\d{1,2}:\d{2}(:\d{2})?.*$", "", regex=True)
    txt = txt.str.replace(r"\s+", "", regex=True).str.rstrip("/")
    if ano_padrao:
        sem_ano = txt.str.fullmatch(r"\d{1,2}/\d{1,2}").fillna(False)
        txt = txt.where(~sem_ano, txt + f"/{ano_padrao}")
    iso = txt.str.match(r"^\d{4}-\d{2}-\d{2}").fillna(False)
    out = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")
    if iso.any():
        out[iso] = pd.to_datetime(txt[iso].str[:10], format="%Y-%m-%d", errors="coerce")
    if (~iso).any():
        out[~iso] = pd.to_datetime(txt[~iso], dayfirst=True, format="mixed", errors="coerce")
    return out.dt.normalize()


def div(a, b):
    """Divisão que devolve 0 em vez de explodir — usada em toda taxa."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(b != 0, a / b, 0.0)
    return r.item() if r.ndim == 0 else r


def br(txt: str) -> str:
    """Troca 1,234.56 -> 1.234,56 apenas dentro dos números (nomes de campanha ficam intactos)."""
    troca = lambda t: t.translate(str.maketrans(",.", ".,"))  # noqa: E731
    txt = re.sub(r"R\$ -?\d[\d,.]*", lambda mm: troca(mm.group(0)), txt)
    return re.sub(r"-?\d[\d,.]*(?=%|x\b)", lambda mm: troca(mm.group(0)), txt)


def fmt(v: float, f: str) -> str:
    """Formata um KPI para exibição."""
    return {
        "brl": f"R$ {v:,.2f}",
        "pct": f"{v:.1%}",
        "int": f"{v:,.0f}",
        "x": f"{v:.2f}x",
    }[f]
