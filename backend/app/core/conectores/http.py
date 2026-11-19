"""O pedaço que fala com a rede: endereço conferido, repetição e paginação.

Está separado dos conectores porque é onde moram os erros que não são de
nenhum CRM em particular — token errado, limite de requisições, página que
nunca acaba, endereço que aponta para dentro da própria máquina.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from .base import ErroDeConexao

TEMPO_LIMITE = 30.0
TENTATIVAS = 4
MAXIMO_PAGINAS = 200
MAXIMO_LINHAS = 50_000


def conferir_url(url: str) -> str:
    """Recusa endereço que não seja HTTPS público.

    O conector genérico aceita a URL que o cliente digitar, e é isso que o
    torna útil para um CRM cuja API ninguém documentou. Mas uma URL livre, num
    sistema que roda no servidor, é também o caminho clássico para fazer o
    servidor buscar coisa que só ele alcança: o endereço de metadados da
    nuvem, um banco na rede interna, o próprio localhost. Por isso o endereço
    é resolvido ANTES e recusado se cair em faixa privada.

    Isto não é blindagem completa: um domínio pode responder um IP público
    agora e um privado na hora da conexão. Para fechar isso de vez seria
    preciso conectar no IP já conferido, o que o httpx não oferece de forma
    direta. Fica registrado como o buraco conhecido deste controle.
    """
    partes = urlparse(url)
    if partes.scheme != "https":
        raise ErroDeConexao(
            "O endereço precisa começar com https:// — não mandamos token de cliente por "
            "conexão aberta."
        )
    if not partes.hostname:
        raise ErroDeConexao(f"Endereço sem servidor: {url!r}")

    try:
        achados = socket.getaddrinfo(partes.hostname, partes.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ErroDeConexao(f"Não consegui resolver o endereço {partes.hostname!r}: {e}") from e

    for *_, sockaddr in achados:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ErroDeConexao(
                f"O endereço {partes.hostname!r} aponta para a rede interna ({ip}). "
                "Só aceitamos endereços públicos de API."
            )
    return url


@dataclass
class Resposta:
    corpo: Any
    status: int


class Sessao:
    """Cliente HTTP com os limites que uma importação precisa ter."""

    def __init__(self, cabecalhos: dict[str, str] | None = None) -> None:
        self.cabecalhos = {"Accept": "application/json", **(cabecalhos or {})}
        # Sem User-Agent com nome de cliente: o que sai daqui vai para o
        # servidor de terceiro, e o nome da empresa do usuário não é dele.
        self.cabecalhos.setdefault("User-Agent", "Neriah-Data/1.0")

    def obter(self, url: str, parametros: dict[str, Any] | None = None) -> Resposta:
        conferir_url(url)
        ultimo = ""
        for tentativa in range(TENTATIVAS):
            try:
                with httpx.Client(timeout=TEMPO_LIMITE, follow_redirects=False) as cliente:
                    r = cliente.get(url, params=parametros, headers=self.cabecalhos)
            except httpx.TimeoutException:
                ultimo = f"o servidor não respondeu em {TEMPO_LIMITE:.0f}s"
            except httpx.HTTPError as e:
                ultimo = f"falha de rede ({type(e).__name__})"
            else:
                if r.status_code in (401, 403):
                    raise ErroDeConexao(
                        "O CRM recusou a credencial (HTTP "
                        f"{r.status_code}). Confira o token e a permissão de leitura dele."
                    )
                if r.status_code == 404:
                    raise ErroDeConexao(
                        f"O endereço respondeu 404. Confira a URL: {url}"
                    )
                if r.status_code == 429 or r.status_code >= 500:
                    ultimo = f"HTTP {r.status_code}"
                    self._esperar(r, tentativa)
                    continue
                if r.status_code >= 400:
                    raise ErroDeConexao(f"O CRM respondeu HTTP {r.status_code}: {r.text[:300]}")
                try:
                    return Resposta(corpo=r.json(), status=r.status_code)
                except ValueError as e:
                    raise ErroDeConexao(
                        "A resposta não é JSON. O endereço devolveu "
                        f"{r.headers.get('content-type', 'tipo desconhecido')}."
                    ) from e
            # Só chega aqui por timeout ou falha de rede: espera e tenta de novo.
            time.sleep(min(2**tentativa, 8))
        raise ErroDeConexao(f"Não consegui falar com o CRM depois de {TENTATIVAS} tentativas: {ultimo}.")

    @staticmethod
    def _esperar(resposta: httpx.Response, tentativa: int) -> None:
        """Respeita o Retry-After quando ele vem, e dobra a espera quando não vem."""
        cabecalho = resposta.headers.get("Retry-After", "")
        try:
            segundos = float(cabecalho)
        except ValueError:
            segundos = float(min(2**tentativa, 8))
        time.sleep(min(segundos, 30.0))


def no_caminho(corpo: Any, caminho: str, padrao: Any = None) -> Any:
    """Lê "dados.itens" dentro do JSON, aceitando índice de lista em "itens.0.nome".

    Caminho vazio devolve o corpo inteiro: é o caso do CRM que responde uma
    lista pura, sem envelope.
    """
    if not caminho:
        return corpo
    atual = corpo
    for pedaco in caminho.split("."):
        if isinstance(atual, dict):
            if pedaco not in atual:
                return padrao
            atual = atual[pedaco]
        elif isinstance(atual, list):
            try:
                atual = atual[int(pedaco)]
            except (ValueError, IndexError):
                return padrao
        else:
            return padrao
    return atual
