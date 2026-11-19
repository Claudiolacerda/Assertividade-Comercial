"""Conector para qualquer API REST que devolva JSON.

Existe por um motivo concreto: a maior parte dos CRMs que os clientes usam no
Brasil não tem documentação pública. Esperar eu escrever um conector dedicado
para cada um significa nunca conectar nenhum. Aqui o cliente descreve a API no
formulário — endereço, como autentica, onde está a lista, como vira a página e
qual campo do JSON é o nome do cliente — e o Neriah lê.

Quando um CRM se repetir entre clientes, ele ganha um conector dedicado com os
campos certos e deixa de precisar deste.
"""

from __future__ import annotations

from typing import Any

from .base import (
    COLUNAS_SAIDA,
    Conector,
    ErroDeConexao,
    Importacao,
    Periodo,
    linha_vazia,
)
from .http import MAXIMO_LINHAS, MAXIMO_PAGINAS, Sessao, no_caminho

TIPOS_DE_AUTENTICACAO = ("bearer", "cabecalho", "parametro", "nenhuma")
TIPOS_DE_PAGINACAO = ("nenhuma", "deslocamento", "pagina", "cursor")


class ConectorGenerico(Conector):
    nome = "generico"
    rotulo = "API REST (configurável)"
    ajuda = (
        "Para um CRM sem conector pronto. Você precisa do endereço do endpoint que lista "
        "os negócios, do token, e de saber em que campo do JSON está cada informação — "
        "o suporte do CRM costuma responder isso."
    )

    def buscar(self, periodo: Periodo) -> Importacao:
        cfg = self.config
        url = cfg.get("url") or ""
        if not url:
            raise ErroDeConexao("Falta o endereço do endpoint na configuração da conexão.")

        campos: dict[str, str] = cfg.get("campos") or {}
        if not campos.get("Cliente"):
            raise ErroDeConexao(
                "Falta dizer qual campo do JSON é o nome do cliente. Sem ele, o Neriah não "
                "tem o que contar."
            )
        desconhecidos = sorted(set(campos) - set(COLUNAS_SAIDA))
        if desconhecidos:
            raise ErroDeConexao(
                "Estas colunas não existem no Neriah: " + ", ".join(desconhecidos) +
                ". As que existem são: " + ", ".join(COLUNAS_SAIDA) + "."
            )

        sessao = Sessao(self._cabecalhos())
        parametros_base = {**(cfg.get("extras") or {}), **self._periodo(periodo)}
        parametros_base.update(self._autenticacao_em_parametro())

        linhas: list[dict[str, Any]] = []
        avisos: list[str] = []
        paginacao = cfg.get("paginacao") or {}
        tipo = paginacao.get("tipo", "nenhuma")
        if tipo not in TIPOS_DE_PAGINACAO:
            raise ErroDeConexao(f"Tipo de paginação desconhecido: {tipo!r}.")
        tamanho = int(paginacao.get("tamanho") or 100)
        param_tamanho = paginacao.get("param_tamanho") or ""
        param = paginacao.get("param") or ""

        pagina, cursor, bruto = 0, None, 0
        while pagina < MAXIMO_PAGINAS:
            parametros = dict(parametros_base)
            if param_tamanho:
                parametros[param_tamanho] = tamanho
            if tipo == "deslocamento" and param:
                parametros[param] = pagina * tamanho
            elif tipo == "pagina" and param:
                parametros[param] = pagina + int(paginacao.get("primeira", 1))
            elif tipo == "cursor" and param and cursor:
                parametros[param] = cursor

            corpo = sessao.obter(url, parametros).corpo
            itens = no_caminho(corpo, cfg.get("itens") or "", [])
            if itens is None:
                itens = []
            if not isinstance(itens, list):
                raise ErroDeConexao(
                    f"O caminho {cfg.get('itens')!r} não aponta para uma lista no JSON — "
                    f"achei {type(itens).__name__}."
                )
            bruto += len(itens)
            for item in itens:
                linhas.append(self._linha(item, campos))
            pagina += 1

            if tipo == "nenhuma" or not itens:
                break
            if len(linhas) >= MAXIMO_LINHAS:
                avisos.append(
                    f"Parei em {MAXIMO_LINHAS} negócios. Reduza o período e importe em partes."
                )
                break
            if tipo == "cursor":
                cursor = no_caminho(corpo, paginacao.get("caminho_proximo") or "")
                if not cursor:
                    break
            else:
                caminho_tem_mais = paginacao.get("caminho_tem_mais") or ""
                if caminho_tem_mais:
                    if not no_caminho(corpo, caminho_tem_mais):
                        break
                elif len(itens) < tamanho:
                    # Sem campo que diga "tem mais", a última página é a que
                    # veio menor que o tamanho pedido. Um CRM que devolva
                    # exatamente `tamanho` na última faz uma requisição a mais,
                    # que volta vazia e encerra no `if not itens` acima.
                    break
        else:
            avisos.append(
                f"Parei em {MAXIMO_PAGINAS} páginas. Se faltou negócio, importe em períodos menores."
            )

        return Importacao(linhas=linhas, paginas=pagina, total_bruto=bruto, avisos=avisos)

    # ---------------------------------------------------------------- partes
    def _cabecalhos(self) -> dict[str, str]:
        auth = self.config.get("auth") or {}
        tipo = auth.get("tipo", "bearer")
        if tipo not in TIPOS_DE_AUTENTICACAO:
            raise ErroDeConexao(f"Tipo de autenticação desconhecido: {tipo!r}.")
        if tipo == "bearer":
            return {"Authorization": f"Bearer {self.credencial.token}"}
        if tipo == "cabecalho":
            nome = auth.get("nome") or "X-Api-Key"
            prefixo = auth.get("prefixo") or ""
            return {nome: f"{prefixo} {self.credencial.token}".strip()}
        return {}

    def _autenticacao_em_parametro(self) -> dict[str, str]:
        auth = self.config.get("auth") or {}
        if auth.get("tipo") == "parametro":
            return {auth.get("nome") or "api_token": self.credencial.token}
        return {}

    def _periodo(self, periodo: Periodo) -> dict[str, str]:
        """Converte a janela nos parâmetros que a API espera, se ela aceitar algum.

        CRM que não filtra por data devolve tudo, e o recorte do mês acontece
        depois, no motor — que já sabe fazer isso com planilha. Então a
        ausência desta configuração não é erro.
        """
        cfg = self.config.get("periodo") or {}
        formato = cfg.get("formato") or "%Y-%m-%d"
        saida: dict[str, str] = {}
        if cfg.get("param_de"):
            saida[cfg["param_de"]] = periodo.de.strftime(formato)
        if cfg.get("param_ate"):
            saida[cfg["param_ate"]] = periodo.ate.strftime(formato)
        return saida

    @staticmethod
    def _linha(item: Any, campos: dict[str, str]) -> dict[str, Any]:
        linha = linha_vazia()
        if not isinstance(item, dict):
            return linha
        for coluna, caminho in campos.items():
            valor = no_caminho(item, caminho)
            # Objeto inteiro no lugar de um valor é o engano mais comum ao
            # preencher o mapa ("responsavel" em vez de "responsavel.nome").
            # Guardar o dicionário cru faria a coluna virar texto de Python na
            # planilha; melhor um campo reconhecível.
            if isinstance(valor, dict):
                valor = valor.get("name") or valor.get("nome") or valor.get("label") or None
            elif isinstance(valor, list):
                valor = ", ".join(str(v) for v in valor if v is not None) or None
            linha[coluna] = valor
        return linha
