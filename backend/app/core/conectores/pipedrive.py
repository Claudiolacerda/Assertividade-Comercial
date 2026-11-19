"""Pipedrive.

Escrito sobre o contrato da API v1 (`/api/v1/deals`), que está no ar há anos e
é o que a maior parte das contas usa. A v2 existe e pagina por cursor; quando
for preciso, ela entra como outra classe e não mexe nesta — o que muda é o
endereço e a forma de virar a página, não o mapa de campos.

AVISO HONESTO: os nomes de campo abaixo vêm do contrato conhecido da v1, e a
documentação oficial não pôde ser consultada da máquina onde este arquivo foi
escrito. O primeiro teste com token de verdade confirma ou corrige — e, se
corrigir, o conserto é só nas constantes daqui, porque nada fora deste arquivo
conhece o formato do Pipedrive.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import Conector, ErroDeConexao, Importacao, Periodo, linha_vazia
from .http import MAXIMO_LINHAS, MAXIMO_PAGINAS, Sessao, no_caminho

TAMANHO_PAGINA = 100


class ConectorPipedrive(Conector):
    nome = "pipedrive"
    rotulo = "Pipedrive"
    ajuda = (
        "O token está em Configurações pessoais › API, dentro da sua conta Pipedrive. "
        "O domínio é o que aparece no endereço quando você usa o sistema "
        "(ex.: suaempresa.pipedrive.com)."
    )

    @property
    def base(self) -> str:
        dominio = (self.config.get("dominio") or "").strip()
        if not dominio:
            raise ErroDeConexao(
                "Falta o domínio da sua conta Pipedrive (ex.: suaempresa.pipedrive.com)."
            )
        dominio = dominio.removeprefix("https://").removeprefix("http://").strip("/")
        if not dominio.endswith(".pipedrive.com"):
            # Endereço livre aqui seria um jeito de contornar a conferência de
            # rede do conector genérico por uma porta lateral.
            raise ErroDeConexao(
                f"{dominio!r} não é um domínio do Pipedrive. Ele termina em .pipedrive.com."
            )
        return f"https://{dominio}/api/v1"

    def buscar(self, periodo: Periodo) -> Importacao:
        sessao = Sessao()
        etapas = self._etapas(sessao)
        linhas: list[dict[str, Any]] = []
        avisos: list[str] = []
        corte = datetime.combine(periodo.de, datetime.min.time())
        pagina, bruto = 0, 0

        while pagina < MAXIMO_PAGINAS:
            corpo = sessao.obter(
                f"{self.base}/deals",
                {
                    "api_token": self.credencial.token,
                    "start": pagina * TAMANHO_PAGINA,
                    "limit": TAMANHO_PAGINA,
                    # Mais recente primeiro: permite parar assim que a página
                    # inteira for anterior ao período, em vez de varrer o
                    # histórico completo da conta a cada importação.
                    "sort": "update_time DESC",
                },
            ).corpo
            itens = corpo.get("data") or []
            if not isinstance(itens, list):
                raise ErroDeConexao("A resposta do Pipedrive não trouxe a lista de negócios.")
            bruto += len(itens)
            for item in itens:
                linhas.append(self._linha(item, etapas))
            pagina += 1

            if not itens:
                break
            if len(linhas) >= MAXIMO_LINHAS:
                avisos.append(f"Parei em {MAXIMO_LINHAS} negócios. Importe em períodos menores.")
                break
            if all(self._antes(i.get("update_time"), corte) for i in itens):
                break
            if not no_caminho(corpo, "additional_data.pagination.more_items_in_collection"):
                break
        else:
            avisos.append(f"Parei em {MAXIMO_PAGINAS} páginas.")

        return Importacao(linhas=linhas, paginas=pagina, total_bruto=bruto, avisos=avisos)

    # ---------------------------------------------------------------- partes
    def _etapas(self, sessao: Sessao) -> dict[int, str]:
        """id da etapa -> nome. O negócio só traz o id.

        Sem isto a coluna Etapa sairia "7", e "7" não diz a ninguém em que pé
        está a negociação. Falha aqui não derruba a importação: o nome da
        etapa é um detalhe, o desfecho vem no campo `status`.
        """
        try:
            corpo = sessao.obter(f"{self.base}/stages", {"api_token": self.credencial.token}).corpo
        except ErroDeConexao:
            return {}
        return {
            e["id"]: e.get("name", "")
            for e in (corpo.get("data") or [])
            if isinstance(e, dict) and "id" in e
        }

    @staticmethod
    def _antes(carimbo: Any, corte: datetime) -> bool:
        if not carimbo:
            return False  # sem data não dá para afirmar que é velho; melhor seguir lendo
        try:
            return datetime.fromisoformat(str(carimbo).replace("Z", "+00:00")).replace(
                tzinfo=None
            ) < corte
        except ValueError:
            return False

    @staticmethod
    def _linha(item: dict[str, Any], etapas: dict[int, str]) -> dict[str, Any]:
        linha = linha_vazia()
        # `title` é o nome do negócio, que é o que o vendedor escreve e o que a
        # pessoa reconhece. Organização e contato entram só quando ele falta.
        linha["Cliente"] = (
            item.get("title") or item.get("org_name") or item.get("person_name") or ""
        )
        # "won" / "lost" / "open" são classificados pelas regras de status que
        # já existem no motor — não traduzo aqui, para a planilha guardar o que
        # o CRM de fato disse.
        linha["Status"] = item.get("status")
        linha["Etapa"] = etapas.get(item.get("stage_id"))
        linha["Responsável"] = no_caminho(item, "user_id.name") or item.get("owner_name")
        linha["Valor"] = item.get("value")
        # "Data da reunião" fica vazia de propósito: um negócio do Pipedrive não
        # tem data de reunião, tem data de criação e de fechamento. O motor já
        # sabe situar o mês pela data de entrada do lead quando a da reunião
        # falta, e avisa que fez isso.
        linha["Data do lead"] = _data(item.get("add_time"))
        linha["Data de fechamento"] = _data(
            item.get("won_time") or item.get("lost_time") or item.get("close_time")
        )
        linha["Motivo da perda"] = item.get("lost_reason")
        linha["ID no CRM"] = item.get("id")
        return linha


def _data(carimbo: Any) -> str | None:
    """"2026-09-04 15:00:00" -> "2026-09-04". A hora não entra em nenhuma conta."""
    if not carimbo:
        return None
    texto = str(carimbo)
    return texto.replace("T", " ").split(" ")[0] or None
