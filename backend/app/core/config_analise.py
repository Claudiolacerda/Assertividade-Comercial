"""Configuração da análise.

Tudo o que era a "célula 2" do notebook vive aqui, agora como um objeto que pode
ser sobrescrito por cliente (cada empresa tem metas e vocabulário próprios) e
guardado no banco em JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# --------------------------------------------------------------------------- #
# Metas (referências do cliente — só marcam ✅/⚠️ e alimentam o diagnóstico)
# --------------------------------------------------------------------------- #
METAS_PADRAO: dict[str, float] = {
    "ctr": 0.010,  # CTR no link mínimo (1,0%)
    "cpl_max": 40.0,  # custo por lead máximo (R$)
    "lead_para_reuniao": 0.20,  # % dos leads que viram reunião agendada
    "comparecimento": 0.70,  # % de comparecimento nas reuniões
    "assertividade": 0.25,  # fechados / reuniões realizadas
    "win_rate": 0.40,  # fechados / (fechados + perdidos)
    "roas": 3.0,  # receita / investimento
    "cac_max": 800.0,  # custo de aquisição de cliente máximo (R$)
}

# --------------------------------------------------------------------------- #
# Apelidos de colunas (o sistema procura na ordem)
# --------------------------------------------------------------------------- #
COLUNAS_META: dict[str, list[str]] = {
    "data_inicio": ["Início dos relatórios", "Reporting starts", "Dia", "Day", "Data"],
    "data_fim": ["Término dos relatórios", "Encerramento dos relatórios", "Reporting ends"],
    "campanha": ["Nome da campanha", "Campaign name", "Campanha"],
    "conjunto": ["Nome do conjunto de anúncios", "Ad set name", "Conjunto de anúncios"],
    "anuncio": ["Nome do anúncio", "Ad name", "Anúncio"],
    "investimento": [
        "Valor usado (BRL)",
        "Valor gasto (BRL)",
        "Amount spent (BRL)",
        "Valor usado",
        "Valor gasto",
        "Amount spent",
    ],
    "impressoes": ["Impressões", "Impressions"],
    "alcance": ["Alcance", "Reach"],
    "cliques": ["Cliques no link", "Link clicks", "Cliques (todos)", "Clicks (all)"],
    "resultados": ["Resultados", "Results", "Leads", "Cadastros", "Conversas por mensagem iniciadas"],
    "tipo_resultado": ["Indicador de resultado", "Tipo de resultado", "Result indicator", "Result type"],
}

COLUNAS_REUNIOES: dict[str, list[str]] = {
    "data_reuniao": ["Data da reunião", "Data da Reunião Realizada", "Data reuniao", "Data", "Dia"],
    "data_agendamento": ["Data do Agendamento", "Data agendamento", "Data agendada", "Agendado em"],
    "cliente": ["Cliente", "Nome", "Lead", "Empresa", "Nome do cliente"],
    "status": ["Status", "Etapa do Funil", "Situação", "Situacao", "Resultado", "Etapa", "Andamento"],
    "valor": ["Valor", "Valor do contrato", "Valor fechado", "Ticket", "Valor da proposta", "Valor (R$)"],
    "responsavel": ["Responsável", "Responsavel", "Quem fez", "Vendedor", "Closer", "Consultor", "SDR"],
    "origem": ["Origem", "Canal", "Fonte", "Origem do lead"],
    "campanha": ["Campanha", "Nome da campanha", "Anúncio de origem"],
    "produto": ["Produto", "Serviço", "Servico", "Plano", "Oferta"],
    "data_fechamento": ["Data de fechamento", "Data fechamento", "Data do fechamento", "Fechado em"],
    "data_lead": ["Data do lead", "Data de entrada", "Data do primeiro contato", "Entrada"],
    "motivo_perda": ["Motivo da perda", "Motivo", "Objeção", "Objecao", "Por que não fechou"],
    "observacoes": ["Observações", "Observacoes", "Obs", "Comentários", "Anotações"],
}

# --------------------------------------------------------------------------- #
# Classificação dos status — a ORDEM importa ("não fechou" antes de "fechou")
# --------------------------------------------------------------------------- #
REGRAS_STATUS: list[tuple[str, list[str]]] = [
    ("No-show", ["no show", "noshow", "no-show", "nao compareceu", "nao apareceu", "faltou", "ausente", "furou"]),
    ("Remarcado", ["remarc", "reagend", "adiad"]),
    ("Cancelado", ["cancel"]),
    (
        "Perdido",
        [
            "nao fechou", "perdid", "perdeu", "recusou", "desistiu", "sem interesse", "nao tem interesse",
            "descartad", "sem fit", "nao qualificad", "desqualificad", "reprovad", "nao vai fechar",
        ],
    ),
    (
        "Fechado",
        [
            "fechou", "fechad", "ganho", "ganhou", "vendid", "venda realizada", "contrato assinado",
            "assinou", "convertid", "pago", "cliente ativo",
        ],
    ),
    (
        "Em negociação",
        [
            "em processo", "processo", "negoci", "proposta", "follow", "aguardando", "pensando",
            "andamento", "retorno", "analise", "avaliando", "quente", "morno",
        ],
    ),
    ("Reunião feita", ["reuniao feita", "reuniao realizada", "realizada", "call feita", "atendid"]),
    ("Agendado", ["agendad", "marcad", "confirmad", "a realizar", "futura"]),
]

# --------------------------------------------------------------------------- #
# Leitura das observações: sinais (não mudam o status, só sinalizam)
# --------------------------------------------------------------------------- #
SINAIS_OBSERVACAO: dict[str, list[str]] = {
    "Provável perda": [
        "nao tem interesse", "sem interesse", "trocou de contabilidade", "fechou com outr", "desistiu", "nao vai",
    ],
    "Objeção: preço/orçamento": [
        "caro", "pechinch", "orcamento", "cotando", "valores", "desconto", "quando receber",
        "recebesse um dinheiro", "fluxo de pagamento",
    ],
    "Decide com cônjuge/sócio": ["marido", "esposa", "mulher", "socio", "entre eles", "familia"],
    "Comparando concorrentes": ["outras opcoes", "outra contabilidade", "concorren", "desenquadrad", "sua agencia"],
    "Promessa de fechamento": [
        "vai fechar", "ira fechar", "fecha em", "fecharia", "disse que fechava", "quer fechar", "decidirao",
    ],
    "Pediu retorno / follow-up": [
        "retornar", "retorne", "retorna", "falar em", "voltar a falar", "falar com ele", "falar no final",
        "follow", "semana", "outubro",
    ],
    "Só tirou dúvidas": ["tirar duvidas", "tirou duvidas"],
    "Pediu contrato/proposta": ["contrato", "proposta"],
}

ORIGENS_TRAFEGO_PAGO: list[str] = [
    "meta", "facebook", "instagram ads", "insta ads", "ads", "trafego", "anuncio", "fb", "pago",
]

STATUS_REALIZADA = ["Fechado", "Perdido", "Em negociação", "Reunião feita"]
STATUS_ORDEM = [
    "Fechado", "Em negociação", "Reunião feita", "Perdido", "No-show", "Remarcado", "Cancelado",
    "Agendado", "Não classificado", "Sem status",
]
DIAS_PT = ["1-Segunda", "2-Terça", "3-Quarta", "4-Quinta", "5-Sexta", "6-Sábado", "7-Domingo"]
MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


@dataclass
class ConfigAnalise:
    """Configuração de uma rodada de análise.

    Os campos com valor padrão espelham a célula de configuração do notebook.
    Cada empresa (tenant) guarda a sua versão disto no banco.
    """

    mes_referencia: str | None = None
    metas: dict[str, float] = field(default_factory=lambda: dict(METAS_PADRAO))
    filtrar_reunioes_por_data: Any = "auto"  # "auto", True ou False
    ano_padrao: int | None = None
    marcacoes_nao_pagas: list[str] = field(default_factory=list)
    classificar_perda_pela_observacao: bool = False
    prob_fechamento_negociacao: float = 0.30
    dias_alerta_pipeline: int = 15
    origens_trafego_pago: list[str] = field(default_factory=lambda: list(ORIGENS_TRAFEGO_PAGO))
    sem_origem_considerar_pago: bool = True
    coluna_leads_meta: str | None = None
    colunas_meta: dict[str, list[str]] = field(default_factory=lambda: {k: list(v) for k, v in COLUNAS_META.items()})
    colunas_reunioes: dict[str, list[str]] = field(
        default_factory=lambda: {k: list(v) for k, v in COLUNAS_REUNIOES.items()}
    )
    regras_status: list[tuple[str, list[str]]] = field(
        default_factory=lambda: [(c, list(ks)) for c, ks in REGRAS_STATUS]
    )
    status_manual: dict[str, str] = field(default_factory=dict)
    sinais_observacao: dict[str, list[str]] = field(
        default_factory=lambda: {k: list(v) for k, v in SINAIS_OBSERVACAO.items()}
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dados: dict[str, Any] | None) -> "ConfigAnalise":
        """Constrói a config a partir do JSON salvo no banco, ignorando chaves desconhecidas."""
        if not dados:
            return cls()
        validos = {f for f in cls.__dataclass_fields__}
        limpo = {k: v for k, v in dados.items() if k in validos}
        if "metas" in limpo and isinstance(limpo["metas"], dict):
            limpo["metas"] = {**METAS_PADRAO, **limpo["metas"]}
        if "regras_status" in limpo and isinstance(limpo["regras_status"], list):
            limpo["regras_status"] = [(r[0], list(r[1])) for r in limpo["regras_status"]]
        return cls(**limpo)


# --------------------------------------------------------------------------- #
# Metadados dos campos comerciais: o que cada coluna destrava.
# Alimenta a "nota da planilha" mostrada ao cliente e a planilha-modelo.
# --------------------------------------------------------------------------- #
CAMPOS_REUNIOES_INFO: dict[str, dict] = {
    "cliente": {
        "rotulo": "Cliente",
        "destrava": "Base de tudo — sem isso não há análise",
        "impacto": "obrigatorio",
        "exemplo": "Padaria do Zé",
    },
    "status": {
        "rotulo": "Etapa do Funil",
        "destrava": "Base de tudo — assertividade, funil e pipeline",
        "impacto": "obrigatorio",
        "exemplo": "Fechado",
    },
    "data_reuniao": {
        "rotulo": "Data da Reunião Realizada",
        "destrava": "Evolução por semana e por dia da semana",
        "impacto": "alto",
        "exemplo": "05/03/2026",
    },
    "valor": {
        "rotulo": "Valor",
        "destrava": "Receita, ticket médio, ROAS, ROI e forecast do pipeline",
        "impacto": "alto",
        "exemplo": "2500,00",
    },
    "campanha": {
        "rotulo": "Campanha",
        "destrava": "CAC e ROAS por campanha — qual anúncio realmente vende",
        "impacto": "alto",
        "exemplo": "[GT] [WPP] [VENDAS]",
    },
    "origem": {
        "rotulo": "Origem",
        "destrava": "Separar tráfego pago de indicação (CAC real do anúncio)",
        "impacto": "alto",
        "exemplo": "Facebook Ads",
    },
    "motivo_perda": {
        "rotulo": "Motivo da perda",
        "destrava": "Motivos de perda e win rate confiável",
        "impacto": "alto",
        "exemplo": "Achou caro",
    },
    "responsavel": {
        "rotulo": "Responsável",
        "destrava": "Comparação de assertividade entre vendedores",
        "impacto": "medio",
        "exemplo": "Marina",
    },
    "data_agendamento": {
        "rotulo": "Data do Agendamento",
        "destrava": "Tempo entre agendar e a reunião acontecer",
        "impacto": "medio",
        "exemplo": "03/03/2026",
    },
    "data_fechamento": {
        "rotulo": "Data de fechamento",
        "destrava": "Ciclo de venda — quantos dias leva para fechar",
        "impacto": "medio",
        "exemplo": "08/03/2026",
    },
    "observacoes": {
        "rotulo": "Observações",
        "destrava": "Objeções, sinais de compra e temperatura do pipeline",
        "impacto": "medio",
        "exemplo": "Gostou, mas vai falar com o sócio",
    },
    "produto": {
        "rotulo": "Produto",
        "destrava": "Assertividade por produto ou plano",
        "impacto": "baixo",
        "exemplo": "Plano ME",
    },
    "data_lead": {
        "rotulo": "Data do lead",
        "destrava": "Tempo de resposta ao lead",
        "impacto": "baixo",
        "exemplo": "01/03/2026",
    },
}

# Valores aceitos na coluna de etapa. Viram lista suspensa na planilha-modelo,
# o que acaba com "Nao fechou" convivendo com "Perdeu" na mesma planilha.
ETAPAS_SUGERIDAS = [
    "Agendado",
    "Reunião Feita",
    "Follow Up",
    "Fechado",
    "Perdido",
    "No-show",
    "Remarcado",
    "Cancelado",
]
