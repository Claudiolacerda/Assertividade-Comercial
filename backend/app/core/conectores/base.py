"""O contrato que todo conector de CRM cumpre.

A decisão que sustenta este pacote: um conector NÃO fala com o motor de
análise. Ele produz as mesmas linhas que uma planilha produziria, com os
mesmos cabeçalhos em português que o mapa de apelidos já reconhece, e o
arquivo resultante entra pelo caminho de sempre.

Isso custa um CSV a mais no disco e paga três coisas:

1. O motor não ganha um caminho novo. Nenhum número muda por ter vindo da API
   em vez da planilha, e a suíte que crava os KPIs continua valendo para os dois.
2. Fica a prova. Quando o cliente perguntar "de onde saiu esse 12?", existe um
   arquivo para abrir, com o que o CRM devolveu naquele dia. Uma integração que
   lê e descarta não se defende depois.
3. Reprocessar continua funcionando: a análise aponta para arquivos, e os
   arquivos existem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any

# As colunas que um conector pode preencher, na ordem em que saem no CSV.
#
# Cada nome aqui é, de propósito, um apelido que `config_analise.COLUNAS_REUNIOES`
# já conhece. Não existe tradução especial para dado vindo de API: o arquivo que
# o conector escreve é indistinguível de uma planilha bem preenchida, e é por
# isso que ele não precisa de código próprio no motor.
COLUNAS_SAIDA: list[str] = [
    "Cliente",
    "Status",
    "Etapa",
    "Responsável",
    "Valor",
    "Origem",
    "Campanha",
    "Produto",
    "Data do lead",
    "Data da reunião",
    "Data de fechamento",
    "Motivo da perda",
    "Observações",
    "ID no CRM",
]

# "ID no CRM" não está no mapa de apelidos e é de propósito: ele não vira campo
# do sistema, fica na planilha para a pessoa conseguir achar o negócio lá no CRM
# quando discordar do número. `padronizar` o lista como "(não usada)", que é a
# verdade.


@dataclass
class Credencial:
    """O segredo do cliente, já decifrado, em memória e só aqui."""

    token: str = ""
    usuario: str = ""
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class Periodo:
    """Janela pedida ao CRM. Inclusiva nos dois extremos."""

    de: date
    ate: date

    def __post_init__(self) -> None:
        if self.de > self.ate:
            raise ValueError("O início do período é depois do fim.")


@dataclass
class Importacao:
    """O que voltou de uma busca, com o que for preciso para explicar depois."""

    linhas: list[dict[str, Any]]
    paginas: int = 0
    total_bruto: int = 0
    avisos: list[str] = field(default_factory=list)

    @property
    def quantidade(self) -> int:
        return len(self.linhas)


class ErroDeConexao(Exception):
    """Falha que o usuário resolve: token errado, endpoint fora do ar, campo faltando.

    Separada de `Exception` nua para o roteador poder devolver 422 com a
    mensagem em vez de um 500 que não diz nada — o mesmo tratamento que
    `ErroDeAnalise` já recebe no caminho da planilha.
    """


class Conector(ABC):
    """Um CRM. Recebe credencial e configuração, devolve linhas."""

    #: identificador curto, usado na API e no banco
    nome: str = ""
    #: como aparece na tela
    rotulo: str = ""
    #: o que o cliente precisa ter em mãos, mostrado no formulário
    ajuda: str = ""

    def __init__(self, credencial: Credencial, config: dict[str, Any] | None = None) -> None:
        self.credencial = credencial
        self.config = config or {}

    @abstractmethod
    def buscar(self, periodo: Periodo) -> Importacao:
        """Traz os negócios do período, já nas colunas de `COLUNAS_SAIDA`."""

    def testar(self) -> str:
        """Confere a credencial e devolve uma frase para a tela.

        O padrão é buscar um período curto: se o token está errado, o CRM
        responde 401 e o usuário descobre agora, e não daqui a um mês quando
        a importação automática falhar calada.
        """
        hoje = date.today()
        resultado = self.buscar(Periodo(de=hoje.replace(day=1), ate=hoje))
        return f"Conexão funcionando: {resultado.quantidade} negócio(s) no mês corrente."


def linha_vazia() -> dict[str, Any]:
    """Uma linha com todas as colunas, para o CSV sair retangular.

    Sem isso, o negócio sem motivo de perda deixava a coluna de fora e o
    `pandas` alinhava a linha seguinte uma casa à esquerda.
    """
    return {c: None for c in COLUNAS_SAIDA}
