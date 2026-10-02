"""JEV — a leitura do mês, escrita por um modelo de linguagem.

O JET calcula. O JEV lê o que o JET calculou e escreve o diagnóstico daquele
mês. A fronteira entre os dois é dura e deliberada:

    Número vem de código. Palavra vem do modelo.

O produto vende "o CAC real" e "a assertividade de verdade". Um número que o
modelo tivesse calculado ou reescrito poderia estar sutilmente errado, e é em
cima dele que o cliente corta verba. Por isso o modelo recebe os números já
calculados e formatados, e o que se pede dele é interpretação: qual dos
problemas atacar primeiro, o que a combinação dos indicadores significa, para
onde mover orçamento. Se ele devolver um número que não está no payload, o
número não aparece em lugar nenhum da tela — a tela mostra os do JET.

**O que sai desta máquina.** Só agregado: contagens, taxas, nomes de campanha
(que são códigos, do tipo "[GT] [WPP] [VENDAS]") e as categorias de sinal, que
vêm de um vocabulário fixo no código. Nunca nome de cliente final, nunca o
texto livre das observações, nunca nome de quem fez a reunião. Essa promessa
não é uma intenção: `montar_payload` é a única porta de saída, e
`test_jev.py` monta o payload a partir da planilha real e falha se qualquer
nome ou observação aparecer nele.

O custo disso é real e vale ser dito: sem o texto livre, o JEV não conserta a
classificação de objeção, que hoje sai de palavras-chave e erra. Ele raciocina
sobre os números, que é o que sobra, e isso o JET sozinho não faz — o JET tem
uma frase pronta por indicador, e nenhuma frase pronta enxerga a interação
entre dois indicadores.

**O JEV é aditivo.** Sem chave de API, com a chave errada, com a rede fora ou
com o modelo recusando, a análise sai inteira do mesmo jeito, com o Score do
JET e um aviso de que a leitura não veio. Nenhum caminho deste módulo levanta
exceção para fora.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from .config_analise import SINAIS_OBSERVACAO

log = logging.getLogger(__name__)

MODELO = "claude-opus-5-5"

# Categorias de sinal: vocabulário fixo, definido no código, não texto do
# cliente. Sai como rótulo + contagem.
CATEGORIAS_SINAL = list(SINAIS_OBSERVACAO)

# KPIs que vão no payload. Lista explícita em vez de "tudo que existe": quem
# acrescentar um KPI ao pipeline tem de decidir conscientemente se ele sai
# desta máquina.
KPIS_ENVIADOS = [
    "inv", "imp", "clq", "leads", "ctr", "cpc", "cpm", "cpl",
    "ag", "real", "ns", "rem", "fut", "fec", "per", "neg", "sd",
    "agr", "comp", "assert", "win", "fag", "rec", "tm", "vneg",
    "agp", "realp", "fecp", "recp", "l2r", "l2c", "cpr", "cac", "roas", "roi",
]

# Colunas das tabelas de campanha que podem sair. Nome da campanha é código de
# mídia, não dado pessoal.
COLUNAS_CAMPANHA = [
    "Campanha", "Investimento (R$)", "Leads Meta", "Leads / resultados",
    "Reuniões agendadas", "Reuniões realizadas", "Fechados", "Perdidos",
    "CAC (R$)", "Custo por lead (R$)", "CTR no link (%)", "Lead → reunião (%)",
]


class PontoJev(BaseModel):
    titulo: str = Field(description="Frase curta, no imperativo, do que fazer.")
    porque: str = Field(description="Por que, citando os indicadores que sustentam isso.")
    indicadores: list[str] = Field(
        description="Rótulos dos indicadores do payload em que esta conclusão se apoia."
    )


class LeituraJev(BaseModel):
    """O que se pede ao modelo. Sem nenhum campo numérico, de propósito."""

    leitura: str = Field(
        description="Dois a quatro períodos sobre o que este mês foi, no geral. "
        "Português do Brasil, direto, sem jargão de consultoria e sem elogio vazio."
    )
    primeiro_passo: str = Field(
        description="A única coisa a fazer primeiro no mês que vem, e por quê."
    )
    pontos: list[PontoJev] = Field(
        description="De dois a quatro pontos de ação, do mais importante para o menos."
    )
    onde_mover_verba: str = Field(
        description="O que fazer com o orçamento entre as campanhas, com base nas notas "
        "delas. Se os dados não bastarem para dizer, diga isso em vez de inventar."
    )


INSTRUCAO = """\
Você é o JEV, o analista do Neriah Data. Recebe o resultado já calculado de um \
mês de operação comercial de um cliente que anuncia na Meta, e escreve a leitura \
desse mês para o dono do negócio ler.

