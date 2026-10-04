"""Gera exportações fictícias no formato de vários CRMs, a partir de UMA base.

A base é a mesma para todos: 32 negócios de setembro/2026, com desfecho,
valor, campanha e responsável conhecidos. Só a FORMA muda de arquivo para
arquivo — cabeçalho, vocabulário de status, formato de data e separador
decimal. Assim, qualquer diferença no que o Neriah lê é culpa do formato.

Grau de confiança de cada formato, para não vender gato por lebre:
  alto   HubSpot, Pipedrive  — nomes de propriedade amplamente documentados
  medio  RD Station, Agendor — três campos do RD confirmados na documentação
  baixo  DataCrazy, Datalitics — produtos reais, formato de exportação NÃO
         documentado publicamente; aqui é uma reconstrução plausível de um
         CRM de WhatsApp e de um rastreador com CRM, não o arquivo real.
"""
import csv, random
from pathlib import Path

# As fixtures ficam ao lado deste arquivo: rodar `python gerar.py` daqui
# regenera todas elas no lugar certo, sem subpasta.
SAIDA = Path(__file__).parent
random.seed(20260904)

CAMPANHAS = ["[GT] [WPP] [VENDAS] [28.10.25]", "[GT] [WPP] [VENDAS] [18.08.26]"]
VENDEDORES = ["Rafael", "Juliana", "Marcos"]
PRIMEIROS = ["Aurora", "Benedito", "Cibele", "Dagoberto", "Eunice", "Fabrício", "Gilda",
             "Hamilton", "Ivete", "Joaquim", "Ladislau", "Marlene", "Nivaldo", "Odete",
             "Plínio", "Quitéria", "Rubens", "Sandra", "Teobaldo", "Ulisses", "Vanda",
             "Waldemar", "Xênia", "Yolanda", "Zuleica", "Amadeu", "Bruna Lima",
             "Celso Rocha", "Dilma Prado", "Edgard Sá", "Fátima Luz", "Getúlio Pires"]

# desfecho: quantos de cada, cravado para poder conferir depois
PLANO = (["ganho"] * 9 + ["perdido"] * 7 + ["negociando"] * 8
         + ["noshow"] * 4 + ["agendado"] * 4)
assert len(PLANO) == len(PRIMEIROS) == 32

BASE = []
for i, (nome, desfecho) in enumerate(zip(PRIMEIROS, PLANO)):
    dia = 1 + (i % 24)
    BASE.append({
        "nome": nome,
        "desfecho": desfecho,
        "valor": 0 if desfecho in ("noshow", "agendado") else round(random.uniform(900, 4800), 2),
        "campanha": CAMPANHAS[i % 2],
        "vendedor": VENDEDORES[i % 3],
        "dia": dia,
        "dia_criado": max(1, dia - 3),
        "obs": {
            "ganho": "Assinou o contrato na call",
            "perdido": "Achou caro e seguiu com o concorrente",
            "negociando": "Pediu a proposta para analisar, retorna semana que vem",
            "noshow": "Não compareceu na reunião marcada",
            "agendado": "Reunião marcada, ainda vai acontecer",
        }[desfecho],
    })

VERDADE = {
    "linhas": len(BASE),
    "fechados": sum(1 for b in BASE if b["desfecho"] == "ganho"),
    "perdidos": sum(1 for b in BASE if b["desfecho"] == "perdido"),
    "em_negociacao": sum(1 for b in BASE if b["desfecho"] == "negociando"),
    "noshow": sum(1 for b in BASE if b["desfecho"] == "noshow"),
    "agendados": sum(1 for b in BASE if b["desfecho"] == "agendado"),
    "receita": round(sum(b["valor"] for b in BASE if b["desfecho"] == "ganho"), 2),
}

def br(v):      # 2500.5 -> "2.500,50"
    return f"{v:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
def iso(d):     return f"2026-09-{d:02d}"
def ptbr(d):    return f"{d:02d}/09/2026"

def escrever(nome, cabecalho, linhas, sep=","):
    caminho = SAIDA / nome
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=sep)
        w.writerow(cabecalho)
        w.writerows(linhas)
    return caminho

# ----------------------------------------------------------------- HubSpot
# Propriedades de negócio em inglês, datas ISO, decimal com ponto.
ETAPA_HS = {"ganho": "Closed Won", "perdido": "Closed Lost",
            "negociando": "Decision Maker Bought-In", "noshow": "Appointment Scheduled",
            "agendado": "Appointment Scheduled"}
escrever("hubspot_deals_export.csv",
    ["Record ID", "Deal Name", "Deal Stage", "Deal owner", "Amount", "Close Date",
     "Create Date", "Pipeline", "Deal Type", "Original Traffic Source", "Notes"],
    [[1000 + i, f"{b['nome']} - Contrato", ETAPA_HS[b["desfecho"]], b["vendedor"],
      f"{b['valor']:.2f}", iso(b["dia"]), iso(b["dia_criado"]), "Sales Pipeline",
      "newbusiness", "Paid Social", b["obs"]] for i, b in enumerate(BASE)])

# --------------------------------------------------------------- Pipedrive
# Cabeçalho com prefixo "Deal - ", em inglês, e DUAS colunas de situação:
# "Deal - Status" só diz Won/Lost/Open, e "Deal - Stage" diz em que ponto do
# funil o negócio está. Quem lê só a primeira trata reunião ainda não
# acontecida como negócio em negociação, e enche o denominador da
# assertividade. O Pipedrive não tem etapa de no-show: quem faltou fica na
# etapa da reunião marcada, igual a quem ainda vai ser atendido.
ETAPA_PD = {"ganho": "Won", "perdido": "Lost", "negociando": "Open",
            "noshow": "Open", "agendado": "Open"}
