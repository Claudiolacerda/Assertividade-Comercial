"""Quando o negócio fecha, contando também os que ainda não fecharam.

O ciclo de venda do sistema sempre foi a média dos dias de quem fechou. O
problema não é o cálculo, é quem ele deixa de fora: o negócio que está em
negociação há 60 dias não entra em lugar nenhum. Como os ciclos longos ainda
não terminaram, a média só enxerga os curtos — o viés é sistemático e sempre
otimista. É o mesmo erro de perguntar o tempo de espera só a quem já foi
atendido.

Em estatística isso se chama censura à direita: do negócio aberto sabe-se algo
("já passou de 45 dias sem fechar"), só não se sabe o desfecho. Kaplan-Meier
usa exatamente essa informação parcial, e responde a pergunta que o comercial
faz de verdade: *de cada 100 reuniões, quantas fecham até 30 dias? até 60?*

Os perdidos entram como censurados na data em que foram perdidos. É uma
escolha, e vale dizer qual: a curva passa a responder "entre os negócios que
ainda estavam de pé, quando fecham", e não "qual fração de tudo acaba
fechando". Para a segunda pergunta o número certo é a taxa de conversão, que o
painel já tem, e por isso as duas aparecem juntas.
"""

from __future__ import annotations

from dataclasses import dataclass

# Marcos em dias que a operação usa para falar de ciclo.
MARCOS = [7, 15, 30, 60, 90]


@dataclass(frozen=True)
class Caso:
    """Um negócio: quantos dias observados e se o fechamento aconteceu."""

    dias: float
    fechou: bool


@dataclass
class Curva:
    """A curva de Kaplan-Meier e o que se lê dela."""

    pontos: list[dict]  # [{dias, sobreviventes, fechados, acumulado}]
    n: int
    eventos: int
    censurados: int
    mediana: float | None
    # Até quando se acompanhou. A curva fica plana daqui para trás até o último
    # fechamento, e mostrar esse trecho plano é o que deixa visível que o
    # acompanhamento continuou sem ninguém fechar.
    limite: float

    def ate(self, dias: float) -> float:
        """Fração que fechou até `dias`, pela curva."""
        acumulado = 0.0
        for ponto in self.pontos:
            if ponto["dias"] <= dias:
                acumulado = ponto["acumulado"]
            else:
                break
        return acumulado


def estimar(casos: list[Caso]) -> Curva | None:
    """Kaplan-Meier do tempo até fechar.

    Devolve None sem nenhum fechamento observado: uma curva reta em zero não
    seria uma estimativa, seria a ausência de uma.
    """
    casos = [c for c in casos if c.dias is not None and c.dias >= 0]
    if not casos or not any(c.fechou for c in casos):
        return None

    n = len(casos)
    tempos = sorted({c.dias for c in casos if c.fechou})
    em_risco = n
    sobrevivencia = 1.0
    pontos: list[dict] = []
    anterior = 0.0

    for t in tempos:
        # Quem saiu antes deste tempo (censurado ou fechado) já não está em
        # risco: é o que faz a conta usar a informação parcial em vez de
        # descartá-la.
        saiu_antes = sum(1 for c in casos if c.dias < t)
        em_risco = n - saiu_antes
        if em_risco <= 0:
            break
        eventos = sum(1 for c in casos if c.fechou and c.dias == t)
        sobrevivencia *= 1 - eventos / em_risco
        pontos.append({
            "dias": float(t),
            "em_risco": em_risco,
            "fechados": eventos,
            "acumulado": 1 - sobrevivencia,
        })
        anterior = t

    mediana = next((p["dias"] for p in pontos if p["acumulado"] >= 0.5), None)
    return Curva(
        pontos=pontos,
        n=n,
        eventos=sum(1 for c in casos if c.fechou),
        censurados=sum(1 for c in casos if not c.fechou),
        mediana=mediana,
        limite=max(c.dias for c in casos),
    )


def resumir(curva: Curva | None, media_ingenua: float | None = None) -> dict | None:
    """O que se diz da curva, com o viés da conta antiga explicitado."""
    if curva is None:
        return None
    marcos = [{"dias": d, "fechado": curva.ate(d)} for d in MARCOS]
    resumo = {
        "n": curva.n,
        "fechados": curva.eventos,
        "em_aberto_ou_perdidos": curva.censurados,
        "mediana_dias": curva.mediana,
        "marcos": marcos,
        "curva": curva.pontos,
        "limite_dias": curva.limite,
        "media_ingenua": media_ingenua,
    }
    resumo["leitura"] = _ler(resumo)
    return resumo


def _ler(resumo: dict) -> str:
    partes = []
    if resumo["mediana_dias"] is not None:
        partes.append(
            f"Metade dos fechamentos acontece até {resumo['mediana_dias']:.0f} dias."
        )
    else:
        partes.append(
            "Menos da metade dos negócios fechou dentro do período observado, então não há "
            "mediana: o ciclo é mais longo que a janela medida."
        )
    trinta = next((m["fechado"] for m in resumo["marcos"] if m["dias"] == 30), None)
    if trinta is not None:
        partes.append(f"Em 30 dias, {trinta:.0%} já fecharam.")
    if resumo["em_aberto_ou_perdidos"]:
        partes.append(
            f"A conta considera os {resumo['em_aberto_ou_perdidos']} negócios ainda sem "
            "fechamento, que a média simples ignorava."
        )
    return " ".join(partes)
