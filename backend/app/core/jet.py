"""JET — a nota do mês.

A análise já diz tudo o que aconteceu. O que ela não dizia é se o mês foi bom.
Trinta e sete KPIs não respondem isso: quem olha quer um número, e depois quer
saber o que derrubou esse número.

O JET responde as duas coisas. Ele lê o resultado pronto, compara cada
indicador com a meta que o cliente escreveu na planilha e devolve um Score de
0 a 100, uma nota por campanha e uma lista de pontos de melhoria em ordem de
quanto cada um custou de Score.

Três pilares, com peso:

    Resultado (40)      chegou no faturamento e no número de clientes?
    Eficiência (30)     o dinheiro rendeu? CAC, CPL e volume de leads
    Assertividade (30)  o funil converteu? comparecimento, fechamento, win rate

Duas decisões que o resto do módulo respeita:

1. **Meta ausente não vira nota.** Se o cliente não escreveu a meta de
   faturamento, o pilar Resultado não é pontuado com zero: ele sai do cálculo
   e os pesos dos outros dois são renormalizados. Um Score baixo tem de
   significar mês ruim, nunca planilha incompleta. O campo `pilares` diz quais
   entraram.

2. **Denominador vazio não é nota cheia.** CAC é investimento ÷ fechados, e o
   pipeline devolve 0,0 quando não houve fechamento. Zero reais por cliente
   parece a perfeição e é o pior mês possível. Todo indicador "quanto menor
   melhor" por isso declara o que precisa existir para ele valer; sem isso ele
   pontua 0 e vira ponto de melhoria. Foi o erro mais fácil de cometer aqui.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Teto de atingimento. Bater 300% de uma meta não compensa ter zerado outra,
# então o excedente é registrado no texto mas não entra no Score.
TETO = 1.0

PESOS_PILAR = {"resultado": 40, "eficiencia": 30, "assertividade": 30}

FAIXAS = [
    (85, "excelente", "O mês bateu o que foi combinado."),
    (70, "bom", "O mês entregou, com pontos a apertar."),
    (50, "atencao", "O mês ficou abaixo do combinado em mais de um ponto."),
    (0, "critico", "O mês não chegou perto das metas."),
]


@dataclass
class Indicador:
    """Um item pontuado: o que foi, o que devia ser, e quanto isso custou."""

    chave: str
    rotulo: str
    pilar: str
    peso: float
    sentido: str  # "min" = quanto maior melhor; "max" = quanto menor melhor
    valor: float
    meta: float
    formato: str
    atingimento: float  # 0..1, já com teto
    pontuado: bool
    motivo_fora: str = ""
    sugestao: str = ""

    @property
    def perda(self) -> float:
        """Quantos pontos de Score este indicador deixou na mesa."""
        return 0.0 if not self.pontuado else self.peso * (1 - self.atingimento)


@dataclass
class ResultadoJet:
    score: float = 0.0
    faixa: str = "critico"
    leitura: str = ""
    pilares: list[dict[str, Any]] = field(default_factory=list)
    indicadores: list[dict[str, Any]] = field(default_factory=list)
    campanhas: list[dict[str, Any]] = field(default_factory=list)
    melhorias: list[dict[str, Any]] = field(default_factory=list)
    metas_ausentes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "faixa": self.faixa,
            "leitura": self.leitura,
            "pilares": self.pilares,
            "indicadores": self.indicadores,
            "campanhas": self.campanhas,
            "melhorias": self.melhorias,
            "metas_ausentes": self.metas_ausentes,
        }


def _atingimento(valor: float, meta: float, sentido: str) -> float:
    """Quanto da meta foi cumprido, de 0 a 1.

    Em "min" (quanto maior melhor) é valor ÷ meta. Em "max" (quanto menor
    melhor, como CAC e CPL) é meta ÷ valor: gastar metade do teto dá 1,0 e
    gastar o dobro dá 0,5. Quem chama já garantiu que o valor é pontuável.
    """
    if meta <= 0:
        return 0.0
    bruto = (valor / meta) if sentido == "min" else (meta / valor if valor > 0 else 0.0)
    return max(0.0, min(TETO, bruto))


def _faixa(score: float) -> tuple[str, str]:
    for corte, nome, leitura in FAIXAS:
        if score >= corte:
            return nome, leitura
    return FAIXAS[-1][1], FAIXAS[-1][2]


# --------------------------------------------------------------------------- #
# A régua: qual KPI entra em qual pilar, com que peso e contra qual meta.
#
# `exige` é o guarda do denominador vazio descrito no topo do arquivo: a lista
# de KPIs que precisam ser maiores que zero para o indicador fazer sentido.
# `zera_se` é diferente — é a condição em que o indicador conta como zero em
# vez de sair do cálculo, porque a ausência ali é o próprio fracasso.
# --------------------------------------------------------------------------- #
REGUA: list[dict[str, Any]] = [
    # ---- Resultado (40) ----
    {"chave": "rec", "rotulo": "Receita fechada", "pilar": "resultado", "peso": 22, "sentido": "min", "meta": "receita_mes",
     "exige_valor": True, "formato": "brl",
     "sugestao": "A receita fechada ficou abaixo da meta. Veja em Pipeline o valor parado em "
                 "negociação: é de lá que sai o mês seguinte."},
    {"chave": "fec", "rotulo": "Clientes fechados", "pilar": "resultado", "peso": 18, "sentido": "min", "meta": "fechamentos_mes",
     "formato": "int",
     "sugestao": "Fecharam menos clientes do que a meta. Compare a assertividade com o volume de "
                 "reuniões: faltou conversa ou faltou conversão?"},
    # ---- Eficiência (30) ----
    {"chave": "cac", "rotulo": "CAC (custo por cliente)", "pilar": "eficiencia", "peso": 12, "sentido": "max", "meta": "cac_max",
     "exige": ["inv"], "zera_se": "fecp", "formato": "brl",
     "sugestao": "O custo por cliente passou do teto. Corte ou reduza a campanha de pior CAC na "
                 "tabela abaixo antes de aumentar orçamento em qualquer outra."},
    {"chave": "cpl", "rotulo": "Custo por lead", "pilar": "eficiencia", "peso": 8, "sentido": "max", "meta": "cpl_max",
     "exige": ["inv"], "zera_se": "leads", "formato": "brl",
     "sugestao": "O lead está caro. Criativo e público são as duas alavancas aqui, nessa ordem."},
    {"chave": "leads", "rotulo": "Leads recebidos", "pilar": "eficiencia", "peso": 6, "sentido": "min", "meta": "leads_mes",
     "formato": "int",
     "sugestao": "Entraram menos leads que o esperado. Confira se o orçamento foi gasto por "
                 "inteiro e se alguma campanha ficou pausada no meio do mês."},
    {"chave": "roas", "rotulo": "ROAS", "pilar": "eficiencia", "peso": 4, "sentido": "min", "meta": "roas",
     "exige": ["inv"], "exige_valor": True, "formato": "x",
     "sugestao": "O retorno sobre o investimento ficou abaixo da meta. Com o CAC no teto, o que "
                 "resolve é ticket, não volume."},
    # ---- Assertividade (30) ----
    {"chave": "assert", "rotulo": "Assertividade", "pilar": "assertividade", "peso": 12, "sentido": "min", "meta": "assertividade",
     "exige": ["real"], "formato": "pct",
     "sugestao": "De cada 100 reuniões feitas, fecharam menos do que a meta. Olhe os motivos de "
                 "perda: se 'achou caro' domina, o problema é ancoragem de valor na call."},
    # `exige_algum`: o comparecimento sai 100% numa planilha que nunca registra
    # no-show, porque toda reunião marcada aparece como realizada. Pontuar isso
    # seria premiar a lacuna. Basta uma ausência registrada no mês para o
    # indicador passar a valer.
    {"chave": "comp", "rotulo": "Comparecimento", "pilar": "assertividade", "peso": 6, "sentido": "min", "meta": "comparecimento",
     "exige": ["real"], "exige_algum": ["ns", "rem"], "formato": "pct",
     "sugestao": "Muita reunião marcada não acontece. Confirmação no dia anterior é a medida de "
                 "maior efeito e menor custo."},
    {"chave": "win", "rotulo": "Win rate", "pilar": "assertividade", "peso": 6, "sentido": "min", "meta": "win_rate",
     "exige": ["per"], "formato": "pct",
     "sugestao": "Entre quem já decidiu, a proporção de ganhos ficou abaixo da meta."},
    {"chave": "l2r", "rotulo": "Lead que vira reunião", "pilar": "assertividade", "peso": 4, "sentido": "min", "meta": "lead_para_reuniao",
     "exige": ["leads"], "formato": "pct",
     "sugestao": "Poucos leads viram reunião. O gargalo está entre o anúncio e a agenda: "
                 "velocidade da primeira resposta costuma ser a causa."},
    {"chave": "ctr", "rotulo": "CTR no link", "pilar": "assertividade", "peso": 2, "sentido": "min", "meta": "ctr",
     "exige": ["imp"], "formato": "pct",
     "sugestao": "O anúncio está sendo pouco clicado. É sinal de criativo, não de verba."},
]

ROTULO_META = {
    "receita_mes": "faturamento do mês",
    "fechamentos_mes": "clientes fechados no mês",
    "leads_mes": "leads no mês",
}


def _montar_indicadores(res, metas: dict[str, float]) -> tuple[list[Indicador], list[str]]:
    """Aplica a régua ao resultado. Devolve os indicadores e as metas que faltam."""
    ausentes: list[str] = []
    saida: list[Indicador] = []

    for linha in REGUA:
        chave, nome_meta = linha["chave"], linha["meta"]
        meta = float(metas.get(nome_meta, 0) or 0)
        valor = res.kpi(chave)
        # O rótulo do KPI é mais específico (traz o recorte "tráfego pago"),
        # mas some junto com o KPI quando a planilha não tem coluna de valor.
        rotulo = res.kpis.get(chave, {}).get("rotulo") or linha["rotulo"]

        ind = Indicador(
            chave=chave, rotulo=rotulo, pilar=linha["pilar"], peso=float(linha["peso"]),
            sentido=linha["sentido"], valor=valor, meta=meta, formato=linha["formato"],
            atingimento=0.0, pontuado=False, sugestao=linha["sugestao"],
        )

        # 1. O KPI nem existe nesta análise (planilha sem coluna de valor, por exemplo).
        if chave not in res.kpis or (linha.get("exige_valor") and not res.tem_valor):
            ind.motivo_fora = "a planilha não tem coluna de valor, então este indicador não existe"
            saida.append(ind)
            continue

        # 2. Meta não escrita: o indicador sai do cálculo e os pesos se
        #    redistribuem. Score baixo tem de ser mês ruim, não planilha vazia.
        if meta <= 0:
            ind.motivo_fora = "meta não preenchida na aba Metas da planilha"
            if nome_meta in ROTULO_META:
                ausentes.append(ROTULO_META[nome_meta])
            saida.append(ind)
            continue

        # 3. Não se aplica: sem investimento não há CAC, sem impressão não há CTR,
        #    sem perda registrada não há win rate confiável.
        algum = linha.get("exige_algum")
        if algum and all(res.kpi(k) <= 0 for k in algum):
            ind.motivo_fora = ("a planilha não registra no-show nem remarcação, então o "
                               "comparecimento sai 100% por falta de registro, não por mérito")
            saida.append(ind)
            continue

        falta = [k for k in linha.get("exige", []) if res.kpi(k) <= 0]
        if falta:
            ind.motivo_fora = {
                "inv": "não houve investimento em tráfego no período",
                "imp": "os anúncios não registraram impressões",
                "real": "nenhuma reunião foi realizada no período",
                "per": "nenhuma perda foi registrada, então o win rate não é confiável",
                "leads": "a Meta não registrou leads no período",
            }.get(falta[0], f"depende de {falta[0]}, que está zerado")
            saida.append(ind)
            continue

        # 4. O guarda do denominador vazio. CAC = investimento ÷ fechados, e o
        #    pipeline devolve 0,0 quando ninguém fechou. Zero real por cliente
        #    parece perfeito e é o pior mês possível: pontua 0, não sai fora.
        gatilho = linha.get("zera_se")
        if gatilho and res.kpi(gatilho) <= 0:
            ind.pontuado = True
            ind.atingimento = 0.0
            ind.motivo_fora = {
                "fecp": "nenhum cliente veio do tráfego pago no período",
                "leads": "a Meta não registrou nenhum lead",
            }.get(gatilho, "")
            saida.append(ind)
            continue

        ind.pontuado = True
        ind.atingimento = _atingimento(valor, meta, linha["sentido"])
        saida.append(ind)

    return saida, ausentes


def _pontuar(indicadores: list[Indicador]) -> tuple[float, list[dict[str, Any]]]:
    """Score 0..100 e o detalhe por pilar.

    Dentro de cada pilar o Score é a média dos atingimentos ponderada pelos
    pesos dos indicadores que entraram. Entre pilares, o peso de um pilar sem
    nenhum indicador pontuável é redistribuído entre os que sobraram — é o que
    impede que faltar meta de faturamento vire nota baixa.
    """
    pilares: list[dict[str, Any]] = []
    vivos: list[tuple[float, float]] = []  # (peso do pilar, nota 0..1)

    for nome, peso_pilar in PESOS_PILAR.items():
        do_pilar = [i for i in indicadores if i.pilar == nome and i.pontuado]
        peso_total = sum(i.peso for i in do_pilar)
        nota = (sum(i.peso * i.atingimento for i in do_pilar) / peso_total) if peso_total else None
        pilares.append({
            "chave": nome,
            "rotulo": {"resultado": "Resultado", "eficiencia": "Eficiência",
                       "assertividade": "Assertividade"}[nome],
            "peso": peso_pilar,
            "nota": None if nota is None else round(nota * 100, 1),
            "pontuado": nota is not None,
            "indicadores_dentro": len(do_pilar),
        })
        if nota is not None:
            vivos.append((float(peso_pilar), nota))

    if not vivos:
        return 0.0, pilares
    soma_pesos = sum(p for p, _ in vivos)
    score = sum(p * n for p, n in vivos) / soma_pesos * 100
    for p in pilares:
        p["peso_efetivo"] = round(PESOS_PILAR[p["chave"]] / soma_pesos * 100, 1) if p["pontuado"] else 0.0
    return score, pilares


def _melhorias(indicadores: list[Indicador], res) -> list[dict[str, Any]]:
    """Pontos de melhoria, do que mais custou Score para o que menos custou.

    Depois dos indicadores vêm as lacunas de registro. Elas não tiram Score
    (não dá para pontuar o que não foi medido), mas são o que impede o próximo
    mês de ter nota confiável, então entram na lista marcadas como tal.
    """
    itens: list[dict[str, Any]] = []

    for ind in sorted(indicadores, key=lambda i: i.perda, reverse=True):
        if not ind.pontuado or ind.perda <= 0.05:
            continue
        itens.append({
            "tipo": "indicador",
            "chave": ind.chave,
            "titulo": ind.rotulo,
            "custo": round(ind.perda, 1),
            "valor": ind.valor,
            "meta": ind.meta,
            "formato": ind.formato,
            "sentido": ind.sentido,
            "atingimento": round(ind.atingimento * 100, 1),
            "texto": ind.motivo_fora or ind.sugestao,
            "acao": ind.sugestao,
        })

    lacunas = []
    if res.kpi("per") <= 0 and res.kpi("real") > 0:
        lacunas.append((
            "Nenhuma perda registrada",
            "Sem a etapa 'Perdido' na planilha, a assertividade fica inflada e o win rate não "
            "pode ser calculado. É o registro que mais muda a nota do mês seguinte.",
        ))
    if res.kpi("ns") <= 0 and res.kpi("rem") <= 0 and res.kpi("ag") > 0:
        lacunas.append((
            "Nenhum no-show registrado",
            "O comparecimento sai 100% porque toda reunião marcada aparece como realizada. "
            "Registrar quem não compareceu é o que revela perda de agenda.",
        ))
    if res.kpi("sd") > 0:
        lacunas.append((
            f"{int(res.kpi('sd'))} reuniões sem desfecho",
            "A conversa aconteceu mas a planilha não diz se fechou ou perdeu. Enquanto ficarem "
            "assim, elas puxam a assertividade para baixo sem dizer por quê.",
        ))
    if "campanha_x_vendas" not in res.tabelas:
        lacunas.append((
            "Vendas não ligadas à campanha",
            "A planilha de reuniões não tem a coluna Campanha, então o JET pontua as campanhas "
            "só por custo de lead e clique. Com essa coluna, ele passa a pontuar por cliente "
            "fechado, que é o que decide onde cortar verba.",
        ))

    for titulo, texto in lacunas:
        itens.append({"tipo": "registro", "chave": None, "titulo": titulo, "custo": 0.0,
                      "valor": None, "meta": None, "formato": None, "sentido": None,
                      "atingimento": None, "texto": texto, "acao": texto})
    return itens


# --------------------------------------------------------------------------- #
# Nota por campanha
#
# Com a coluna Campanha na planilha de reuniões, a nota sai por cliente
# fechado — que é o que decide onde cortar verba. Sem ela, só dá para pontuar
# custo de lead e clique, e a nota diz isso de si mesma em `base`.
# --------------------------------------------------------------------------- #
CRITERIOS_VENDA = [
    {"col": "CAC (R$)", "peso": 5, "sentido": "max", "meta": "cac_max", "exige_col": "Fechados",
     "rotulo": "CAC"},
    {"col": "Custo por lead (R$)", "peso": 3, "sentido": "max", "meta": "cpl_max",
     "exige_col": "Leads Meta", "rotulo": "custo por lead"},
    {"col": "Lead → reunião (%)", "peso": 2, "sentido": "min", "meta": "lead_para_reuniao",
     "exige_col": "Leads Meta", "rotulo": "lead para reunião"},
]
CRITERIOS_MIDIA = [
    {"col": "Custo por lead (R$)", "peso": 5, "sentido": "max", "meta": "cpl_max",
     "exige_col": "Leads / resultados", "rotulo": "custo por lead"},
    {"col": "CTR no link (%)", "peso": 2, "sentido": "min", "meta": "ctr", "exige_col": None,
     "rotulo": "CTR"},
]


def _nota_campanhas(res, metas: dict[str, float]) -> list[dict[str, Any]]:
    tem_venda = "campanha_x_vendas" in res.tabelas
    df = res.tabelas.get("campanha_x_vendas")
    if df is None or df.empty:
        df = res.tabelas.get("meta_campanhas")
        tem_venda = False
    if df is None or df.empty:
        return []

    criterios = CRITERIOS_VENDA if tem_venda else CRITERIOS_MIDIA
    col_inv = "Investimento (R$)"
    linhas: list[dict[str, Any]] = []

    for _, linha in df.iterrows():
        investido = float(linha.get(col_inv) or 0)
        if investido <= 0:
            continue  # campanha sem verba no período não tem o que pontuar

        peso_usado, soma, porques = 0.0, 0.0, []
        for c in criterios:
            if c["col"] not in df.columns:
                continue
            meta = float(metas.get(c["meta"], 0) or 0)
            if meta <= 0:
                continue
            # o guarda do denominador vazio, de novo: custo por lead de uma
            # campanha sem lead vem 0 e pareceria a melhor do mês.
            if c["exige_col"] and float(linha.get(c["exige_col"]) or 0) <= 0:
                at = 0.0
                porques.append(f"nenhum resultado em {c['rotulo']}")
            else:
                valor = float(linha.get(c["col"]) or 0)
                at = _atingimento(valor, meta, c["sentido"])
                if at < 0.7:
                    porques.append(f"{c['rotulo']} fora da meta")
            peso_usado += c["peso"]
            soma += c["peso"] * at

        if peso_usado <= 0:
            continue
        nota = soma / peso_usado * 100
        faixa, _ = _faixa(nota)
        linhas.append({
            "campanha": str(linha.get("Campanha", "(sem nome)")),
            "investido": investido,
            "nota": round(nota, 1),
            "faixa": faixa,
            "fechados": int(linha["Fechados"]) if tem_venda and "Fechados" in df.columns else None,
            "leads": float(linha.get("Leads Meta" if tem_venda else "Leads / resultados") or 0),
            "porque": "; ".join(dict.fromkeys(porques)) or "dentro das metas",
            "base": "venda" if tem_venda else "midia",
        })

    linhas.sort(key=lambda x: (x["nota"], -x["investido"]))
    return linhas


def avaliar(res) -> ResultadoJet:
    """Lê um Resultado já calculado e devolve a nota do mês."""
    metas = dict(res.config.metas)
    indicadores, ausentes = _montar_indicadores(res, metas)
    score, pilares = _pontuar(indicadores)
    faixa, leitura = _faixa(score)

    fora = [p["rotulo"] for p in pilares if not p["pontuado"]]
    if len(fora) == len(pilares):
        leitura = ("Sem nenhuma meta preenchida não há o que pontuar. Preencha a aba Metas da "
                   "planilha-modelo e o Score aparece na próxima análise.")
    elif fora:
        # Uma nota alta sobre dois pilares de três não é a nota do mês inteiro,
        # e dizer só "excelente" esconderia isso de quem lê rápido.
        leitura = (f"{leitura} A nota cobre {len(pilares) - len(fora)} dos {len(pilares)} pilares: "
                   f"{' e '.join(fora)} ficou de fora por falta de meta ou de dado.")

    return ResultadoJet(
        score=score,
        faixa=faixa,
        leitura=leitura,
        pilares=pilares,
        indicadores=[{
            "chave": i.chave, "rotulo": i.rotulo, "pilar": i.pilar, "peso": i.peso,
            "sentido": i.sentido, "valor": i.valor, "meta": i.meta, "formato": i.formato,
            "atingimento": round(i.atingimento * 100, 1), "pontuado": i.pontuado,
            "motivo_fora": i.motivo_fora, "custo": round(i.perda, 1),
        } for i in indicadores],
        campanhas=_nota_campanhas(res, metas),
        melhorias=_melhorias(indicadores, res),
        metas_ausentes=sorted(set(ausentes)),
    )
