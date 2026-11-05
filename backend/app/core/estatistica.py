"""Quanto de um número é medição e quanto é sorteio.

Uma taxa calculada sobre 35 reuniões não é um fato, é uma estimativa. Dizer
"assertividade de 25,7%, meta 30%, FORA DA META" sobre 9 fechamentos em 35
reuniões é afirmar uma reprovação que o dado não sustenta: com essa amostra, a
taxa real pode estar entre 14% e 42%, e a meta está inteira dentro dessa faixa.

O erro que isso causa é caro e silencioso. O cliente corta verba, troca
vendedor ou muda oferta por causa de uma oscilação que é sorteio, e no mês
seguinte "melhora" sozinha — o que confirma a decisão errada e ensina a
repetir.

Intervalo de Wilson, e não o normal simples (p ± 1,96·√(p(1-p)/n)): com
amostra pequena ou taxa perto de 0% ou 100%, o normal devolve limites abaixo
de zero ou acima de um, e erra a cobertura justamente onde mais importa. O de
Wilson é quase tão simples e se comporta.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

# z para 95% bilateral. Entra a mão: é uma constante, não vale uma dependência.
Z_95 = 1.959963984540054

# Abaixo disso a faixa é tão larga que o número não sustenta comparação com
# meta nenhuma. Não é um limite estatístico, é um limite de honestidade: com 5
# reuniões, qualquer taxa entre 20% e 80% é compatível com o que se viu.
MINIMO_PARA_COMPARAR = 10


@dataclass(frozen=True)
class Faixa:
    """A taxa medida e o intervalo em que a taxa real provavelmente está."""

    taxa: float
    minimo: float
    maximo: float
    n: int

    @property
    def largura(self) -> float:
        return self.maximo - self.minimo

    def para_json(self) -> dict:
        return {
            "taxa": self.taxa,
            "min": self.minimo,
            "max": self.maximo,
            "n": self.n,
            "largura": self.largura,
        }


def wilson(sucessos: float, total: float, z: float = Z_95) -> Faixa | None:
    """Intervalo de Wilson para uma proporção. None quando não há amostra.

    Sem denominador não há taxa: devolver (0, 0, 0) faria a tela mostrar uma
    faixa cravada em zero, que é a afirmação mais forte possível justamente
    onde não há informação nenhuma.
    """
    n = int(round(total))
    if n <= 0:
        return None
    k = max(0.0, min(float(sucessos), float(n)))
    p = k / n
    denominador = 1 + z**2 / n
    centro = (p + z**2 / (2 * n)) / denominador
    margem = z * sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominador
    # Arredonda antes de cravar: com k = n a conta dá exatamente 1, mas em
    # ponto flutuante sai 0,9999999999999999, e a faixa passava a excluir a
    # própria taxa medida — invariante que um teste checa, e com razão.
    baixo = round(max(0.0, centro - margem), 10)
    alto = round(min(1.0, centro + margem), 10)
    return Faixa(taxa=p, minimo=min(baixo, p), maximo=max(alto, p), n=n)


def veredito(faixa: Faixa | None, meta: float | None, tipo: str | None) -> str:
    """O que dá para afirmar sobre a taxa e a meta.

    "dentro" / "fora" só quando a meta está fora do intervalo: aí a diferença
    não se explica por sorteio. Quando a meta cai dentro da faixa, a resposta
    honesta não é "fora da meta" nem "dentro da meta", é "ainda não dá para
    dizer" — e essa terceira resposta é a que faltava no sistema.
    """
    if faixa is None or meta is None or tipo not in ("min", "max"):
        return "sem_meta"
    if faixa.n < MINIMO_PARA_COMPARAR:
        return "amostra_pequena"
    if tipo == "min":
        if faixa.minimo >= meta:
            return "dentro"
        if faixa.maximo < meta:
            return "fora"
    else:  # máximo: a meta é um teto
        if faixa.maximo <= meta:
            return "dentro"
        if faixa.minimo > meta:
            return "fora"
    return "indistinguivel"


def frase_do_veredito(veredito_: str, faixa: Faixa | None, rotulo: str) -> str | None:
    """A frase curta que acompanha o selo, quando ela acrescenta algo."""
    if faixa is None:
        return None
    if veredito_ == "amostra_pequena":
        return (
            f"{faixa.n} caso(s) é pouco para comparar com meta: a taxa real pode estar entre "
            f"{faixa.minimo:.0%} e {faixa.maximo:.0%}."
        )
    if veredito_ == "indistinguivel":
        return (
            f"A meta está dentro da faixa provável desta taxa ({faixa.minimo:.0%} a "
            f"{faixa.maximo:.0%}, com {faixa.n} casos): a diferença ainda pode ser sorteio, não "
            f"desempenho."
        )
    return None
