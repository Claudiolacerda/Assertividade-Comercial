"""Orquestração da análise: dos arquivos crus ao resultado completo.

Uma chamada a `analisar()` faz tudo o que o notebook fazia de cima a baixo e
devolve um objeto `Resultado` com as tabelas, os KPIs, o diagnóstico automático
e a auditoria de qualidade — pronto para virar JSON (frontend) ou Excel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config_analise import CAMPOS_REUNIOES_INFO, DIAS_PT, MESES_PT, STATUS_ORDEM, ConfigAnalise
from .jet import avaliar as avaliar_jet
from .leitura import ler_arquivos, ler_metas_da_planilha, padronizar
from .metricas import (
    TAXAS_COMERCIAIS,
    TAXAS_CRUZADAS,
    TAXAS_META,
    agrupar_meta,
    aplicar_taxas,
    contagens,
    g,
    tabela_comercial,
)
from .texto import br, div, fmt, normalizar, para_data, para_numero


class ErroDeAnalise(Exception):
    """Erro que o usuário final consegue entender e corrigir na planilha."""


@dataclass
class Resultado:
    """Tudo o que uma rodada de análise produz."""

    mes_referencia: str
    nome_mes: str
    tem_valor: bool
    tem_origem: bool
    config: ConfigAnalise

    kpis: dict[str, dict[str, Any]] = field(default_factory=dict)
    blocos: list[tuple[str, list[str]]] = field(default_factory=list)
    diagnostico: pd.DataFrame = field(default_factory=pd.DataFrame)
    qualidade: pd.DataFrame = field(default_factory=pd.DataFrame)
    resumo_qualidade: pd.DataFrame = field(default_factory=pd.DataFrame)
    mapeamento: pd.DataFrame = field(default_factory=pd.DataFrame)
    tabelas: dict[str, pd.DataFrame] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)
    tipos_resultado: list[str] = field(default_factory=list)
    cobertura: dict[str, Any] = field(default_factory=dict)
    jet: dict[str, Any] = field(default_factory=dict)
    # Preenchido fora de `analisar()`, pela camada de rota: o JEV usa rede e o
    # núcleo não pode depender disso. Fica vazio numa análise feita sem ele.
    jev: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    def kpi(self, chave: str) -> float:
        return self.kpis[chave]["valor"] if chave in self.kpis else 0.0

    def to_payload(self) -> dict[str, Any]:
        """Versão JSON-serializável, consumida pelo frontend."""
        return {
            "mes_referencia": self.mes_referencia,
            "nome_mes": self.nome_mes,
            "tem_valor": self.tem_valor,
            "tem_origem": self.tem_origem,
            "avisos": self.avisos,
            "tipos_resultado": self.tipos_resultado,
            "cobertura": self.cobertura,
            "jet": self.jet,
            "jev": self.jev,
            "blocos": [{"titulo": t, "chaves": ks} for t, ks in self.blocos],
            "kpis": self.kpis,
            "diagnostico": _tabela_json(self.diagnostico),
            "qualidade": _tabela_json(self.qualidade),
            "resumo_qualidade": _tabela_json(self.resumo_qualidade),
            "mapeamento": _tabela_json(self.mapeamento),
            "tabelas": {nome: _tabela_json(df) for nome, df in self.tabelas.items()},
        }


def _tabela_json(df: pd.DataFrame | None) -> list[dict[str, Any]]:
    """DataFrame -> lista de dicts com NaN/Timestamp já tratados."""
    if df is None or df.empty:
        return []
    saida = df.copy()
    for c in saida.columns:
        if pd.api.types.is_datetime64_any_dtype(saida[c]):
            saida[c] = saida[c].dt.strftime("%Y-%m-%d")
    saida = saida.astype(object).where(pd.notna(saida), None)
    registros = saida.to_dict(orient="records")
    for reg in registros:
        for k, v in reg.items():
            if isinstance(v, (np.integer,)):
                reg[k] = int(v)
            elif isinstance(v, (np.floating,)):
                reg[k] = None if not np.isfinite(v) else float(v)
            elif isinstance(v, np.bool_):
                reg[k] = bool(v)
            elif isinstance(v, list):
                reg[k] = ", ".join(str(x) for x in v)
    return registros


# ====================================================================== #
# Análise
# ====================================================================== #
def analisar(
    arquivos_meta: list[str | Path],
    arquivos_reunioes: list[str | Path],
    cfg: ConfigAnalise | None = None,
) -> Resultado:
    cfg = cfg or ConfigAnalise()
    avisos: list[str] = []

    # As metas da aba "Metas" da planilha vencem as guardadas na configuração:
    # quem escreveu o número na planilha deste mês está dizendo a meta deste
    # mês. A aba é opcional, e sem ela nada muda.
    metas_planilha = ler_metas_da_planilha(arquivos_reunioes)
    if metas_planilha:
        cfg = replace(cfg, metas={**cfg.metas, **metas_planilha})

    m_bruto, r_bruto, em_blocos, log_meta, log_reun = _ler(arquivos_meta, arquivos_reunioes, cfg, avisos)
    meta = _tratar_meta(m_bruto, cfg, avisos)
    reun, tem_valor, tem_origem, ano_padrao = _tratar_reunioes(r_bruto, cfg, avisos)

    mes, periodo, nome_mes, r, m, filtrou = _filtrar_periodo(reun, meta, cfg, em_blocos, avisos)

    res = Resultado(
        mes_referencia=mes,
        nome_mes=nome_mes,
        tem_valor=tem_valor,
        tem_origem=tem_origem,
        config=cfg,
        avisos=avisos,
    )

    ctx = _Contexto(
        cfg=cfg, res=res, r=r, m=m, reun=reun, periodo=periodo, filtrou=filtrou,
        em_blocos=em_blocos, ano_padrao=ano_padrao,
    )
    _metricas_meta(ctx)
    _metricas_comerciais(ctx)
    _ciclo_perdas_pipeline(ctx)
    _cruzamento(ctx)
    _kpis(ctx)
    _diagnostico(ctx)
    _qualidade(ctx, log_meta, log_reun)
    _cobertura(res, log_reun)
    res.jet = avaliar_jet(res).to_payload()
    return res


@dataclass
class _Contexto:
    """Estado compartilhado entre as etapas (o que no notebook eram variáveis globais)."""

    cfg: ConfigAnalise
    res: Resultado
    r: pd.DataFrame  # reuniões do período
    m: pd.DataFrame  # meta do período
    reun: pd.DataFrame  # reuniões antes do filtro
    periodo: pd.Period
    filtrou: bool
    em_blocos: bool
    ano_padrao: int
    geral: pd.Series = field(default_factory=pd.Series)
    pago: pd.Series = field(default_factory=pd.Series)
    rp: pd.DataFrame = field(default_factory=pd.DataFrame)
    inv: float = 0.0
    imp: float = 0.0
    alc: float = 0.0
    clq: float = 0.0
    leads: float = 0.0
    fech: pd.DataFrame = field(default_factory=pd.DataFrame)
    perd: pd.DataFrame = field(default_factory=pd.DataFrame)
    pipe: pd.DataFrame = field(default_factory=pd.DataFrame)
    suspeitos: pd.DataFrame = field(default_factory=pd.DataFrame)
    sem_valor: pd.DataFrame = field(default_factory=pd.DataFrame)
    diag: list[dict[str, str]] = field(default_factory=list)

    @property
    def tem_valor(self) -> bool:
        return self.res.tem_valor

    def add(self, area: str, nivel: str, texto: str) -> None:
        self.diag.append({"Área": area, "Nível": nivel, "Diagnóstico": br(texto)})


# ---------------------------------------------------------------------- #
# 1. Leitura
# ---------------------------------------------------------------------- #
def _ler(arquivos_meta, arquivos_reunioes, cfg: ConfigAnalise, avisos: list[str]):
    try:
        m_bruto, _ = ler_arquivos(
            arquivos_meta,
            {".csv", ".xlsx"},
            [cfg.colunas_meta["campanha"], cfg.colunas_meta["investimento"]],
            avisos,
        )
    except (FileNotFoundError, ValueError) as e:
        raise ErroDeAnalise(
            "Não consegui ler o relatório da Meta. Verifique se o arquivo exportado do Gerenciador de "
            f"Anúncios tem as colunas de campanha e de valor gasto. Detalhe: {e}"
        ) from e
    try:
        r_bruto, em_blocos = ler_arquivos(
            arquivos_reunioes,
            {".xlsx", ".xlsm", ".xls", ".csv"},
            [cfg.colunas_reunioes["cliente"], cfg.colunas_reunioes["status"]],
            avisos,
        )
    except (FileNotFoundError, ValueError) as e:
        raise ErroDeAnalise(
            "Não consegui ler a planilha de assertividade comercial. Ela precisa ter uma coluna de cliente "
            f"e uma de etapa/status. Detalhe: {e}"
        ) from e

    colunas_meta = {k: list(v) for k, v in cfg.colunas_meta.items()}
    if cfg.coluna_leads_meta:
        colunas_meta["resultados"] = [cfg.coluna_leads_meta]
    meta, log_meta = padronizar(m_bruto, colunas_meta, "Meta Ads")
    reun, log_reun = padronizar(r_bruto, cfg.colunas_reunioes, "Reuniões")
    return meta, reun, em_blocos, log_meta, log_reun


def _tratar_meta(meta: pd.DataFrame, cfg: ConfigAnalise, avisos: list[str]) -> pd.DataFrame:
    for c in ["investimento", "impressoes", "alcance", "cliques", "resultados"]:
        meta[c] = para_numero(meta[c]) if c in meta else 0.0
        meta[c] = meta[c].fillna(0.0)
    for c in ["data_inicio", "data_fim"]:
        if c in meta:
            meta[c] = para_data(meta[c])
    for c in ["campanha", "conjunto", "anuncio", "tipo_resultado"]:
        if c not in meta:
            meta[c] = "(sem informação)"
        meta[c] = meta[c].fillna("(sem informação)").astype(str)

    # remove linhas vazias / linha de totais que algumas exportações trazem
    meta = meta[~((meta["campanha"].str.strip().isin(["", "(sem informação)", "nan"])) & (meta["investimento"] == 0))]
    meta["tipo_resultado"] = meta["tipo_resultado"].str.replace("actions:", "", regex=False).replace(
        {
            "onsite_conversion.messaging_conversation_started_7d": "Conversas no WhatsApp/Direct iniciadas",
            "lead": "Leads (formulário)",
            "nan": "(sem resultado)",
        }
    )
    # campanhas pausadas que não gastaram nem apareceram no período só poluem as tabelas
    sem_entrega = meta[(meta["investimento"] == 0) & (meta["impressoes"] == 0)]
    meta = meta.drop(sem_entrega.index)
    if len(sem_entrega):
        avisos.append(
            f"{len(sem_entrega)} campanha(s) sem gasto e sem impressões no período ficaram fora das tabelas."
        )
    return meta


def _tratar_reunioes(reun: pd.DataFrame, cfg: ConfigAnalise, avisos: list[str]):
    reun = reun[reun["cliente"].notna() & (reun["cliente"].astype(str).str.strip() != "")].reset_index(drop=True) \
        if "cliente" in reun else reun

    if "status" not in reun:
        raise ErroDeAnalise(
            "Não encontrei a coluna de STATUS/ETAPA na planilha de reuniões. "
            "Renomeie a coluna para 'Etapa do Funil' ou 'Status'."
        )
    if "data_reuniao" not in reun and "data_agendamento" not in reun:
        raise ErroDeAnalise(
            "Não encontrei nenhuma coluna de DATA na planilha de reuniões "
            "(ex.: 'Data da Reunião Realizada' ou 'Data do Agendamento')."
        )

    ano_padrao = cfg.ano_padrao
    if ano_padrao is None:  # descobre o ano pelas datas completas
        anos = pd.concat(
            [
                reun[c].astype("string").str.extract(r"(20\d{2})")[0]
                for c in ["data_reuniao", "data_agendamento", "data_fechamento", "data_lead"]
                if c in reun
            ]
        ).dropna()
        ano_padrao = int(anos.mode()[0]) if len(anos) else datetime.now().year

    reun["data_reuniao_texto"] = reun["data_reuniao"].astype("string") if "data_reuniao" in reun else pd.NA
    for c in ["data_reuniao", "data_agendamento", "data_fechamento", "data_lead"]:
        if c in reun:
            reun[c] = para_data(reun[c], ano_padrao)
    if "data_agendamento" not in reun:
        reun["data_agendamento"] = pd.NaT
    if "data_reuniao" not in reun:
        reun["data_reuniao"] = pd.NaT
    # data usada no filtro/semana: data da reunião; se vazia, a do agendamento
    reun["data_referencia"] = reun["data_reuniao"].fillna(reun["data_agendamento"])

    # bool() é obrigatório: .any() devolve numpy.bool_, que não serializa em JSON
    # e derruba a gravação no banco — só aparece quando a planilha TEM a coluna.
    tem_valor = bool("valor" in reun and para_numero(reun["valor"]).notna().any())
    reun["valor"] = para_numero(reun["valor"]) if "valor" in reun else np.nan
    for c in ["cliente", "responsavel", "origem", "campanha", "produto", "motivo_perda", "observacoes"]:
        if c not in reun:
            reun[c] = np.nan
        reun[c] = reun[c].astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA})

    reun["status_original"] = reun["status"].astype("string").str.strip()
    reun["status_padrao"] = reun["status_original"].map(lambda t: _classificar_status(t, cfg))

    # "Cliente - Fulano" -> Marcação = Fulano (parceiro, indicação, vendedor...)
    partes_nome = reun["cliente"].str.extract(r"^\s*(.*?)\s*-\s*([^-]+?)\s*$")
    reun["marcacao"] = partes_nome[1].fillna("(sem marcação)")
    reun["cliente"] = partes_nome[0].fillna(reun["cliente"]).str.strip()

    def sinais(obs) -> list[str]:
        n = normalizar(obs)
        return [
            rotulo
            for rotulo, chaves in cfg.sinais_observacao.items()
            if n and any(normalizar(k) in n for k in chaves)
        ]

    reun["sinais_obs"] = reun["observacoes"].map(sinais)
    reun["sinais_texto"] = reun["sinais_obs"].map(", ".join).replace("", pd.NA)
    if cfg.classificar_perda_pela_observacao:
        mudar = (reun["status_padrao"] == "Reunião feita") & reun["sinais_obs"].map(lambda l: "Provável perda" in l)
        reun.loc[mudar, "status_padrao"] = "Perdido"
        reun.loc[mudar & reun["motivo_perda"].isna(), "motivo_perda"] = reun.loc[mudar, "observacoes"]
        if mudar.sum():
            avisos.append(f"{mudar.sum()} reunião(ões) reclassificada(s) como Perdido pela observação.")

    # origem paga x não paga
    tem_origem = bool(reun["origem"].notna().any())
    if tem_origem:
        padroes = [normalizar(p) for p in cfg.origens_trafego_pago]
        reun["trafego_pago"] = reun["origem"].map(
            lambda o: any(p in normalizar(o) for p in padroes) if pd.notna(o) else False
        )
        reun["trafego_pago"] |= reun["campanha"].notna()
    else:
        reun["trafego_pago"] = cfg.sem_origem_considerar_pago
    nao_pagas = [normalizar(x) for x in cfg.marcacoes_nao_pagas]
    if nao_pagas:
        reun.loc[reun["marcacao"].map(normalizar).isin(nao_pagas), "trafego_pago"] = False
    reun["origem"] = reun["origem"].fillna("(sem origem)")
    reun["responsavel"] = reun["responsavel"].fillna("(sem responsável)")
    reun["produto"] = reun["produto"].fillna("(sem produto)")
    return reun, tem_valor, tem_origem, ano_padrao


def _classificar_status(txt, cfg: ConfigAnalise) -> str:
    if pd.isna(txt) or str(txt).strip() == "":
        return "Sem status"
    if txt in cfg.status_manual:
        return cfg.status_manual[txt]
    n = normalizar(txt)
    for categoria, chaves in cfg.regras_status:
        if any(normalizar(k) in n for k in chaves):
            return categoria
    return "Não classificado"


# ---------------------------------------------------------------------- #
# 2. Período
# ---------------------------------------------------------------------- #
def _filtrar_periodo(
    reun: pd.DataFrame, meta: pd.DataFrame, cfg: ConfigAnalise, em_blocos: bool, avisos: list[str]
):
    mes = cfg.mes_referencia
    if mes is None:
        meses = reun["data_referencia"].dropna().dt.to_period("M")
        if not len(meses):
            raise ErroDeAnalise(
                "Nenhuma data válida na planilha de reuniões — não consigo saber o mês da análise. "
                "Preencha as datas ou escolha o mês manualmente."
            )
        mes = (meses.mode()[0] if em_blocos else meses.max()).strftime("%Y-%m")
    periodo = pd.Period(mes, "M")
    ini_mes, fim_mes = periodo.start_time.normalize(), periodo.end_time.normalize()
    nome_mes = f"{MESES_PT[periodo.month - 1]}/{periodo.year}"

    filtrar = (not em_blocos) if cfg.filtrar_reunioes_por_data == "auto" else bool(cfg.filtrar_reunioes_por_data)
    dref = reun["data_referencia"]
    no_periodo = dref.notna() & (dref.dt.to_period("M") == periodo)
    r = reun[no_periodo].copy() if filtrar else reun.copy()
    if r.empty:
        raise ErroDeAnalise(
            f"Nenhuma reunião de {nome_mes} na planilha enviada. Confira o mês escolhido ou as datas da planilha."
        )
    if not filtrar and not no_periodo.any():
        # Painel por semanas: as linhas entram sem filtro de data, então um mês escolhido
        # errado passaria batido. Avisa em vez de rotular silenciosamente.
        avisos.append(
            f"A planilha de reuniões é um painel por semanas e nenhuma das datas preenchidas é de "
            f"{nome_mes}. Todas as linhas foram analisadas como {nome_mes} — confirme se o mês está certo."
        )

    # Meta: se a exportação é diária, filtra; se é relatório de período, confere a cobertura
    aviso_meta = ""
    m = meta.copy()
    if "data_inicio" in m and m["data_inicio"].notna().any():
        diario = "data_fim" not in m or (m["data_inicio"] == m.get("data_fim", m["data_inicio"])).all()
        if diario:
            m = m[m["data_inicio"].dt.to_period("M") == periodo]
        else:
            ini_rel, fim_rel = m["data_inicio"].min(), m["data_fim"].max()
            if ini_rel > ini_mes or fim_rel < fim_mes or ini_rel.to_period("M") != periodo:
                aviso_meta = (
                    f"O relatório da Meta cobre {ini_rel:%d/%m/%Y} a {fim_rel:%d/%m/%Y}, "
                    f"diferente do mês analisado ({ini_mes:%d/%m/%Y} a {fim_mes:%d/%m/%Y})."
                )
    if aviso_meta:
        avisos.append(aviso_meta)
    return mes, periodo, nome_mes, r, m, filtrar


# ---------------------------------------------------------------------- #
# 3. Métricas da Meta
# ---------------------------------------------------------------------- #
def _metricas_meta(ctx: _Contexto) -> None:
    m, res = ctx.m, ctx.res
    res.tabelas["meta_campanhas"] = aplicar_taxas(
        agrupar_meta(m, ["campanha"]).rename(columns={"campanha": "Campanha"}),
        TAXAS_META,
        m["investimento"].sum(),
    )
    if (m["conjunto"] != "(sem informação)").any():
        res.tabelas["meta_conjuntos"] = aplicar_taxas(
            agrupar_meta(m, ["campanha", "conjunto"]).rename(
                columns={"campanha": "Campanha", "conjunto": "Conjunto de anúncios"}
            ),
            TAXAS_META,
        )
    if (m["anuncio"] != "(sem informação)").any():
        res.tabelas["meta_anuncios"] = aplicar_taxas(
            agrupar_meta(m, ["campanha", "conjunto", "anuncio"]).rename(
                columns={"campanha": "Campanha", "conjunto": "Conjunto de anúncios", "anuncio": "Anúncio"}
            ),
            TAXAS_META,
        )
    ctx.inv = float(m["investimento"].sum())
    ctx.imp = float(m["impressoes"].sum())
    ctx.alc = float(m["alcance"].sum())
    ctx.clq = float(m["cliques"].sum())
    ctx.leads = float(m["resultados"].sum())
    res.tipos_resultado = sorted(m["tipo_resultado"].unique())
    res.tabelas["base_meta"] = m.rename(columns={"investimento": "investimento (R$)"})


# ---------------------------------------------------------------------- #
# 4. Métricas comerciais
# ---------------------------------------------------------------------- #
def _metricas_comerciais(ctx: _Contexto) -> None:
    r, res, tv = ctx.r, ctx.res, ctx.res.tem_valor
    ctx.geral = contagens(r, tv)
    ctx.rp = r[r["trafego_pago"]]
    ctx.pago = contagens(ctx.rp, tv)

    if "semana_planilha" in r and r["semana_planilha"].notna().any():
        r["semana"] = r["semana_planilha"].fillna("(sem semana)")  # usa os blocos da própria planilha
    else:
        r["semana"] = r["data_referencia"].dt.to_period("W-SUN").map(
            lambda p: f"{p.start_time:%d/%m} a {p.end_time:%d/%m}" if pd.notna(p) else "(sem data)"
        )
    r["dia_semana"] = r["data_reuniao"].dt.dayofweek.map(lambda d: DIAS_PT[int(d)] if pd.notna(d) else "(sem data)")

    presentes = [s for s in STATUS_ORDEM if s in r["status_padrao"].unique()]
    por_status = (
        r.groupby("status_padrao")
        .agg(**{"Quantidade": ("status_padrao", "size"), "Valor total (R$)": ("valor", "sum")})
        .reindex(presentes)
        .reset_index()
        .rename(columns={"status_padrao": "Status padronizado"})
    )
    por_status["% do total (%)"] = div(por_status["Quantidade"], por_status["Quantidade"].sum())
    if not tv:
        por_status = por_status.drop(columns="Valor total (R$)")
    res.tabelas["por_status"] = por_status

    receita_total = g(ctx.geral, "Receita fechada (R$)")
    ordem_sem = (
        list(dict.fromkeys(r["semana"]))
        if ctx.em_blocos
        else list(dict.fromkeys(r.sort_values("data_referencia")["semana"]))
    )
    grupos = [
        ("por_responsavel", "responsavel", "Responsável", None),
        ("por_origem", "origem", "Origem", None),
        ("por_produto", "produto", "Produto", None),
        ("por_marcacao", "marcacao", "Marcação no nome", None),
        ("por_semana", "semana", "Semana", ordem_sem),
        ("por_dia", "dia_semana", "Dia da semana", DIAS_PT + ["(sem data)"]),
    ]
    for nome, coluna, rotulo, ordem in grupos:
        if nome == "por_produto" and not (r["produto"] != "(sem produto)").any():
            continue
        if nome == "por_marcacao" and not (r["marcacao"] != "(sem marcação)").any():
            continue
        if nome == "por_origem" and not ctx.res.tem_origem:
            continue
        tabela = tabela_comercial(r, coluna, rotulo, tv, ordem)
        res.tabelas[nome] = aplicar_taxas(tabela, TAXAS_COMERCIAIS, receita_total)

    # Status original x padronizado (transparência total da classificação)
    res.tabelas["mapa_status"] = (
        r.groupby(["status_padrao", "status_original"], dropna=False)
        .size()
        .rename("Quantidade")
        .reset_index()
        .rename(columns={"status_padrao": "Status padronizado", "status_original": "Texto escrito na planilha"})
    )
    matriz = pd.crosstab(r["responsavel"], r["status_padrao"]).reindex(columns=presentes, fill_value=0)
    res.tabelas["status_por_responsavel"] = matriz.reset_index().rename(columns={"responsavel": "Responsável"})


# ---------------------------------------------------------------------- #
# 5. Ciclo de venda, perdas e pipeline
# ---------------------------------------------------------------------- #
def _ciclo_perdas_pipeline(ctx: _Contexto) -> None:
    r, res, cfg, tv = ctx.r, ctx.res, ctx.cfg, ctx.res.tem_valor

    # ---- Ciclo de venda
    fech = r[r["status_padrao"] == "Fechado"].copy()
    if "data_fechamento" in fech and fech["data_fechamento"].notna().any():
        base_ini = (
            fech["data_lead"]
            if "data_lead" in fech and fech["data_lead"].notna().any()
            else fech["data_reuniao"]
        )
        fech["Dias até fechar"] = (fech["data_fechamento"] - base_ini).dt.days
        d = fech["Dias até fechar"].dropna()
        res.tabelas["ciclo"] = pd.DataFrame(
            {
                "Indicador": [
                    "Fechamentos com data", "Média (dias)", "Mediana (dias)", "Mais rápido (dias)",
                    "Mais lento (dias)", "Fechou no mesmo dia da reunião", "Fechou em até 7 dias",
                    "Fechou em mais de 7 dias",
                ],
                "Valor": [
                    len(d), d.mean(), d.median(), d.min(), d.max(),
                    (d == 0).sum(), ((d > 0) & (d <= 7)).sum(), (d > 7).sum(),
                ],
            }
        )
        res.tabelas["ciclo_por_responsavel"] = (
            fech.groupby("responsavel")["Dias até fechar"]
            .agg(["count", "mean", "median", "min", "max"])
            .reset_index()
            .rename(
                columns={
                    "responsavel": "Responsável", "count": "Fechamentos", "mean": "Média (dias)",
                    "median": "Mediana (dias)", "min": "Mínimo (dias)", "max": "Máximo (dias)",
                }
            )
        )
        cols = ["cliente", "responsavel", "origem", "data_reuniao", "data_fechamento", "Dias até fechar"]
        cols += ["valor"] if tv else []
        res.tabelas["fechamentos"] = (
            fech[cols]
            .rename(
                columns={
                    "cliente": "Cliente", "responsavel": "Responsável", "origem": "Origem",
                    "data_reuniao": "Data da reunião", "data_fechamento": "Data de fechamento",
                    "valor": "Valor (R$)",
                }
            )
            .sort_values("Dias até fechar")
        )
    ctx.fech = fech

    # ---- Tempo entre o agendamento e a reunião
    ag = r[r["data_agendamento"].notna() & r["data_reuniao"].notna()].copy()
    if len(ag):
        d = (ag["data_reuniao"] - ag["data_agendamento"]).dt.days
        res.tabelas["tempo_agendamento"] = pd.DataFrame(
            {
                "Indicador": [
                    "Reuniões com as duas datas", "Média (dias)", "Mediana (dias)",
                    "Reunião no mesmo dia do agendamento", "1 a 2 dias depois", "3 dias ou mais",
                ],
                "Valor": [len(d), d.mean(), d.median(), (d == 0).sum(), d.between(1, 2).sum(), (d >= 3).sum()],
            }
        )

    # ---- Motivos de perda
    perd = r[r["status_padrao"] == "Perdido"].copy()
    perd["motivo_perda"] = perd["motivo_perda"].fillna("(motivo não informado)")
    motivos = (
        perd.groupby("motivo_perda")
        .agg(**{"Quantidade": ("motivo_perda", "size"), "Valor potencial perdido (R$)": ("valor", "sum")})
        .sort_values("Quantidade", ascending=False)
        .reset_index()
        .rename(columns={"motivo_perda": "Motivo"})
    )
    if len(motivos):
        motivos["% das perdas (%)"] = div(motivos["Quantidade"], motivos["Quantidade"].sum())
    res.tabelas["motivos_perda"] = motivos
    ctx.perd = perd
    if not perd.empty:
        cols = ["cliente", "responsavel", "origem", "data_reuniao", "motivo_perda"] + (["valor"] if tv else [])
        res.tabelas["lista_perdas"] = perd[cols].rename(
            columns={
                "cliente": "Cliente", "responsavel": "Responsável", "origem": "Origem",
                "data_reuniao": "Data da reunião", "motivo_perda": "Motivo", "valor": "Valor (R$)",
            }
        )

    # ---- Pipeline em aberto
    hoje = pd.Timestamp.today().normalize()
    pipe = r[r["status_padrao"].isin(["Em negociação", "Reunião feita"])].copy()
    pipe["Dias em aberto"] = (hoje - pipe["data_referencia"]).dt.days
    pipe["Valor ponderado (R$)"] = pipe["valor"].fillna(0) * cfg.prob_fechamento_negociacao
    pipe["Temperatura"] = np.select(
        [
            pipe["sinais_obs"].map(lambda l: "Provável perda" in l),
            pipe["status_padrao"].eq("Em negociação")
            | pipe["sinais_obs"].map(lambda l: "Promessa de fechamento" in l),
        ],
        ["❄️ Fria (sinal de perda)", "🔥 Quente"],
        "🌤️ Morna",
    )
    pipe["Alerta"] = np.where(
        pipe["Dias em aberto"] > cfg.dias_alerta_pipeline,
        f"⚠️ sem atualização há +{cfg.dias_alerta_pipeline} dias",
        np.where(pipe["Dias em aberto"].isna(), "sem data", "ok"),
    )
    pipe["_ord"] = pipe["Temperatura"].map({"🔥 Quente": 0, "🌤️ Morna": 1, "❄️ Fria (sinal de perda)": 2})
    cols_pipe = [
        "cliente", "marcacao", "responsavel", "semana", "data_referencia", "status_original", "Temperatura",
        "sinais_texto", "observacoes", "Dias em aberto", "Alerta",
    ] + (["valor", "Valor ponderado (R$)"] if tv else [])
    res.tabelas["pipeline"] = (
        pipe.sort_values(["_ord", "Dias em aberto"], ascending=[True, False])[cols_pipe].rename(
            columns={
                "cliente": "Cliente", "marcacao": "Marcação", "responsavel": "Responsável", "semana": "Semana",
                "data_referencia": "Data", "status_original": "Etapa na planilha",
                "sinais_texto": "Sinais na observação", "observacoes": "Observação", "valor": "Valor (R$)",
            }
        )
    )
    ctx.pipe = pipe

    # ---- Observações: objeções e sinais
    exp = r[["cliente", "status_padrao", "semana", "observacoes", "sinais_obs"]].explode("sinais_obs").reset_index(
        drop=True
    )
    exp = exp[exp["sinais_obs"].notna()]
    res.tabelas["sinais_resumo"] = (
        exp.groupby("sinais_obs")
        .agg(**{"Clientes": ("cliente", "nunique")})
        .reset_index()
        .rename(columns={"sinais_obs": "Sinal na observação"})
        .sort_values("Clientes", ascending=False)
    )
    if len(exp):
        res.tabelas["sinais_por_status"] = (
            pd.crosstab(exp["sinais_obs"], exp["status_padrao"])
            .reset_index()
            .rename(columns={"sinais_obs": "Sinal na observação"})
        )
    lista = r[r["observacoes"].notna()][
        ["cliente", "marcacao", "semana", "status_padrao", "sinais_texto", "observacoes"]
    ].rename(
        columns={
            "cliente": "Cliente", "marcacao": "Marcação", "semana": "Semana",
            "status_padrao": "Status padronizado", "sinais_texto": "Sinais identificados",
            "observacoes": "Observação",
        }
    )
    if len(lista):
        lista["Sinais identificados"] = lista["Sinais identificados"].fillna("—")
    res.tabelas["observacoes"] = lista

    # ---- No-show / remarcadas
    res.tabelas["noshow"] = r[r["status_padrao"].isin(["No-show", "Remarcado", "Cancelado"])][
        ["cliente", "responsavel", "origem", "data_reuniao", "status_padrao", "status_original"]
    ].rename(
        columns={
            "cliente": "Cliente", "responsavel": "Responsável", "origem": "Origem",
            "data_reuniao": "Data da reunião", "status_padrao": "Status padronizado",
            "status_original": "Status na planilha",
        }
    )

    # ---- Base tratada (para o cliente conferir qualquer número)
    base = r.drop(columns=["status", "status_ord", "sinais_obs"], errors="ignore").rename(
        columns={"valor": "valor (R$)"}
    )
    if not tv:
        base = base.drop(columns=["valor (R$)"], errors="ignore")
    res.tabelas["base_reunioes"] = base.dropna(axis=1, how="all")


# ---------------------------------------------------------------------- #
# 6. Cruzamento Meta × Comercial
# ---------------------------------------------------------------------- #
def _cruzamento(ctx: _Contexto) -> None:
    res, tv = ctx.res, ctx.res.tem_valor
    funil = pd.DataFrame(
        {
            "Etapa": [
                "Impressões", "Cliques no link", "Leads / conversas (Meta)",
                "Reuniões agendadas (tráfego pago)", "Reuniões realizadas (tráfego pago)",
                "Clientes fechados (tráfego pago)",
            ],
            "Quantidade": [
                ctx.imp, ctx.clq, ctx.leads,
                ctx.pago["Reuniões agendadas"], ctx.pago["Reuniões realizadas"], ctx.pago["Fechados"],
            ],
        }
    )
    funil["Conversão da etapa anterior (%)"] = div(funil["Quantidade"], funil["Quantidade"].shift(1).fillna(0))
    funil["Conversão desde impressões (%)"] = div(funil["Quantidade"], ctx.imp)
    funil["Custo por etapa (R$)"] = div(ctx.inv, funil["Quantidade"])
    res.tabelas["funil"] = funil

    # Resultado por campanha: só é possível se a planilha de reuniões tiver "Campanha"
    if ctx.rp["campanha"].notna().any():
        meta_camp = res.tabelas["meta_campanhas"]
        base_m = meta_camp.assign(chave=meta_camp["Campanha"].map(normalizar))[
            ["chave", "Campanha", "Investimento (R$)", "Leads / resultados"]
        ].rename(columns={"Leads / resultados": "Leads Meta"})
        base_r = ctx.rp.assign(
            chave=ctx.rp["campanha"].fillna("(campanha não informada)").map(normalizar),
            campanha=ctx.rp["campanha"].fillna("(campanha não informada)"),
        )
        com = base_r.groupby("chave").apply(lambda x: contagens(x, tv), include_groups=False).reset_index()
        nomes = base_r.groupby("chave")["campanha"].first()
        cruz = base_m.merge(com, on="chave", how="outer")
        cruz["Campanha"] = cruz["Campanha"].fillna(cruz["chave"].map(nomes) + "  (não achada na Meta)")
        cruz = cruz.drop(columns="chave").fillna(0)
        cols = [
            "Campanha", "Investimento (R$)", "Leads Meta", "Reuniões agendadas", "Reuniões realizadas",
            "No-show", "Fechados", "Perdidos", "Em negociação",
        ] + (["Receita fechada (R$)", "Valor em negociação (R$)"] if tv else [])
        cruz = cruz[[c for c in cols if c in cruz]].sort_values("Investimento (R$)", ascending=False).reset_index(
            drop=True
        )
        res.tabelas["campanha_x_vendas"] = aplicar_taxas(cruz, TAXAS_CRUZADAS)


# ---------------------------------------------------------------------- #
# 7. KPIs do resumo executivo
# ---------------------------------------------------------------------- #
def _kpis(ctx: _Contexto) -> None:
    res, cfg, geral, pago = ctx.res, ctx.cfg, ctx.geral, ctx.pago
    metas = cfg.metas
    sem_noshow = (geral["No-show"] + geral["Remarcadas"] + geral["Canceladas"]) == 0
    receita_pago = g(pago, "Receita fechada (R$)")
    tipos = ", ".join(res.tipos_resultado)
    prob = cfg.prob_fechamento_negociacao

    # chave: (rótulo, valor ou fórmula, formato, explicação, meta)
    K: dict[str, tuple] = {
        "inv": ("Investimento em tráfego pago", ctx.inv, "brl", "Soma de 'Valor usado' da Meta no período", None),
        "imp": ("Impressões", ctx.imp, "int", "Quantas vezes os anúncios apareceram", None),
        "alc": ("Alcance (soma)", ctx.alc, "int",
                "Pessoas alcançadas — somado entre anúncios, pode ter sobreposição", None),
        "clq": ("Cliques no link", ctx.clq, "int", "Cliques que levaram ao destino do anúncio", None),
        "leads": ("Leads / resultados (Meta)", ctx.leads, "int", f"Coluna 'Resultados' da Meta ({tipos})", None),
        "ctr": ("CTR no link", "={clq}/{imp}", "pct", "Cliques ÷ impressões", ("min", metas["ctr"])),
        "cpc": ("CPC", "={inv}/{clq}", "brl", "Investimento ÷ cliques", None),
        "cpm": ("CPM", "={inv}/{imp}*1000", "brl", "Custo por mil impressões", None),
        "cpl": ("Custo por lead/conversa (CPL)", "={inv}/{leads}", "brl", "Investimento ÷ leads",
                ("max", metas["cpl_max"])),
        "ag": ("Reuniões agendadas (total)", geral["Reuniões agendadas"], "int",
               "Todas as linhas do mês na planilha de reuniões", None),
        "real": ("Reuniões realizadas (total)", geral["Reuniões realizadas"], "int",
                 "Fechado + Perdido + Em negociação + Reunião feita", None),
        "ns": ("No-show (total)", geral["No-show"], "int", "Cliente não compareceu", None),
        "rem": ("Remarcadas + canceladas", geral["Remarcadas"] + geral["Canceladas"], "int",
                "Não aconteceram no dia marcado", None),
        "fut": ("Ainda vão acontecer", geral["Ainda vão acontecer"], "int",
                "Status 'Agendado' — ficam fora das taxas", None),
        "fec": ("Fechados (total)", geral["Fechados"], "int", "Status padronizado = Fechado", None),
        "per": ("Perdidos (total)", geral["Perdidos"], "int", "Status padronizado = Perdido", None),
        "neg": ("Em negociação / follow-up (total)", geral["Em negociação"], "int",
                "Follow-up, proposta, aguardando retorno", None),
        "sd": ("Reunião feita, sem desfecho registrado", geral["Reunião feita sem desfecho"], "int",
               "Etapa 'Reunião Feita' — a conversa aconteceu, mas não diz se fechou ou perdeu", None),
        "agr": ("Agendamento → realização", "={real}/({real}+{ns}+{rem})", "pct",
                "Realizadas ÷ (realizadas + no-show + remarcadas/canceladas)", None),
        "comp": ("Comparecimento", "={real}/({real}+{ns})", "pct",
                 "Realizadas ÷ (realizadas + no-show)"
                 + ("" if not sem_noshow else " — a planilha não registra no-show, por isso tende a 100%"),
                 None if sem_noshow else ("min", metas["comparecimento"])),
        "assert": ("⭐ ASSERTIVIDADE (fechados ÷ realizadas)", "={fec}/{real}", "pct",
                   "De cada 100 reuniões feitas, quantas fecharam", ("min", metas["assertividade"])),
        "win": ("Win rate (fechados ÷ decididas)", "={fec}/({fec}+{per})", "pct",
                "Considera só quem já decidiu (fechou ou perdeu)"
                + (" — SEM PERDAS REGISTRADAS, por isso não é confiável" if geral["Perdidos"] == 0 else ""),
                ("min", metas["win_rate"]) if geral["Perdidos"] > 0 else None),
        "fag": ("Fechamento sobre agendadas", "={fec}/{ag}", "pct", "Fechados ÷ tudo que foi agendado", None),
        "rec": ("Receita fechada (total)", g(geral, "Receita fechada (R$)"), "brl",
                "Soma do valor dos fechados", None),
        "tm": ("Ticket médio", "={rec}/{fec}", "brl", "Receita ÷ fechados", None),
        "vneg": ("Valor em negociação", g(geral, "Valor em negociação (R$)"), "brl",
                 "Soma do valor das negociações abertas", None),
        "fcst": ("Forecast ponderado do pipeline", f"={{vneg}}*{prob}", "brl",
                 f"Valor em negociação × {prob:.0%} de probabilidade", None),
        "agp": ("Reuniões agendadas (tráfego pago)", pago["Reuniões agendadas"], "int",
                "Reuniões cuja origem é tráfego pago", None),
        "realp": ("Reuniões realizadas (tráfego pago)", pago["Reuniões realizadas"], "int",
                  "Idem, só as realizadas", None),
        "fecp": ("Fechados (tráfego pago)", pago["Fechados"], "int", "Clientes vindos do tráfego pago", None),
        "recp": ("Receita fechada (tráfego pago)", receita_pago, "brl",
                 "Receita dos clientes vindos do tráfego pago", None),
        "l2r": ("Lead → reunião agendada", "={agp}/{leads}", "pct", "Reuniões agendadas pagas ÷ leads da Meta",
                ("min", metas["lead_para_reuniao"])),
        "l2c": ("Lead → cliente", "={fecp}/{leads}", "pct", "Fechados pagos ÷ leads da Meta", None),
        "cpr": ("Custo por reunião realizada", "={inv}/{realp}", "brl",
                "Investimento ÷ reuniões realizadas pagas", None),
        "cac": ("CAC (custo por cliente)", "={inv}/{fecp}", "brl",
                "Investimento ÷ clientes fechados do tráfego pago", ("max", metas["cac_max"])),
        "roas": ("ROAS", "={recp}/{inv}", "x", "Receita do tráfego pago ÷ investimento", ("min", metas["roas"])),
        "roi": ("ROI", "=({recp}-{inv})/{inv}", "pct", "(Receita − investimento) ÷ investimento", None),
    }
    blocos = [
        ("TRÁFEGO PAGO (META)", ["inv", "imp", "alc", "clq", "leads", "ctr", "cpc", "cpm", "cpl"]),
        (
            "COMERCIAL — TODAS AS ORIGENS",
            ["ag", "real", "ns", "rem", "fut", "fec", "neg", "sd", "per", "agr", "comp", "assert", "win",
             "fag", "rec", "tm", "vneg", "fcst"],
        ),
        (
            "RESULTADO DO TRÁFEGO PAGO (META × REUNIÕES)",
            ["agp", "realp", "fecp", "recp", "l2r", "l2c", "cpr", "cac", "roas", "roi"],
        ),
    ]
    if not res.tem_valor:  # sem coluna de valor: tira receita/ROAS em vez de mostrar zero
        fora = {"rec", "tm", "vneg", "fcst", "recp", "roas", "roi"}
        blocos = [(t, [k for k in ks if k not in fora]) for t, ks in blocos]
        K = {k: v for k, v in K.items() if k not in fora}

    # Avalia as fórmulas
    valores: dict[str, float] = {}

    def avaliar(k: str) -> float:
        if k in valores:
            return valores[k]
        v = K[k][1]
        if isinstance(v, str):
            expr = re.sub(r"\{(\w+)\}", lambda mm: f"({avaliar(mm.group(1))})", v[1:])
            try:
                v = float(eval(expr))  # noqa: S307 - expressão montada só a partir de K, sem entrada do usuário
                v = 0.0 if not np.isfinite(v) else v
            except ZeroDivisionError:
                v = 0.0
        valores[k] = float(v)
        return valores[k]

    for k in K:
        avaliar(k)

    res.blocos = blocos
    res.kpis = {
        k: {
            "rotulo": K[k][0],
            "valor": valores[k],
            "formula": K[k][1] if isinstance(K[k][1], str) else None,
            "formato": K[k][2],
            "texto": br(fmt(valores[k], K[k][2])),
            "explicacao": K[k][3],
            "meta_tipo": K[k][4][0] if K[k][4] else None,
            "meta_valor": K[k][4][1] if K[k][4] else None,
            "dentro_da_meta": (
                None
                if not K[k][4]
                else (valores[k] >= K[k][4][1] if K[k][4][0] == "min" else 0 < valores[k] <= K[k][4][1])
            ),
        }
        for k in K
    }
    ctx.res.kpis = res.kpis


# ---------------------------------------------------------------------- #
# 8. Diagnóstico automático
# ---------------------------------------------------------------------- #
def _diagnostico(ctx: _Contexto) -> None:
    res, cfg, r, geral = ctx.res, ctx.cfg, ctx.r, ctx.geral
    tabelas, kpis = res.tabelas, res.kpis
    valor = lambda k: kpis[k]["valor"] if k in kpis else 0.0  # noqa: E731

    # Metas
    for k, dados in kpis.items():
        if dados["meta_tipo"]:
            ctx.add(
                "Metas",
                "✅ Dentro da meta" if dados["dentro_da_meta"] else "⚠️ Abaixo da meta",
                f"{dados['rotulo']}: {fmt(dados['valor'], dados['formato'])} "
                f"(meta {'mínima' if dados['meta_tipo'] == 'min' else 'máxima'} "
                f"{fmt(dados['meta_valor'], dados['formato'])}).",
            )

    # Campanhas da Meta
    mc = tabelas.get("meta_campanhas", pd.DataFrame())
    if not mc.empty:
        com_leads = mc[mc["Leads / resultados"] > 0]
        if len(com_leads):
            b = com_leads.nsmallest(1, "Custo por lead (R$)").iloc[0]
            w = com_leads.nlargest(1, "Custo por lead (R$)").iloc[0]
            ctx.add(
                "Meta", "ℹ️",
                f"Menor CPL: '{b['Campanha']}' (R$ {b['Custo por lead (R$)']:,.2f}). "
                f"Maior CPL: '{w['Campanha']}' (R$ {w['Custo por lead (R$)']:,.2f}).",
            )
        for _, z in mc[(mc["Leads / resultados"] == 0) & (mc["Investimento (R$)"] > 0)].iterrows():
            ctx.add(
                "Meta", "🔴 Atenção",
                f"'{z['Campanha']}' gastou R$ {z['Investimento (R$)']:,.2f} sem gerar nenhum resultado.",
            )
    if len(res.tipos_resultado) > 1:
        ctx.add(
            "Meta", "⚠️ Atenção",
            f"Há tipos de resultado diferentes somados como lead ({', '.join(res.tipos_resultado)}). "
            "Compare CPL entre campanhas do mesmo tipo.",
        )
    for a in res.avisos:
        ctx.add("Dados", "⚠️ Atenção", a)

    # Campanha × vendas
    cz = tabelas.get("campanha_x_vendas", pd.DataFrame())
    if not cz.empty:
        vend = cz[cz["Fechados"] > 0]
        if len(vend) and "CAC (R$)" in vend:
            b = vend.nsmallest(1, "CAC (R$)").iloc[0]
            roas = f", ROAS {b['ROAS (x)']:.2f}x" if "ROAS (x)" in b else ""
            ctx.add(
                "Campanhas", "✅",
                f"Campanha com menor CAC: '{b['Campanha']}' — {b['Fechados']:.0f} cliente(s), "
                f"CAC R$ {b['CAC (R$)']:,.2f}{roas}.",
            )
        for _, z in cz[(cz["Fechados"] == 0) & (cz["Investimento (R$)"] > 0)].iterrows():
            ctx.add(
                "Campanhas", "🔴 Atenção",
                f"'{z['Campanha']}' investiu R$ {z['Investimento (R$)']:,.2f}, gerou "
                f"{z['Reuniões agendadas']:.0f} reunião(ões) e nenhum fechamento.",
            )

    # Equipe
    col_assert = "Assertividade - fechamento s/ realizadas (%)"
    pr = tabelas.get("por_responsavel", pd.DataFrame())
    if not pr.empty and col_assert in pr:
        pr = pr[(pr["Reuniões realizadas"] > 0) & (pr["Responsável"] != "(sem responsável)")]
        if len(pr) > 1:
            b, w = pr.iloc[pr[col_assert].argmax()], pr.iloc[pr[col_assert].argmin()]
            ctx.add(
                "Equipe", "ℹ️",
                f"Maior assertividade: {b['Responsável']} ({b[col_assert]:.1%} em "
                f"{b['Reuniões realizadas']:.0f} reuniões). "
                f"Menor: {w['Responsável']} ({w[col_assert]:.1%} em {w['Reuniões realizadas']:.0f}).",
            )

    # Perdas
    motivos = tabelas.get("motivos_perda", pd.DataFrame())
    if len(motivos) and motivos.iloc[0]["Motivo"] != "(motivo não informado)":
        top = motivos.iloc[0]
        vp = f", R$ {top['Valor potencial perdido (R$)']:,.2f}" if "Valor potencial perdido (R$)" in top else ""
        ctx.add(
            "Perdas", "ℹ️",
            f"Principal motivo de perda: '{top['Motivo']}' ({top['% das perdas (%)']:.0%} das perdas{vp}).",
        )
    if len(motivos) and (motivos["Motivo"] == "(motivo não informado)").any():
        q = motivos.loc[motivos["Motivo"] == "(motivo não informado)", "Quantidade"].iloc[0]
        ctx.add(
            "Dados", "⚠️ Atenção",
            f"{q} perda(s) sem motivo registrado — preencher ajuda a entender o que trava a venda.",
        )

    # Pipeline
    pipe = ctx.pipe
    paradas = int((pipe["Dias em aberto"] > cfg.dias_alerta_pipeline).sum()) if len(pipe) else 0
    if paradas:
        extra = (
            f" — somam R$ {pipe.loc[pipe['Dias em aberto'] > cfg.dias_alerta_pipeline, 'valor'].sum():,.2f}"
            if res.tem_valor
            else ""
        )
        ctx.add(
            "Pipeline", "⚠️ Atenção",
            f"{paradas} oportunidade(s) em aberto há mais de {cfg.dias_alerta_pipeline} dias{extra}. "
            "Vale fazer follow-up ou dar como perdida.",
        )
    quentes = pipe[pipe["Temperatura"] == "🔥 Quente"] if len(pipe) else pipe
    if len(quentes):
        ctx.add(
            "Pipeline", "🔥 Oportunidade",
            f"{len(quentes)} cliente(s) quentes para fechar agora: "
            f"{', '.join(quentes['cliente'].astype(str))}.",
        )
    if geral["Perdidos"] == 0 and geral["Reuniões realizadas"] > 0:
        frias = int((pipe["Temperatura"] == "❄️ Fria (sinal de perda)").sum()) if len(pipe) else 0
        ctx.add(
            "Perdas", "⚠️ Atenção",
            f"Nenhuma reunião está marcada como perdida. {geral['Reunião feita sem desfecho']:.0f} reuniões "
            f"estão só como 'Reunião feita' e {frias} delas têm sinal claro de perda na observação. "
            "Sem registrar perdas, a assertividade real fica escondida — crie a etapa 'Perdido' na planilha.",
        )

    # Objeções
    sr = tabelas.get("sinais_resumo", pd.DataFrame())
    if len(sr):
        top = sr[~sr["Sinal na observação"].isin(["Pediu retorno / follow-up"])].head(3)
        if len(top):
            ctx.add(
                "Objeções", "ℹ️",
                "Sinais mais frequentes nas observações: "
                + "; ".join(f"{row['Sinal na observação']} ({row['Clientes']} clientes)" for _, row in top.iterrows())
                + ".",
            )

    # CAC e marcações
    fech_marc = r[(r["status_padrao"] == "Fechado") & (r["marcacao"] != "(sem marcação)")]
    if len(fech_marc) and not cfg.marcacoes_nao_pagas:
        fecp_sem = ctx.pago["Fechados"] - len(fech_marc[fech_marc["trafego_pago"]])
        marcs = ", ".join(sorted(fech_marc["marcacao"].unique()))
        ctx.add(
            "CAC", "⚠️ Confirmar",
            f"{len(fech_marc)} dos {geral['Fechados']:.0f} fechamentos têm a marcação '{marcs}' no nome. "
            f"Hoje eles contam como tráfego pago (CAC R$ {valor('cac'):,.2f}). Se vieram de indicação/parceiro, "
            f"o CAC real do anúncio é R$ {div(ctx.inv, fecp_sem):,.2f} ({fecp_sem:.0f} clientes). "
            "Para corrigir, marque essa etiqueta como 'não paga' na configuração.",
        )

    # Avisos de dados
    if (geral["No-show"] + geral["Remarcadas"] + geral["Canceladas"]) == 0:
        ctx.add(
            "Dados", "ℹ️",
            "Nenhuma reunião registrada como no-show, remarcada ou cancelada. Se isso aconteceu no mês, "
            "crie essas etapas na planilha — senão comparecimento e 'agendamento → realização' aparecem em "
            "100% sem refletir a realidade.",
        )
    if not res.tem_valor:
        ctx.add(
            "Dados", "ℹ️",
            "A planilha não tem coluna de valor do contrato — receita, ticket médio, ROAS e ROI não foram "
            "calculados. Adicione uma coluna 'Valor' (mensalidade ou valor do contrato) para liberar esses "
            "indicadores.",
        )
    if r["responsavel"].eq("(sem responsável)").mean() > 0.5:
        ctx.add(
            "Dados", "ℹ️",
            f"{r['responsavel'].eq('(sem responsável)').sum()} de {len(r)} reuniões estão sem 'Quem fez' — "
            "a comparação por vendedor fica incompleta.",
        )
    if geral["Ainda vão acontecer"]:
        ctx.add(
            "Dados", "ℹ️",
            f"{geral['Ainda vão acontecer']:.0f} reunião(ões) ainda com status 'Agendado' — ficam fora das "
            "taxas até serem atualizadas.",
        )
    if geral["Não classificadas"]:
        ctx.add(
            "Dados", "⚠️ Atenção",
            f"{geral['Não classificadas']:.0f} reunião(ões) com status não reconhecido. "
            "Veja a auditoria de qualidade dos dados.",
        )
    ctx.sem_valor = (
        r[(r["status_padrao"] == "Fechado") & (r["valor"].isna() | (r["valor"] == 0))]
        if res.tem_valor
        else r.iloc[0:0]
    )
    if len(ctx.sem_valor):
        ctx.add(
            "Dados", "⚠️ Atenção",
            f"{len(ctx.sem_valor)} fechamento(s) sem valor — receita, ticket médio e ROAS ficam subestimados.",
        )


# ---------------------------------------------------------------------- #
# 9. Qualidade dos dados
# ---------------------------------------------------------------------- #
def _qualidade(ctx: _Contexto, log_meta: pd.DataFrame, log_reun: pd.DataFrame) -> None:
    res, r, cfg = ctx.res, ctx.r, ctx.cfg
    problemas: list[dict[str, Any]] = []

    def prob(tipo: str, df_: pd.DataFrame, detalhe: str) -> None:
        for _, row in df_.iterrows():
            problemas.append(
                {
                    "Problema": tipo,
                    "Cliente": row.get("cliente"),
                    "Semana": row.get("semana_planilha", row.get("semana")),
                    "Data como está na planilha": row.get("data_reuniao_texto"),
                    "Status na planilha": row.get("status_original"),
                    "Observação": row.get("observacoes"),
                    "Detalhe": detalhe,
                }
            )

    prob("Status não reconhecido", r[r["status_padrao"] == "Não classificado"],
         "Ajuste as regras de status na configuração")
    prob("Sem status", r[r["status_padrao"] == "Sem status"], "Preencher o status na planilha")
    prob("Fechado sem valor", ctx.sem_valor, "Receita subestimada")
    if ctx.filtrou:
        prob("Sem data (fora da análise)", ctx.reun[ctx.reun["data_referencia"].isna()],
             "Linha ignorada por não ter data")
    else:
        prob("Reunião sem data", r[r["data_reuniao"].isna()],
             "Entra nas contagens, mas não em 'dia da semana' nem em tempo de agendamento")
        prob(
            "Data fora do mês",
            r[r["data_referencia"].notna() & (r["data_referencia"].dt.to_period("M") != ctx.periodo)],
            f"A data não é de {res.nome_mes} — provável erro de digitação",
        )
    prob("Agendamento depois da reunião", r[r["data_agendamento"] > r["data_reuniao"]],
         "Data do agendamento é posterior à da reunião")
    suspeito = r[
        (r["status_padrao"] == "Fechado")
        & r["sinais_obs"].map(
            lambda l: bool(
                set(l) & {"Promessa de fechamento", "Pediu retorno / follow-up", "Decide com cônjuge/sócio"}
            )
        )
    ]
    prob(
        "Fechado, mas a observação sugere que ainda não fechou",
        suspeito,
        "Confirme se o contrato foi mesmo assinado — pode estar inflando a assertividade",
    )
    dup = r[r["cliente"].notna() & r.duplicated(["cliente", "data_reuniao"], keep=False)]
    prob("Possível duplicidade", dup, "Mesmo cliente e mesma data")
    if "data_fechamento" in r:
        prob("Fechado sem data de fechamento", r[(r["status_padrao"] == "Fechado") & r["data_fechamento"].isna()],
             "Ciclo de venda não calculado para esta linha")
        prob("Data de fechamento antes da reunião", r[r["data_fechamento"] < r["data_reuniao"]], "Verificar datas")

    res.qualidade = pd.DataFrame(
        problemas,
        columns=["Problema", "Cliente", "Semana", "Data como está na planilha", "Status na planilha",
                 "Observação", "Detalhe"],
    )
    if len(suspeito):
        real = div(ctx.geral["Fechados"] - len(suspeito), ctx.geral["Reuniões realizadas"])
        ctx.add(
            "Dados", "⚠️ Confirmar",
            f"{len(suspeito)} cliente(s) marcados como Fechado têm observação de quem ainda vai decidir "
            f"({', '.join(suspeito['cliente'].astype(str))}). Se não fecharam, a assertividade real é "
            f"{real:.1%} e não {res.kpis['assert']['valor']:.1%}.",
        )
    res.diagnostico = pd.DataFrame(ctx.diag)
    res.resumo_qualidade = (
        res.qualidade["Problema"].value_counts().rename_axis("Problema").reset_index(name="Ocorrências")
        if len(res.qualidade)
        else pd.DataFrame({"Problema": ["Nenhum problema encontrado ✅"], "Ocorrências": [0]})
    )
    res.mapeamento = pd.concat([log_meta, log_reun], ignore_index=True)


# ---------------------------------------------------------------------- #
# 10. Nota da planilha — o que falta e o que aquilo destrava
# ---------------------------------------------------------------------- #
def _cobertura(res: Resultado, log_reun: pd.DataFrame) -> None:
    """Transforma o mapeamento de colunas em tarefa para o cliente.

    O sistema já sabia quais colunas não achou; faltava dizer, em português, o
    que cada ausência está custando em indicador.
    """
    PESO = {"obrigatorio": 0, "alto": 1, "medio": 2, "baixo": 3}
    encontrados = {
        linha["Campo do sistema"]: linha["Coluna encontrada no arquivo"]
        for _, linha in log_reun.iterrows()
        if linha["Coluna encontrada no arquivo"] != "— NÃO ENCONTRADA —"
    }
    campos = []
    for campo, info in CAMPOS_REUNIOES_INFO.items():
        achou = campo in encontrados
        # a coluna existe mas veio vazia: conta como ausente, senão a nota mente
        if achou and campo == "valor" and not res.tem_valor:
            achou = False
        if achou and campo == "origem" and not res.tem_origem:
            achou = False
        campos.append(
            {
                "campo": campo,
                "rotulo": info["rotulo"],
                "destrava": info["destrava"],
                "impacto": info["impacto"],
                "encontrado": achou,
                "coluna": encontrados.get(campo) if achou else None,
            }
        )
    campos.sort(key=lambda c: (c["encontrado"], PESO[c["impacto"]]))
    tem = sum(1 for c in campos if c["encontrado"])
    res.cobertura = {
        "encontrados": tem,
        "total": len(campos),
        "percentual": round(tem / len(campos), 4),
        "campos": campos,
        "faltando_alto_impacto": [c["rotulo"] for c in campos if not c["encontrado"] and c["impacto"] == "alto"],
    }