FASE_PD = {"ganho": "Negotiations Started", "perdido": "Proposal Made",
           "negociando": "Proposal Made", "noshow": "Demo Scheduled",
           "agendado": "Demo Scheduled"}
escrever("pipedrive_deals_export.csv",
    ["Deal - ID", "Deal - Title", "Deal - Stage", "Deal - Status", "Deal - Owner",
     "Deal - Value", "Deal - Currency", "Deal - Won time", "Deal - Add time",
     "Deal - Source Campaign", "Deal - Notes"],
    [[2000 + i, f"{b['nome']} - Negócio", FASE_PD[b["desfecho"]], ETAPA_PD[b["desfecho"]],
      b["vendedor"], f"{b['valor']:.2f}", "BRL",
      iso(b["dia"]) if b["desfecho"] == "ganho" else "", iso(b["dia_criado"]),
      b["campanha"], b["obs"]] for i, b in enumerate(BASE)])

# -------------------------------------------------------------- RD Station
# Português, data dd/mm/aaaa, decimal com vírgula. "Ganha"/"Perdida" no
# feminino, porque o objeto lá é "a negociação".
ETAPA_RD = {"ganho": "Ganha", "perdido": "Perdida", "negociando": "Em andamento",
            "noshow": "Em andamento", "agendado": "Em andamento"}
escrever("rdstation_negociacoes.csv",
    ["Nome da negociação", "Etapa do funil de vendas", "Responsável pela negociação",
     "Valor da negociação", "Data de criação", "Data de fechamento", "Funil",
     "Campanha", "Origem", "Anotações"],
    [[f"{b['nome']}", ETAPA_RD[b["desfecho"]], b["vendedor"], br(b["valor"]),
      ptbr(b["dia_criado"]), ptbr(b["dia"]) if b["desfecho"] == "ganho" else "",
      "Funil de Vendas", b["campanha"], "Facebook Ads", b["obs"]]
     for b in BASE], sep=";")

# ----------------------------------------------------------------- Agendor
ETAPA_AG = {"ganho": "Ganho", "perdido": "Perdido", "negociando": "Em negociação",
            "noshow": "Não compareceu", "agendado": "Agendado"}
escrever("agendor_negocios.csv",
    ["Negócio", "Etapa", "Status", "Responsável", "Valor", "Data de início",
     "Data de conclusão", "Funil", "Origem", "Descrição"],
    [[f"{b['nome']} Ltda", "Proposta enviada", ETAPA_AG[b["desfecho"]], b["vendedor"],
      br(b["valor"]), ptbr(b["dia_criado"]),
      ptbr(b["dia"]) if b["desfecho"] in ("ganho", "perdido") else "",
      "Funil Principal", "Anúncio Facebook", b["obs"]] for b in BASE], sep=";")

# --------------------------------------------------------------- DataCrazy
# CRM de WhatsApp: a linha é o contato, não o negócio, e a data tem hora.
ETAPA_DC = {"ganho": "Vendido", "perdido": "Perdido", "negociando": "Em atendimento",
            "noshow": "Não compareceu", "agendado": "Agendado"}
escrever("datacrazy_leads.csv",
    ["ID", "Contato", "Telefone", "Funil", "Status", "Atendente", "Valor",
     "Data de entrada", "Última interação", "Canal", "Campanha", "Tags", "Observação"],
    [[3000 + i, b["nome"], f"+55 11 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
      "Funil de Vendas", ETAPA_DC[b["desfecho"]], b["vendedor"], br(b["valor"]),
      f"{ptbr(b['dia_criado'])} 09:{i % 60:02d}", f"{ptbr(b['dia'])} 15:{i % 60:02d}",
      "WhatsApp", b["campanha"], "lead-quente", b["obs"]] for i, b in enumerate(BASE)])

# -------------------------------------------------------------- Datalitics
# Rastreador + CRM: o forte dele é a origem, então vem com utm.
ETAPA_DL = {"ganho": "Venda", "perdido": "Perdido", "negociando": "Qualificado",
            "noshow": "Não compareceu", "agendado": "Agendado"}
escrever("datalitics_leads.csv",
    ["lead_id", "Nome", "Status", "Vendedor", "Valor", "Data do lead",
     "Data da conversão", "utm_source", "utm_medium", "utm_campaign",
     "Canal", "Anotação"],
    [[f"ld_{4000+i}", b["nome"], ETAPA_DL[b["desfecho"]], b["vendedor"],
      f"{b['valor']:.2f}", f"{iso(b['dia_criado'])}T09:00:00",
      f"{iso(b['dia'])}T15:00:00" if b["desfecho"] == "ganho" else "",
      "facebook", "paid", b["campanha"], "Meta Ads", b["obs"]]
     for i, b in enumerate(BASE)])

import json
(SAIDA / "_verdade.json").write_text(json.dumps(VERDADE, indent=2, ensure_ascii=False), encoding="utf-8")
print("verdade da base:", json.dumps(VERDADE, ensure_ascii=False))
for f in sorted(SAIDA.glob("*.csv")):
    print(" ", f.name, f.stat().st_size, "bytes")
