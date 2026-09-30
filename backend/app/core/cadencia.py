"""Fluxos de cadência comercial.

Um fluxo é um grafo: etapas (nós) ligadas por setas. O usuário desenha no canvas,
mas o valor não está em desenhar — está em o Neriah *sugerir* o desenho a partir
do que ele já sabe da operação. Uma cadência montada sobre as objeções reais
("9 clientes travaram em preço") vale mais que qualquer template genérico.
"""

from __future__ import annotations

from typing import Any

# Canais de contato de uma etapa. O front usa isto para cor e ícone.
CANAIS = ["whatsapp", "ligacao", "email", "reuniao", "espera", "condicao", "nota"]

MODELOS: dict[str, dict[str, Any]] = {
    "padrao": {
        "nome": "Cadência padrão — 7 dias",
        "descricao": "O básico bem feito: cinco toques em uma semana, sem sumir e sem irritar.",
        "etapas": [
            ("whatsapp", "Contato imediato", 0, "Oi {nome}! Vi que você pediu informação sobre {servico}. Consigo te explicar em 10 minutos — prefere hoje à tarde ou amanhã de manhã?"),
            ("espera", "Aguardar resposta", 1, "Se respondeu, siga para a reunião. Se não, continue a cadência."),
            ("ligacao", "Ligação", 1, "Ligar no início da tarde. Se não atender, mandar áudio curto se apresentando."),
            ("whatsapp", "Prova de valor", 3, "Enviar um caso parecido com o dele, com número real. Sem pedir resposta."),
            ("whatsapp", "Última tentativa", 7, "{nome}, vou parar de te escrever para não incomodar. Se mudar de ideia, é só chamar. Deixo meu contato aqui."),
        ],
    },
    "preco": {
        "nome": "Quebra de objeção — preço",
        "descricao": "Para quem achou caro: reancorar no custo de não resolver, não no desconto.",
        "etapas": [
            ("nota", "Objeção registrada", 0, "Cliente sinalizou preço na reunião. Não oferecer desconto no primeiro toque."),
            ("whatsapp", "Reancorar valor", 1, "{nome}, pensei no que conversamos. Quanto te custa hoje continuar do jeito que está? Te mando uma conta rápida."),
            ("email", "Comparativo por escrito", 2, "Enviar comparativo: custo do serviço x custo do problema em 12 meses."),
            ("ligacao", "Conversa de decisão", 4, "Perguntar o que falta para ser um sim. Ouvir mais do que falar."),
            ("condicao", "Fechou?", 6, "Sim → onboarding. Não → cadência de nutrição longa."),
        ],
    },
    "conjuge": {
        "nome": "Decisor oculto",
        "descricao": "Quando a decisão depende de cônjuge ou sócio que não estava na reunião.",
        "etapas": [
            ("whatsapp", "Material para levar", 0, "{nome}, separei um resumo de uma página para você mostrar ao {decisor}. Fica mais fácil que explicar de cabeça."),
            ("espera", "Tempo de conversa", 2, "Dar espaço para a conversa acontecer."),
            ("whatsapp", "Convite para os dois", 3, "Faz sentido uma call rápida com vocês dois? 15 minutos, tiro as dúvidas dele na hora."),
            ("reuniao", "Reunião com o decisor", 5, "Reapresentar o essencial. Quem decide precisa ouvir de você, não de terceiros."),
        ],
    },
    "recuperacao": {
        "nome": "Recuperar parado",
        "descricao": "Oportunidade sem movimento há semanas — reabrir sem parecer cobrança.",
        "etapas": [
            ("whatsapp", "Reabrir conversa", 0, "{nome}, tudo bem? Passando para saber se o assunto ainda está de pé ou se posso encerrar por aqui."),
            ("espera", "Aguardar", 3, "A pergunta de encerramento costuma gerar resposta. Dar tempo."),
            ("ligacao", "Último contato", 5, "Ligação curta. Objetivo é só um sim ou um não claro."),
            ("condicao", "Vale seguir?", 6, "Sem resposta após este ponto → marcar como perdido e liberar o funil."),
        ],
    },
}

# Layout do canvas: as etapas nascem organizadas, e não empilhadas na origem.
LARGURA_COLUNA = 260
ALTURA_LINHA = 150
POR_COLUNA = 4


def _posicao(indice: int) -> dict[str, float]:
    coluna, linha = divmod(indice, POR_COLUNA)
    return {"x": 80 + coluna * LARGURA_COLUNA, "y": 60 + linha * ALTURA_LINHA}


def montar_fluxo(etapas: list[tuple[str, str, int, str]]) -> dict[str, Any]:
    """Converte a lista de etapas em grafo com nós e ligações em sequência."""
    nos = []
    for i, (canal, titulo, dia, texto) in enumerate(etapas):
        nos.append(
            {
                "id": f"n{i + 1}",
                "type": "etapa",
                "position": _posicao(i),
                "data": {"canal": canal, "titulo": titulo, "dia": dia, "texto": texto},
            }
        )
    ligacoes = [
        {"id": f"e{i}", "source": f"n{i}", "target": f"n{i + 1}"} for i in range(1, len(nos))
    ]
    return {"nos": nos, "ligacoes": ligacoes}


