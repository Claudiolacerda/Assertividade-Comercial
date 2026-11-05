"""E se eu investir mais? A resposta que os meses já analisados conseguem dar.

A pergunta é a mais cara que existe numa agência, e a mais fácil de responder
errado. Com os meses guardados dá para medir o que aconteceu quando o
investimento mudou, e esse é o começo da resposta — não o fim dela. Três
limites que este módulo trata como parte do resultado, e não como letra miúda:

1. **Poucos meses não fazem uma reta.** Com dois pontos a reta é exata, o R²
   dá 1 e não existe margem de erro: parece a melhor previsão já feita, e é a
   pior. Abaixo de três meses o módulo recusa o ajuste e devolve a regra de
   três, dizendo que é uma regra de três.
2. **Investimento parado não ensina nada.** Se todos os meses gastaram o
   mesmo, não há como saber o efeito de mudar: não existe variação para
   observar.
3. **Correlação não é causa, e a reta não vale fora do que se viu.** Dobrar o
   investimento raramente dobra o resultado, porque o público bom se esgota
   antes. Todo cenário fora da faixa já praticada sai marcado.

A conta em si é mínimos quadrados a mão, que para uma reta é aritmética de
colégio. O intervalo é o de previsão (não o da média), que é o mais largo dos
dois e o único honesto para "quantas vendas vou ter no mês que vem".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Com menos de três meses não sobra grau de liberdade para estimar o erro, e
# uma previsão sem erro declarado é um chute com cara de conta.
MINIMO_MESES = 3

# t de Student a 95%, bilateral, por graus de liberdade (n - 2). Entra a mão
# porque o scipy não é dependência do projeto e isto é uma tabela de 30 linhas.
# O número é grande de propósito em amostra pequena: com 3 meses, a faixa fica
# larga, e ela ficar larga é a informação.
T_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
    27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
}

# O que se projeta a partir do investimento. A ordem é a da tela.
ALVOS = [
    ("fec", "Clientes fechados", "int"),
    ("rec", "Receita fechada", "brl"),
    ("leads", "Leads", "int"),
]

VARIACOES = [-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.5]


@dataclass
class Reta:
    """Uma reta ajustada, com o que é preciso para dizer o quanto confiar nela."""

    a: float  # intercepto
    b: float  # inclinação: resultado por real investido
    r2: float
    s: float  # desvio padrão dos resíduos
    n: int
    x_media: float
    sxx: float

    def prever(self, x: float) -> float:
        return self.a + self.b * x

    def margem(self, x: float) -> float:
        """Metade do intervalo de previsão a 95% em x.

        É o intervalo de PREVISÃO, não o da média: ele responde "quantas vendas
        terei", que é a pergunta, e não "qual a média de longo prazo", que não é.
        Por isso o 1 + dentro da raiz.
        """
        gl = self.n - 2
        if gl < 1 or self.sxx <= 0:
            return 0.0
        t = T_95.get(gl, 1.96)
        return t * self.s * float(np.sqrt(1 + 1 / self.n + (x - self.x_media) ** 2 / self.sxx))


def ajustar(x: list[float], y: list[float]) -> Reta | None:
    """Mínimos quadrados para uma reta. Devolve None quando não dá para ajustar."""
    xs, ys = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n = len(xs)
    if n < MINIMO_MESES or len(ys) != n:
        return None
    x_media, y_media = float(xs.mean()), float(ys.mean())
    sxx = float(((xs - x_media) ** 2).sum())
    if sxx <= 0:  # investimento igual em todos os meses: não há o que observar
        return None
    b = float(((xs - x_media) * (ys - y_media)).sum() / sxx)
    a = y_media - b * x_media
    resid = ys - (a + b * xs)
    sqe = float((resid**2).sum())
    sqt = float(((ys - y_media) ** 2).sum())
    # Mês nenhum variou no alvo (toda venda igual): a reta explica tudo por
    # vacuidade. Chamar isso de R² = 1 seria mentir para cima.
    r2 = 1.0 - sqe / sqt if sqt > 0 else 0.0
    s = float(np.sqrt(sqe / (n - 2))) if n > 2 else 0.0
    return Reta(a=a, b=b, r2=r2, s=s, n=n, x_media=x_media, sxx=sxx)


def _limpar(pontos: list[dict], alvo: str) -> tuple[list[float], list[float]]:
    """Pares (investimento, alvo) dos meses que têm os dois números."""
    x, y = [], []
    for p in pontos:
        inv, val = p.get("inv"), p.get(alvo)
        if inv is None or val is None or float(inv) <= 0:
            continue
        x.append(float(inv))
        y.append(float(val))
    return x, y


def _qualidade(reta: Reta, rotulo: str) -> tuple[bool, str | None]:
    """Se dá para usar a reta, e o que dizer quando ela é fraca.

    Uma reta ruim não é escondida: ela é mostrada com o motivo. Esconder
    deixaria o usuário sem saber que o investimento, nos meses dele, não
    explicou o resultado — que é em si um achado.
    """
    if reta.b <= 0:
        return False, (
            f"Nos meses medidos, investir mais não veio junto com mais {rotulo.lower()}. "
            "A reta desce, então ela não sustenta uma projeção de aumento."
        )
    if reta.r2 < 0.5:
        return False, (
            f"O investimento explica só {reta.r2:.0%} da variação de {rotulo.lower()}. "
            "O resto veio de outra coisa (oferta, equipe, sazonalidade), então trate o "
            "número como ordem de grandeza."
        )
    if reta.n < 5:
        return True, (
            f"São {reta.n} meses. A reta já diz alguma coisa, mas a margem é larga de "
            "propósito: cada mês novo a estreita."
        )
    return True, None


def projetar(
    pontos: list[dict],
    metas: dict[str, float] | None = None,
    total_analises: int | None = None,
) -> dict:
    """Monta a projeção do efeito do investimento sobre os resultados.

    `pontos` são os meses, cada um com `mes_referencia`, `inv` e os alvos.
    `metas` são as do cliente (o teto de CAC entra na leitura). `total_analises`
    é quantas análises existem ao todo: quando ele é maior que o número de
    meses, a tela precisa explicar a diferença, porque "tenho 3 análises" e "a
    conta usa 2 meses" parece erro do sistema e não é.
    """
    # Mês analisado sem investimento registrado não entra na conta: não há
    # eixo x. Mas ele também não pode sumir em silêncio, senão o usuário conta
    # as análises dele, conta os meses da tela e encontra uma diferença sem
    # explicação. A lista volta no payload e vira frase na leitura.
    ignorados = [
        p.get("mes_referencia") for p in pontos if not p.get("inv") and p.get("mes_referencia")
    ]
    pontos = [p for p in pontos if p.get("inv")]
    pontos = sorted(pontos, key=lambda p: p.get("mes_referencia") or "")
    n = len(pontos)
    investimentos = [float(p["inv"]) for p in pontos]
    atual = investimentos[-1] if investimentos else 0.0

    base = {
        "n_meses": n,
        "n_analises": total_analises if total_analises is not None else n,
        "meses_sem_investimento": sorted(ignorados),
        "ritmo": _ritmo(pontos),
        "minimo_meses": MINIMO_MESES,
        "investimento_atual": atual,
        "faixa_observada": (
            {"min": min(investimentos), "max": max(investimentos)} if investimentos else None
        ),
        "pontos": [
            {
                "mes_referencia": p.get("mes_referencia"),
                "inv": float(p["inv"]),
                **{chave: (None if p.get(chave) is None else float(p[chave])) for chave, _r, _f in ALVOS},
            }
            for p in pontos
        ],
        "alvos": [{"chave": c, "rotulo": r, "formato": f} for c, r, f in ALVOS],
    }

    if n == 0:
        return {**base, "metodo": "insuficiente", "motivo": "Nenhuma análise com investimento registrado."}

    retas: dict[str, Reta] = {}
    for chave, _rotulo, _f in ALVOS:
        x, y = _limpar(pontos, chave)
        reta = ajustar(x, y)
        if reta:
            retas[chave] = reta

    if not retas:
        parcial = {**base, **_regra_de_tres(pontos, atual, n)}
        return {
            **parcial,
            "manchete": _manchete(parcial),
            "resumo": _resumo(parcial),
            "leitura": _ler(parcial, metas or {}),
        }

    modelos, avisos = {}, []
    for chave, rotulo, _f in ALVOS:
        reta = retas.get(chave)
        if not reta:
            continue
        confiavel, aviso = _qualidade(reta, rotulo)
        modelos[chave] = {
            "inclinacao": reta.b,
            "por_mil": reta.b * 1000,  # efeito de cada R$ 1.000 a mais
            "intercepto": reta.a,
            "r2": reta.r2,
            "confiavel": confiavel,
            "aviso": aviso,
        }
        # Só o alvo principal (clientes fechados) manda aviso para a lista
        # geral. Os outros guardam o deles em `modelos[x]["aviso"]`: três
        # frases dizendo "o investimento explica pouco", uma por indicador,
        # gastam a atenção que a próxima linha precisa.
        if aviso and chave == "fec" and aviso not in avisos:
            avisos.append(aviso)

    faixa = base["faixa_observada"]
    cenarios = []
    for variacao in VARIACOES:
        inv = atual * (1 + variacao)
        cenario = {
            "variacao": variacao,
            "investimento": inv,
            "fora_do_historico": bool(faixa and (inv < faixa["min"] or inv > faixa["max"])),
        }
        for chave, _r, _f in ALVOS:
            reta = retas.get(chave)
            if not reta:
                continue
            valor = reta.prever(inv)
            margem = reta.margem(inv)
            cenario[chave] = {
                # Resultado negativo não existe: a reta pode cair abaixo de
                # zero fora da faixa observada, e um "-1,2 cliente" destrói a
                # confiança no resto da tela com razão.
                "valor": max(0.0, valor),
                "min": max(0.0, valor - margem),
                "max": max(0.0, valor + margem),
            }
        cenarios.append(cenario)

    # ---- A faixa que não informa nada é pior que faixa nenhuma ----
    # Com 3 meses sobra 1 grau de liberdade e o t de Student é 12,7: o
    # intervalo fica mais largo que a própria estimativa, e a tabela imprime
    # "8,5 clientes (0,0 a 18,5)" oito vezes. O número continua certo e a
    # leitura vira ruído. Melhor dizer uma vez que a margem não cabe na tela do
    # que repeti-la em cada linha.
    hoje = next((c for c in cenarios if c["variacao"] == 0), None)
    sem_faixa: list[str] = []
    for chave, rotulo, _f in ALVOS:
        dado = (hoje or {}).get(chave)
        if not dado or dado.get("min") is None:
            continue
        util = dado["valor"] > 0 and dado["min"] > 0 and (dado["max"] - dado["min"]) <= dado["valor"]
        if util:
            continue
        for c in cenarios:
            if chave in c:
                c[chave]["min"] = c[chave]["max"] = None
        sem_faixa.append(rotulo.lower())
        # O genérico "são N meses, a margem é larga" passa a sobrar: a frase
        # montada no fim diz a mesma coisa com o tamanho junto.
        avisos[:] = [a for a in avisos if not a.startswith(f"São {n} meses")]

    if sem_faixa:
        quais = ", ".join(sem_faixa[:-1]) + " e " + sem_faixa[-1] if len(sem_faixa) > 1 else sem_faixa[0]
        avisos.append(
            f"Com {n} meses, a margem de erro de {quais} fica maior que a própria previsão, então "
            "ela não é mostrada: leia os números como ordem de grandeza. Cada mês novo analisado "
            "estreita essa margem rápido."
        )

    completo = {
        **base,
        "metodo": "regressao",
        "modelos": modelos,
        "cenarios": cenarios,
        "avisos": avisos,
        "influencia": influencia(pontos),
    }
    return {
        **completo,
        "manchete": _manchete(completo),
        "resumo": _resumo(completo),
        "leitura": _ler(completo, metas or {}),
    }


def _brl(v: float, casas: int = 2) -> str:
    """R$ 1.234,56 com a pontuação brasileira, sem depender do locale do servidor."""
    return "R$ " + f"{v:,.{casas}f}".translate(str.maketrans(",.", ".,"))


def _num(v: float, casas: int = 1) -> str:
    return f"{v:,.{casas}f}".translate(str.maketrans(",.", ".,"))


_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _mes(iso: str | None) -> str:
    """"2026-10" -> "outubro/2026". Numa frase, o código não se lê."""
    if not iso or len(iso) != 7 or "-" not in iso:
        return iso or "esse mês"
    ano, mes = iso.split("-")
    try:
        return f"{_MESES[int(mes) - 1]}/{ano}"
    except (ValueError, IndexError):
        return iso


def _clientes(v: float) -> str:
    """"1,0 cliente" / "2,5 clientes": a frase é lida em voz alta em reunião."""
    return f"{_num(v)} cliente" + ("" if 0.95 <= abs(v) < 1.95 else "s")


def influencia(pontos: list[dict], alvo: str = "fec") -> list[dict]:
    """Refaz a reta sem cada mês, para ver o quanto ela depende de um ponto só.

    Com três meses, cada um carrega um terço da conclusão — e às vezes bem
    mais que isso. Um mês atípico no meio derruba o R² e achata a inclinação, e
    o painel mostra uma tendência fraca sem dizer que ela é fraca POR CAUSA de
    um ponto. Tirar um de cada vez e recalcular responde isso em uma linha:
    "sem setembro, cada R$ 1.000 a mais viria com 2,1 clientes em vez de 0,7".

    Deixar de fora é diagnóstico, não projeção: a reta sem o mês removido pode
    passar por apenas dois pontos, e aí o R² dela é 1 por construção e não quer
    dizer nada. Por isso a função devolve inclinação e nada mais — quem mostra
    isso na tela tem de dizer que é um "e se", não uma previsão alternativa.
    """
    x = [float(p["inv"]) for p in pontos if p.get("inv") and p.get(alvo) is not None]
    y = [float(p[alvo]) for p in pontos if p.get("inv") and p.get(alvo) is not None]
    nomes = [p.get("mes_referencia") for p in pontos if p.get("inv") and p.get(alvo) is not None]
    if len(x) < 3:
        return []

    cheia = ajustar(x, y)
    if not cheia:
        return []

    fora = []
    for i, nome in enumerate(nomes):
        sobra_x = x[:i] + x[i + 1 :]
        sobra_y = y[:i] + y[i + 1 :]
        reta = _reta_de_diagnostico(sobra_x, sobra_y)
        if reta is None:
            continue
        inclinacao, r2 = reta
        fora.append({
            "mes_referencia": nome,
            "por_mil_sem_ele": inclinacao * 1000,
            "por_mil_com_todos": cheia.b * 1000,
            # Quantas vezes a inclinação muda ao tirar este mês. É a medida de
            # influência que importa aqui: 1,0 é "não muda nada".
            "fator": (inclinacao / cheia.b) if cheia.b else 0.0,
            "r2_sem_ele": r2,
            "pontos_restantes": len(sobra_x),
        })
    return fora


def _reta_de_diagnostico(x: list[float], y: list[float]) -> tuple[float, float | None] | None:
    """Inclinação (e R², quando ele significa algo) de um ajuste de diagnóstico.

    Aceita dois pontos de propósito, porque é exatamente com três meses que a
    pergunta "quanto depende de um mês?" mais importa. Com dois pontos o R² é 1
    por construção, então ele volta como None em vez de voltar como 1: um "100%"
    aqui seria lido como confiança máxima, que é o oposto do que o número diz.
    """
    import numpy as _np

    if len(x) < 2 or len(set(x)) < 2:
        return None
    if len(x) == 2:
        inclinacao = (y[1] - y[0]) / (x[1] - x[0])
        return inclinacao, None
    reta = ajustar(x, y)
    return (reta.b, reta.r2) if reta else None


def _ritmo(pontos: list[dict]) -> dict | None:
    """O ritmo médio dos meses: soma contra soma, sem reta no meio.

    É a única afirmação sobre investimento e resultado que não depende de
    modelo nenhum — e por isso é a que sobra quando a regressão não se sustenta.
    "Cada R$ 1.000 investidos vieram acompanhados de 2,3 clientes" é um fato
    sobre o período; "cada R$ 1.000 A MAIS trazem 0,7 cliente" é uma previsão,
    que pode ou não estar de pé. As duas frases se parecem e dizem coisas
    diferentes, então o sistema publica as duas separadas e nomeadas.
    """
    inv = sum(float(x["inv"]) for x in pontos if x.get("inv"))
    if inv <= 0:
        return None
    soma = lambda chave: sum(  # noqa: E731
        float(x[chave]) for x in pontos if x.get("inv") and x.get(chave) is not None
    )
    fec, rec, leads = soma("fec"), soma("rec"), soma("leads")
    ritmo = {
        "meses": len([x for x in pontos if x.get("inv")]),
        "investimento_total": inv,
        "clientes": fec,
        "receita": rec,
        "leads": leads,
        "cac_medio": inv / fec if fec else None,
        "clientes_por_mil": fec / inv * 1000 if fec else None,
        "leads_por_mil": leads / inv * 1000 if leads else None,
        "receita_por_real": rec / inv if rec else None,
    }
    return ritmo


def _resumo(p: dict) -> dict | None:
    """A frase de uma linha que descreve o período, sem prometer o futuro."""
    ritmo = p.get("ritmo") or {}
    por_mil, cac = ritmo.get("clientes_por_mil"), ritmo.get("cac_medio")
    if not por_mil or not cac:
        return None
    # Plural escrito à mão: é uma frase para ser lida em voz alta numa reunião,
    # e "2,0 cliente(s) fechado(s)" trava a leitura.
    mes = "mês" if ritmo["meses"] == 1 else "meses"
    cliente = "cliente fechado" if 0.95 <= por_mil < 1.95 else "clientes fechados"
    partes = [
        f"Nos {ritmo['meses']} {mes} analisados, cada R$ 1.000 investidos em tráfego vieram "
        f"acompanhados de {_num(por_mil)} {cliente}"
    ]
    if ritmo.get("leads_por_mil"):
        partes.append(f"e {_num(ritmo['leads_por_mil'], 0)} leads")
    texto = " ".join(partes) + f", ou seja, {_brl(cac)} por cliente."
    if ritmo.get("receita_por_real"):
        texto += f" Cada R$ 1,00 investido andou junto com {_brl(ritmo['receita_por_real'])} de receita fechada."
    return {
        "nivel": "info",
        "texto": texto,
        "rodape": (
            "Isto descreve o que aconteceu no período, somando tudo. Não é o efeito de investir "
            "mais: para isso serve a tendência acima, que depende de a reta se sustentar."
        ),
    }


def _mes_dominante(influencias: list[dict]) -> dict | None:
    """O mês cuja remoção mais mexe na inclinação, se ele mexer demais.

    "Demais" é mudar de sinal ou dobrar/halvar o efeito. Abaixo disso a
    remoção muda o número sem mudar a história, e apontar o mês ali seria
    transformar ruído em suspeita.
    """
    if not influencias:
        return None
    pior = max(influencias, key=lambda i: abs(i["fator"] - 1))
    if pior["fator"] < 0 or abs(pior["fator"] - 1) >= 1.0 or pior["fator"] < 0.5:
        return pior
    return None


def _manchete(p: dict) -> dict | None:
    """A frase grande do topo, decidida junto com os números que ela resume.

    Ela nasce aqui, e não na tela, porque é a afirmação mais lida do cartão e
    precisa ser a mesma no PDF. E muda de conteúdo, não só de cor, quando a
    reta é fraca: um número grande e verde dizendo "+0,7 cliente por R$ 1.000"
    acima de uma linha dizendo "o investimento explica 5% da variação" faz o
    leitor acreditar no de cima, porque ele é maior, vem primeiro e tem cara de
    conclusão. Quem manda aqui é o número menor.
    """
    modelos = p.get("modelos") or {}
    vendas, receita = modelos.get("fec"), modelos.get("rec")
    if not vendas or vendas.get("por_mil", 0) <= 0:
        if vendas and vendas.get("inclinacao", 0) <= 0 and p.get("metodo") == "regressao":
            return {
                "nivel": "atencao",
                "texto": (
                    f"Nos {p.get('n_meses')} meses medidos, investir mais não veio junto com mais "
                    "vendas. A tendência não sustenta uma projeção de aumento: os cenários abaixo "
                    "são hipótese, não previsão."
                ),
            }
        return None

    por_mil = vendas["por_mil"]
    extra = (
        f" e {_brl(receita['por_mil'], 0)} de receita"
        if receita and receita.get("por_mil", 0) > 0
        else ""
    )
    if p.get("metodo") == "regra_de_tres":
        return {
            "nivel": "info",
            "texto": (
                f"A cada R$ 1.000 a mais no anúncio, o ritmo médio dos meses dá mais "
                f"{_clientes(por_mil)}{extra}."
            ),
        }
    if vendas.get("confiavel"):
        return {
            "nivel": "ok",
            "texto": (
                f"A cada R$ 1.000 a mais no anúncio, os meses medidos trazem mais "
                f"{_clientes(por_mil)}{extra}."
            ),
        }
    return {
        "nivel": "atencao",
        "texto": (
            f"Nos {p.get('n_meses')} meses medidos, o investimento explica só "
            f"{(vendas.get('r2') or 0) * 100:.0f}% da variação das vendas. O que mexeu no "
            "resultado foi outra coisa, então os cenários abaixo são hipótese, não previsão."
        ),
    }


def _ler(p: dict, metas: dict[str, float]) -> list[dict]:
    """A leitura dos números: o que eles dizem, em frases.

    A tabela de cenários mostra o QUE; isto diz o E DAÍ. São as mesmas contas,
    ditas na ordem em que a decisão é tomada: o anúncio ainda se paga na
    margem? o próximo cliente custa mais ou menos que os de hoje? até onde dá
    para subir sem apostar? e o quanto dessa conta é firme?

    Tudo determinístico, pela mesma razão do JET: o número e a frase têm de
    concordar sempre, e uma frase gerada por modelo de linguagem pode discordar
    do número que está logo acima dela.
    """
    linhas: list[dict] = []
    modelos = p.get("modelos") or {}
    vendas, receita = modelos.get("fec"), modelos.get("rec")
    atual = p.get("investimento_atual") or 0.0
    faixa = p.get("faixa_observada") or {}
    regra = p.get("metodo") == "regra_de_tres"
    n_meses, n_analises = p.get("n_meses") or 0, p.get("n_analises") or 0

    if p.get("metodo") == "insuficiente":
        return []

    # ---- 1. O anúncio se paga na margem? ----
    if receita and receita["por_mil"] > 0:
        por_real = receita["por_mil"] / 1000
        # Na regra de três o número é a MÉDIA, não o efeito de um real a mais:
        # dizer "a mais" ali seria atribuir à proporção uma leitura marginal
        # que só a reta sustenta.
        abertura = "No ritmo médio dos meses, cada R$ 1,00 investido veio acompanhado de" if regra \
            else "Cada R$ 1,00 a mais em anúncio veio junto com"
        if por_real >= 1:
            linhas.append({
                "nivel": "ok",
                "texto": (
                    f"{abertura} {_brl(por_real)} de receita fechada. É receita, não lucro: "
                    f"desconte o custo de entregar o serviço antes de decidir se vale subir."
                ),
            })
        else:
            linhas.append({
                "nivel": "critico",
                "texto": (
                    f"{abertura} só {_brl(por_real)} de receita. O anúncio não está se pagando: "
                    f"antes de aumentar a verba, o que precisa melhorar é a conversão, não o "
                    f"alcance."
                ),
            })

    # ---- 2. O próximo cliente custa mais ou menos que os de hoje? ----
    if vendas and vendas["por_mil"] > 0:
        cac_marginal = 1000 / vendas["por_mil"]
        # O CAC médio é o MEDIDO (investimento somado ÷ clientes somados), não
        # o que a reta estima para hoje. Com um ajuste fraco os dois divergem, e
        # chamar de "médio" um valor que saiu do modelo é apresentar previsão
        # como fato — justamente no caso em que o modelo não merece confiança.
        cac_medio = (p.get("ritmo") or {}).get("cac_medio") or 0.0
        if cac_medio > 0 and not regra:
            if cac_marginal > cac_medio * 1.15:
                linhas.append({
                    "nivel": "atencao",
                    "texto": (
                        f"O próximo cliente custa {_brl(cac_marginal)}, acima do CAC médio de "
                        f"{_brl(cac_medio)}. Parte das vendas acontece sem depender do anúncio, "
                        f"então subir a verba rende menos do que a média faz parecer."
                    ),
                })
            elif cac_marginal < cac_medio * 0.85:
                linhas.append({
                    "nivel": "ok",
                    "texto": (
                        f"O próximo cliente custa {_brl(cac_marginal)}, abaixo do CAC médio de "
                        f"{_brl(cac_medio)}. A operação ainda ganha com escala: cada real a mais "
                        f"rende melhor que os anteriores."
                    ),
                })
            else:
                linhas.append({
                    "nivel": "info",
                    "texto": (
                        f"O próximo cliente custa {_brl(cac_marginal)}, na mesma faixa do CAC "
                        f"médio de {_brl(cac_medio)}. O resultado cresce junto com a verba, sem "
                        f"ganho nem perda de eficiência no caminho medido."
                    ),
                })
        teto = float(metas.get("cac_max") or 0)
        if teto > 0 and not regra:
            if cac_marginal <= teto:
                sobra = (teto - cac_marginal) / teto
                linhas.append({
                    "nivel": "ok",
                    "texto": (
                        f"Esse custo cabe no seu teto de {_brl(teto)} por cliente, com "
                        f"{sobra:.0%} de folga. Enquanto couber, aumentar a verba é a alavanca "
                        f"mais direta que você tem."
                    ),
                })
            else:
                linhas.append({
                    "nivel": "critico",
                    "texto": (
                        f"Esse custo já passa do seu teto de {_brl(teto)} por cliente. Cada "
                        f"cliente a mais entra fora da meta: o caminho aqui é melhorar a "
                        f"conversão antes de aumentar a verba."
                    ),
                })

    # ---- 3. Até onde dá para subir sem apostar? ----
    maximo = float(faixa.get("max") or 0)
    if maximo > 0 and atual > 0:
        if maximo > atual * 1.02:
            margem = maximo / atual - 1
            linhas.append({
                "nivel": "info",
                "texto": (
                    f"Você já operou com até {_brl(maximo)} num mês, que é {margem:.0%} acima de "
                    f"hoje. Até esse valor a conta se apoia no que aconteceu; acima dele, ela é "
                    f"extrapolação."
                ),
            })
        else:
            linhas.append({
                "nivel": "atencao",
                "texto": (
                    f"Hoje é o seu maior investimento já analisado ({_brl(atual)}). Qualquer "
                    f"cenário de aumento aqui é território novo: suba em degraus de 10% a 20% e "
                    f"meça cada um antes do próximo."
                ),
            })

    # ---- 3b. Algum mês ficou de fora? ----
    sem_inv = p.get("meses_sem_investimento") or []
    if sem_inv:
        lista = ", ".join(sem_inv)
        linhas.append({
            "nivel": "atencao",
            "texto": (
                f"{len(sem_inv)} mês(es) analisado(s) ficaram fora da conta por não terem "
                f"investimento registrado ({lista}). Sem o valor gasto não há como medir o efeito "
                f"de mudá-lo: confira se o relatório da Meta daquele mês foi enviado junto."
            ),
        })

    # ---- 3c. A conclusão depende de um mês só? ----
    dominante = _mes_dominante(p.get("influencia") or [])
    if dominante:
        fator, sem_ele, com_todos = dominante["fator"], dominante["por_mil_sem_ele"], dominante["por_mil_com_todos"]
        if fator < 0:
            efeito = (
                f"a tendência inverteria de sinal, passando a indicar {_clientes(abs(sem_ele))} "
                f"a MENOS por R$ 1.000 investidos"
            )
        else:
            efeito = (
                f"cada R$ 1.000 a mais viria com {_clientes(sem_ele)} em vez de "
                f"{_clientes(com_todos)}"
            )
        linhas.append({
            "nivel": "atencao",
            "texto": (
                f"A conclusão depende muito de um mês só: sem {_mes(dominante['mes_referencia'])}, "
                f"{efeito}. Com {n_meses} meses, um mês atípico domina a reta — vale olhar o que "
                f"houve nele antes de decidir pela tendência."
            ),
        })
    elif p.get("influencia"):
        linhas.append({
            "nivel": "ok",
            "texto": (
                "Nenhum mês sozinho manda na conta: tirando qualquer um deles, a tendência fica "
                "parecida. É o que dá firmeza a uma série curta."
            ),
        })

    # ---- 4. O quanto dessa conta é firme? ----
    if regra:
        falta = max(0, (p.get("minimo_meses") or MINIMO_MESES) - n_meses)
        extra = ""
        if n_analises > n_meses:
            extra = (
                f" Você tem {n_analises} análises, mas elas cobrem {n_meses} mês(es): a conta usa "
                f"a última versão de cada mês, então reprocessar o mesmo mês não conta como mês novo."
            )
        linhas.append({
            "nivel": "atencao",
            "texto": (
                f"Isto ainda é proporção, não tendência medida: ela supõe que cada real novo rende "
                f"igual ao primeiro.{extra} Com mais {falta} mês(es) de investimento diferente o "
                f"sistema passa a medir a tendência de verdade."
            ),
        })
    elif vendas and vendas["inclinacao"] == 0:
        linhas.append({
            "nivel": "info",
            "texto": (
                f"O número de clientes fechados foi o mesmo em todos os {n_meses} meses, mesmo "
                f"com o investimento variando. Isso não quer dizer que mudar a verba não adianta: "
                f"quer dizer que, nessa faixa, o gargalo não é o anúncio."
            ),
        })
    elif vendas:
        r2 = vendas.get("r2") or 0.0
        if r2 >= 0.7:
            linhas.append({
                "nivel": "ok",
                "texto": (
                    f"O investimento explica {r2:.0%} da variação das vendas nos {n_meses} meses "
                    f"medidos: a relação é forte o suficiente para planejar com ela, lembrando que "
                    f"ela descreve o passado."
                ),
            })
        else:
            # A manchete já diz o número; aqui entra só o que ela não diz: onde
            # procurar a explicação que falta.
            linhas.append({
                "nivel": "atencao",
                "texto": (
                    f"Com o investimento explicando {r2:.0%} da variação, o que mais mexeu no "
                    f"resultado foi outra coisa: oferta, equipe, qualidade do lead ou época do "
                    f"ano. É aí que está a alavanca deste mês, não na verba."
                ),
            })

    return linhas


def _regra_de_tres(pontos: list[dict], atual: float, n: int) -> dict:
    """O que dá para dizer sem reta: o ritmo médio, proporcional.

    Não é uma projeção, é uma conta de proporção com o nome certo. Ela supõe
    que o próximo real rende igual ao primeiro, e isso quase nunca é verdade —
    mas é melhor que a tela vazia, e muito melhor que uma reta fingida com dois
    pontos.
    """
    inv_total = sum(float(p["inv"]) for p in pontos)
    motivos = []
    if n < MINIMO_MESES:
        motivos.append(
            f"São {n} mês(es) analisado(s) e a regressão precisa de {MINIMO_MESES}: "
            "com dois pontos a reta passa exatamente por eles e a margem de erro some, "
            "o que faz a previsão parecer perfeita justamente quando é mais frágil."
        )
    else:
        motivos.append(
            "O investimento foi praticamente o mesmo em todos os meses, então não há "
            "variação para medir o efeito de mudá-lo."
        )

    modelos, cenarios = {}, []
    proporcoes: dict[str, float] = {}
    for chave, _rotulo, _f in ALVOS:
        total = sum(float(p[chave]) for p in pontos if p.get(chave) is not None)
        if inv_total <= 0 or total <= 0:
            continue
        proporcoes[chave] = total / inv_total
        modelos[chave] = {
            "inclinacao": total / inv_total,
            "por_mil": total / inv_total * 1000,
            "intercepto": 0.0,
            "r2": None,
            "confiavel": False,
            "aviso": None,
        }
    for variacao in VARIACOES:
        inv = atual * (1 + variacao)
        cenario = {"variacao": variacao, "investimento": inv, "fora_do_historico": variacao != 0}
        for chave, proporcao in proporcoes.items():
            cenario[chave] = {"valor": inv * proporcao, "min": None, "max": None}
        cenarios.append(cenario)

    return {
        "metodo": "regra_de_tres" if modelos else "insuficiente",
        "motivo": " ".join(motivos),
        "modelos": modelos,
        "cenarios": cenarios,
        "avisos": [
            "Isto é uma regra de três sobre a média dos meses, não uma regressão: ela supõe "
            "que cada real novo rende igual ao primeiro, o que raramente acontece."
        ],
    }