Regras que não se quebram:

1. NÃO CALCULE NADA, nem em algarismo nem por extenso. Todos os números já vêm \
calculados e formatados no payload: use exatamente o campo "texto" de cada KPI. \
Nunca derive, some, divida ou arredonde um número novo, e nunca cite um número \
que não esteja no payload. A proibição vale para comparações em palavras: "um \
terço do mínimo", "o dobro do teto" e "metade da meta" são contas, e contas \
feitas de cabeça saem erradas. Para comparar, use "abaixo", "acima", "bem \
abaixo", "perto da meta". Se o que você quer dizer depende de uma conta que não \
está feita, diga a conclusão sem o número.

2. Não invente contexto. Você não sabe o ramo do cliente, o ticket, o tamanho da \
equipe nem o que aconteceu no mercado. Só sabe o que está no payload.

3. Quando um indicador está fora do cálculo do Score, isso está marcado com o \
motivo. Não trate ausência de dado como mau desempenho, e vice-versa.

4. O valor que você acrescenta é a INTERAÇÃO entre indicadores, que a régua fixa \
do Score não enxerga. Exemplos do tipo de raciocínio esperado: CAC no teto com \
assertividade boa significa que o problema é o custo da mídia, não a reunião; \
assertividade baixa com custo por lead bom significa o contrário; muita reunião \
sem desfecho registrado significa que a assertividade medida está pior do que a \
real. Procure o padrão deste mês, não repita esses exemplos.