def modelo(chave: str) -> dict[str, Any]:
    m = MODELOS[chave]
    return {"nome": m["nome"], "descricao": m["descricao"], "fluxo": montar_fluxo(m["etapas"])}


def sugerir_de_analise(resultado: dict[str, Any]) -> dict[str, Any]:
    """Monta uma cadência a partir do que a análise encontrou.

    É o que separa isto de um quadro branco: o fluxo nasce das objeções que a
    equipe registrou, das oportunidades paradas e dos clientes quentes — não de
    um modelo que serve para qualquer negócio.
    """
    tabelas = resultado.get("tabelas") or {}
    sinais = {s.get("Sinal na observação"): s.get("Clientes", 0) for s in tabelas.get("sinais_resumo") or []}
    pipeline = tabelas.get("pipeline") or []
    quentes = [p for p in pipeline if "Quente" in str(p.get("Temperatura", ""))]
    paradas = [p for p in pipeline if "sem atualização" in str(p.get("Alerta", ""))]

    etapas: list[tuple[str, str, int, str]] = []
    motivos: list[str] = []

    if quentes:
        nomes = ", ".join(str(p.get("Cliente")) for p in quentes[:5])
        etapas.append(
            ("nota", f"{len(quentes)} clientes quentes", 0,
             f"Prioridade da semana: {nomes}. Estes já demonstraram intenção — o toque aqui é de fechamento, não de nutrição.")
        )
        etapas.append(
            ("ligacao", "Ligar para os quentes", 0,
             "Ligação no mesmo dia. Objetivo único: marcar a assinatura, não reapresentar a proposta.")
        )
        motivos.append(f"{len(quentes)} oportunidade(s) quentes no pipeline")

    preco = sinais.get("Objeção: preço/orçamento", 0)
    if preco:
        etapas.append(
            ("whatsapp", "Reancorar valor (preço)", 1,
             f"{preco} clientes travaram em preço. Não abrir desconto: mostrar o custo de continuar como está. "
             "Mensagem: \"{nome}, quanto te custa hoje continuar do jeito que está? Te mando uma conta rápida.\"")
        )
        etapas.append(
            ("email", "Comparativo por escrito", 2,
             "Custo do serviço x custo do problema em 12 meses. Documento de uma página, para ele reler sozinho.")
        )
        motivos.append(f"preço foi objeção de {preco} cliente(s)")

    conjuge = sinais.get("Decide com cônjuge/sócio", 0)
    if conjuge:
        etapas.append(
            ("whatsapp", "Material para o decisor", 2,
             f"{conjuge} decisões dependem de outra pessoa que não estava na reunião. "
             "Enviar resumo de uma página que ele consiga mostrar, em vez de explicar de cabeça.")
        )
        etapas.append(
            ("reuniao", "Call com os dois", 4,
             "15 minutos com o casal ou com os sócios. Quem decide precisa ouvir de você.")
        )
        motivos.append(f"{conjuge} cliente(s) dependem de um decisor oculto")

    concorrencia = sinais.get("Comparando concorrentes", 0)
    if concorrencia:
        etapas.append(
            ("whatsapp", "Diferencial, não preço", 3,
             f"{concorrencia} clientes estão comparando. Mandar o que só você faz — evitar guerra de tabela.")
        )
        motivos.append(f"{concorrencia} cliente(s) comparando concorrentes")

    if paradas:
        etapas.append(
            ("whatsapp", f"Reabrir {len(paradas)} paradas", 5,
             "\"{nome}, o assunto ainda está de pé ou posso encerrar por aqui?\" — a pergunta de encerramento "
             "costuma destravar resposta.")
        )
        etapas.append(
            ("condicao", "Sem resposta?", 7,
             "Sem retorno depois deste ponto: marcar como perdido. Funil limpo vale mais que funil cheio.")
        )
        motivos.append(f"{len(paradas)} oportunidade(s) sem movimento")

    if not etapas:  # análise sem sinal suficiente: entrega o básico bem feito
        return {
            **modelo("padrao"),
            "nome": "Cadência sugerida",
            "descricao": "A análise não trouxe objeções suficientes para personalizar. Este é o padrão de 7 dias.",
            "origem": [],
        }

    # As etapas são acrescentadas por tema, então os dias saem fora de ordem.
    # Ordenar antes de montar faz o desenho seguir a linha do tempo.
    etapas.sort(key=lambda e: e[2])
    return {
        "nome": "Cadência sugerida pela análise",
        "descricao": "Montada a partir de: " + "; ".join(motivos) + ".",
        "fluxo": montar_fluxo(etapas),
        "origem": motivos,
    }
