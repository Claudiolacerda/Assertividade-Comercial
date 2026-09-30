"""Envio de mensagens no WhatsApp.

Dois provedores, escolhidos por variável de ambiente:

* **evolution** — a Evolution API, que muita agência já roda em Docker. Não exige
  aprovação da Meta e envia texto livre.
* **cloud** — a API oficial da Meta (WhatsApp Cloud API). Exige verificação de
  negócio, e mensagem iniciada por você precisa de modelo aprovado — por isso só
  vale a pena quando o volume justifica.

Sem nenhum configurado, o sistema não fica sem saída: a tela oferece copiar o
texto ou abrir o WhatsApp Web com a mensagem pronta, que funciona desde o
primeiro dia e sem credencial nenhuma.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from .config import settings


class ErroEnvio(Exception):
    """Falha que o usuário consegue entender e agir."""


@dataclass
class Envio:
    sucesso: bool
    provedor: str
    detalhe: str


def normalizar_numero(numero: str) -> str:
    """Deixa só dígitos e garante o DDI do Brasil.

    Aceita '(83) 99853-9248', '83998539248', '+55 83 99853-9248'.
    """
    limpo = re.sub(r"\D", "", numero or "")
    if not limpo:
        raise ErroEnvio("Número de WhatsApp vazio.")
    if limpo.startswith("55") and len(limpo) >= 12:
        pass
    elif len(limpo) in (10, 11):  # DDD + número, sem DDI
        limpo = "55" + limpo
    elif not limpo.startswith("55"):
        raise ErroEnvio(
            f"Número '{numero}' não parece válido. Use DDD + número, por exemplo (83) 99853-9248."
        )
    if not 12 <= len(limpo) <= 13:
        raise ErroEnvio(f"Número '{numero}' tem {len(limpo)} dígitos — esperado 12 ou 13 com o DDI.")
    return limpo


def link_whatsapp(numero: str | None, texto: str) -> str:
    """Link wa.me com a mensagem pronta — o caminho que sempre funciona."""
    from urllib.parse import quote

    destino = ""
    if numero:
        try:
            destino = normalizar_numero(numero)
        except ErroEnvio:
            destino = ""
    return f"https://wa.me/{destino}?text={quote(texto)}"


def provedor_configurado() -> str:
    """'evolution', 'cloud' ou '' quando o envio automático não está ligado."""
    p = (settings.zap_provedor or "").strip().lower()
    if p == "evolution" and settings.zap_evolution_url and settings.zap_evolution_token:
        return "evolution"
    if p == "cloud" and settings.zap_cloud_token and settings.zap_cloud_phone_id:
        return "cloud"
    return ""


def _enviar_evolution(numero: str, texto: str) -> Envio:
    base = settings.zap_evolution_url.rstrip("/")
    instancia = settings.zap_evolution_instancia or "default"
    url = f"{base}/message/sendText/{instancia}"
    try:
        resp = httpx.post(
            url,
            headers={"apikey": settings.zap_evolution_token, "Content-Type": "application/json"},
            json={"number": numero, "text": texto},
            timeout=30,
        )
    except httpx.HTTPError as e:
        raise ErroEnvio(f"Não consegui falar com a Evolution API em {base}: {e}") from e
    if resp.status_code >= 400:
        raise ErroEnvio(f"A Evolution API recusou o envio ({resp.status_code}): {resp.text[:200]}")
    return Envio(True, "evolution", f"Enviado para {numero}.")


def _enviar_cloud(numero: str, texto: str) -> Envio:
    url = f"https://graph.facebook.com/v21.0/{settings.zap_cloud_phone_id}/messages"
    try:
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.zap_cloud_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "text",
                "text": {"preview_url": False, "body": texto},
            },
            timeout=30,
        )
    except httpx.HTTPError as e:
        raise ErroEnvio(f"Não consegui falar com a API da Meta: {e}") from e
    if resp.status_code >= 400:
        # o caso mais comum: fora da janela de 24h, que exige modelo aprovado
        raise ErroEnvio(
            f"A Meta recusou o envio ({resp.status_code}): {resp.text[:250]}. "
            "Fora da janela de 24 horas, a Cloud API só entrega mensagem com modelo aprovado."
        )
    return Envio(True, "cloud", f"Enviado para {numero}.")


def enviar(numero: str, texto: str) -> Envio:
    """Envia pelo provedor configurado. Levanta ErroEnvio com motivo legível."""
    provedor = provedor_configurado()
    if not provedor:
        raise ErroEnvio(
            "Envio automático não configurado. Use 'Abrir no WhatsApp' para mandar agora, "
            "ou configure ZAP_PROVEDOR no servidor."
        )
    destino = normalizar_numero(numero)
    return _enviar_evolution(destino, texto) if provedor == "evolution" else _enviar_cloud(destino, texto)
