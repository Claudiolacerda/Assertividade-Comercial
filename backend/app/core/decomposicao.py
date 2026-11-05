"""Por que mudou. A pergunta que o cliente faz e que cinco indicadores soltos
não respondem.

A receita de um mês é um produto de etapas:

    receita = leads × (reuniões ÷ leads) × (realizadas ÷ reuniões)
              × (fechados ÷ realizadas) × (receita ÷ fechados)

Quando ela cai 20%, a causa está em um ou dois desses fatores, e o painel
atual obriga o usuário a comparar cinco números com os do mês passado e juntar
de cabeça. Quem tem quatro minutos não faz essa conta, e responde ao cliente
"caiu porque o mercado estava fraco".

O método é LMDI (índice de Divisia com média logarítmica). Escolhido por uma
razão prática: ele é EXATO — as contribuições somam exatamente a variação
observada, sem resíduo — e é independente da ordem dos fatores. A alternativa
ingênua (trocar um fator por vez) deixa um resíduo que ninguém sabe onde pôr,
e dá resultados diferentes conforme a ordem em que se troca.

A média logarítmica de a e b é (a-b)/ln(a/b), e é o peso que faz a soma fechar.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log

# A cadeia, do topo do funil até o dinheiro. A ordem é a do funil, e serve
# só para a leitura: o resultado não depende dela.
FATORES = [
    ("leads", "Volume de leads", "Quantos entraram", "int"),
    ("agendamento", "Taxa de agendamento", "Quantos leads viraram reunião", "pct"),
    ("comparecimento", "Comparecimento", "Quantas reuniões aconteceram", "pct"),
    ("assertividade", "Assertividade", "Quantas reuniões viraram venda", "pct"),
    ("ticket", "Ticket médio", "Quanto cada venda trouxe", "brl"),
]


@dataclass(frozen=True)
class Mes:
    """Os cinco fatores de um mês, já reduzidos a partir dos KPIs."""

    referencia: str
    leads: float
    agendamento: float
    comparecimento: float
    assertividade: float
    ticket: float

    @property
    def receita(self) -> float:
        return (
            self.leads * self.agendamento * self.comparecimento * self.assertividade * self.ticket
        )

    def fator(self, nome: str) -> float:
        return float(getattr(self, nome))

    @property
    def completo(self) -> bool:
        """Um fator zerado quebra o produto e a conta: o mês não serve."""
        return all(self.fator(n) > 0 for n, *_resto in FATORES)


def _media_log(a: float, b: float) -> float:
    """Média logarítmica, o peso que faz as contribuições somarem o total."""
    if a <= 0 or b <= 0:
        return 0.0
    if abs(a - b) < 1e-12:
        return a
    return (a - b) / log(a / b)


def montar_mes(valores: dict[str, float], referencia: str, leads: float | None = None) -> Mes | None:
    """Reduz os indicadores de um mês aos cinco fatores da cadeia.

    `valores` é o dicionário achatado (chave -> número) que o sistema guarda
    por análise. `leads` entra de fora de propósito: quem compara dois meses
    precisa usar a MESMA origem de lead nos dois, e essa decisão não cabe aqui
    dentro — um mês com total informado e outro sem viraria uma variação de
    volume que só existe no critério.
    """
    valor = lambda chave: float(valores.get(chave) or 0)  # noqa: E731
    leads = float(leads) if leads is not None else (valor("leadsinf") or valor("leads"))
    agendadas, realizadas = valor("ag"), valor("real")
    fechados, receita = valor("fec"), valor("rec")
    if min(leads, agendadas, realizadas, fechados, receita) <= 0:
        return None
    return Mes(
        referencia=referencia,
        leads=leads,
        agendamento=agendadas / leads,
        comparecimento=realizadas / agendadas,
        assertividade=fechados / realizadas,
        ticket=receita / fechados,
    )


def comparar(anterior: Mes | None, atual: Mes | None) -> dict | None:
    """Reparte a variação da receita entre os cinco fatores.

    Devolve None quando algum dos dois meses não tem a cadeia inteira: sem um
    dos fatores o produto não é a receita, e repartir uma diferença que não
    fecha seria pior que não repartir.
    """
    if not anterior or not atual or not anterior.completo or not atual.completo:
        return None

    r0, r1 = anterior.receita, atual.receita
    peso = _media_log(r1, r0)
    if peso <= 0 or not isfinite(peso):
        return None

    contribuicoes = []
    for nome, rotulo, explicacao, formato in FATORES:
        a, b = anterior.fator(nome), atual.fator(nome)
        efeito = peso * log(b / a) if a > 0 and b > 0 else 0.0
        contribuicoes.append({
            "fator": nome,
            "rotulo": rotulo,
            "explicacao": explicacao,
            # O formato vem junto: a tela não deve adivinhar que "leads" é
            # contagem e "ticket" é dinheiro a partir do nome da chave.
            "formato": formato,
            "antes": a,
            "depois": b,
            "variacao": (b / a - 1) if a > 0 else 0.0,
            "efeito_reais": efeito,
            # Quanto deste fator pesou na variação total, em módulo: é o que
            # ordena a leitura ("o que mais mexeu foi...").
            "peso": abs(efeito),
        })

    total = r1 - r0
    soma = sum(c["efeito_reais"] for c in contribuicoes)
    # O LMDI fecha por construção; a conferência existe para pegar erro de
    # implementação, não erro de método.
    assert abs(soma - total) < max(1.0, abs(total) * 0.001), "a decomposição não fechou"

    contribuicoes.sort(key=lambda c: c["peso"], reverse=True)
    return {
        "mes_anterior": anterior.referencia,
        "mes_atual": atual.referencia,
        "receita_antes": r0,
        "receita_depois": r1,
        "variacao_reais": total,
        "variacao_pct": (r1 / r0 - 1) if r0 else 0.0,
        "contribuicoes": contribuicoes,
        "leitura": _ler(total, contribuicoes),
    }


def _ler(total: float, contribuicoes: list[dict]) -> str:
    """Uma frase: o que puxou para cima e o que puxou para baixo."""
    direcao = "subiu" if total >= 0 else "caiu"
    maior = contribuicoes[0]
    # O maior fator na direção CONTRÁRIA é a informação que o usuário não vê
    # sozinho: o que segurou um mês ruim, ou o que estragou um mês bom.
    contrario = next(
        (c for c in contribuicoes if (c["efeito_reais"] > 0) != (total >= 0) and c["peso"] > 0),
        None,
    )
    frase = (
        f"A receita {direcao} e quem mais mexeu foi {maior['rotulo'].lower()} "
        f"({maior['variacao']:+.0%})."
    )
    if contrario:
        sentido = "segurou a queda" if total < 0 else "puxou para baixo"
        frase += f" Na direção oposta, {contrario['rotulo'].lower()} {sentido} ({contrario['variacao']:+.0%})."
    return frase
