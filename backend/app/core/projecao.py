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


def projetar(pontos: list[dict]) -> dict:
    """Monta a projeção do efeito do investimento sobre os resultados.

    `pontos` são os meses, cada um com `mes_referencia`, `inv` e os alvos.
    """
    pontos = [p for p in pontos if p.get("inv")]
    pontos = sorted(pontos, key=lambda p: p.get("mes_referencia") or "")
    n = len(pontos)
    investimentos = [float(p["inv"]) for p in pontos]
    atual = investimentos[-1] if investimentos else 0.0

    base = {
        "n_meses": n,
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
        return {**base, **_regra_de_tres(pontos, atual, n)}

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
        if aviso:
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

    return {
        **base,
        "metodo": "regressao",
        "modelos": modelos,
        "cenarios": cenarios,
        "avisos": avisos,
    }


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