5. Português do Brasil. Frases curtas. Sem "é importante ressaltar", sem \
"podemos observar", sem travessão. Fale como quem conhece a operação e tem \
pressa, não como relatório de consultoria.
"""


def montar_payload(res) -> dict[str, Any]:
    """A única porta de saída. Só agregado sai daqui.

    Tudo que é texto escrito pelo cliente ou nome de pessoa fica de fora por
    construção: as listas acima são de inclusão, não de exclusão, então um
    campo novo no pipeline não vaza sozinho — alguém tem de adicioná-lo aqui.
    """
    kpis = {
        chave: {
            "rotulo": k["rotulo"],
            "texto": k["texto"],
            "meta": k.get("meta_valor"),
            "meta_tipo": k.get("meta_tipo"),
            "dentro_da_meta": k.get("dentro_da_meta"),
        }
        for chave, k in res.kpis.items()
        if chave in KPIS_ENVIADOS
    }

    jet = res.jet or {}
    # Prefere a tabela que liga campanha a cliente fechado; cai na de mídia
    # quando a planilha de reuniões não tem a coluna Campanha.
    linhas = _linhas(res, "campanha_x_vendas") or _linhas(res, "meta_campanhas")
    campanhas = [
        {c: linha[c] for c in COLUNAS_CAMPANHA if c in linha} for linha in linhas[:25]
    ]

    sinais = _contagem_de_sinais(res)

    return {
        "mes": res.nome_mes,
        "planilha": {
            "tem_coluna_de_valor": bool(res.tem_valor),
            "tem_coluna_de_origem": bool(res.tem_origem),
            "liga_campanha_a_cliente": "campanha_x_vendas" in res.tabelas,
        },
        "kpis": kpis,
        "score": {
            "valor": jet.get("score"),
            "faixa": jet.get("faixa"),
            "pilares": jet.get("pilares", []),
            "metas_nao_preenchidas": jet.get("metas_ausentes", []),
        },
        "indicadores": [
            {k: i[k] for k in ("rotulo", "pilar", "atingimento", "pontuado", "motivo_fora", "custo")}
            for i in jet.get("indicadores", [])
        ],
        "campanhas": campanhas,
        "sinais_nas_observacoes": sinais,
    }


def _linhas(res, nome: str) -> list[dict[str, Any]]:
    df = res.tabelas.get(nome)
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


def _contagem_de_sinais(res) -> dict[str, int]:
    """Quantas observações caíram em cada categoria.

    A categoria é um rótulo fixo do código (`SINAIS_OBSERVACAO`), então sai o
    rótulo e a contagem, nunca o texto que gerou a classificação.
    """
    df = res.tabelas.get("sinais_resumo")
    if df is None or df.empty:
        return {}
    col_sinal = next((c for c in df.columns if "inal" in c.lower()), None)
    col_qtd = next((c for c in df.columns if df[c].dtype.kind in "iuf"), None)
    if col_sinal is None or col_qtd is None:
        return {}
    return {
        str(linha[col_sinal]): int(linha[col_qtd])
        for _, linha in df.iterrows()
        if str(linha[col_sinal]) in CATEGORIAS_SINAL
    }


def pedir_leitura(payload: dict[str, Any], chave_api: str | None) -> LeituraJev | None:
    """Chama o modelo. Devolve None em qualquer falha, sem levantar.

    Toda falha aqui é prevista e nenhuma delas pode derrubar uma análise: sem
    chave, sem rede, estourou o limite, o modelo recusou. A análise já está
    pronta quando esta função é chamada; a leitura é um acréscimo.
    """
    try:
        import anthropic
    except ImportError:
        log.info("JEV desligado: o pacote anthropic não está instalado")
        return None

    try:
        cliente = anthropic.Anthropic(api_key=chave_api) if chave_api else anthropic.Anthropic()
    except Exception as e:  # noqa: BLE001 - credencial ausente ou malformada
        log.warning("JEV: não consegui montar o cliente da API (%s)", type(e).__name__)
        return None

    import json

    try:
        resposta = cliente.messages.parse(
            model=MODELO,
            max_tokens=8000,
            system=INSTRUCAO,
            thinking={"type": "adaptive"},
            # O diagnóstico decide corte de verba, então vale pensar mais: é
            # uma chamada por análise, não por requisição de usuário.
            output_config={"effort": "high"},
            messages=[{
                "role": "user",
                "content": "Leia o mês a seguir e devolva a análise.\n\n"
                           + json.dumps(payload, ensure_ascii=False, default=str),
            }],
            output_format=LeituraJev,
        )
    except anthropic.APIStatusError as e:
        log.warning("JEV: a API respondeu %s", e.status_code)
        return None
    except anthropic.APIConnectionError:
        log.warning("JEV: não consegui alcançar a API")
        return None
    except Exception as e:  # noqa: BLE001 - nada aqui pode derrubar a análise
        log.warning("JEV: falhou (%s)", type(e).__name__)
        return None

    # Uma recusa volta com HTTP 200: o conteúdo tem de ser checado, não o status.
    if getattr(resposta, "stop_reason", None) == "refusal":
        log.warning("JEV: o modelo recusou a requisição")
        return None
    return resposta.parsed_output


def avaliar(res, chave_api: str | None, ativo: bool) -> dict[str, Any]:
    """Orquestra. Devolve sempre um dicionário, nunca levanta."""
    if not ativo:
        return {"ativo": False, "leitura": None, "motivo": "O JEV está desligado nesta instalação."}

    leitura = pedir_leitura(montar_payload(res), chave_api)
    if leitura is None:
        return {
            "ativo": True,
            "leitura": None,
            "motivo": "A leitura do JEV não veio nesta análise. Os números e o Score abaixo "
                      "não dependem dela.",
        }
    return {"ativo": True, "leitura": leitura.model_dump(), "motivo": None}
