"""Relatório em texto para WhatsApp.

O painel é para quem analisa; isto é para quem decide. O dono do negócio não abre
dashboard — ele lê o WhatsApp no semáforo. Então o texto precisa caber numa tela,
abrir pelo que importa e terminar numa pergunta que provoque resposta.

Formatação do WhatsApp: *negrito*, _itálico_, ```mono```. Nada de markdown comum.
"""

from __future__ import annotations

from typing import Any

MESES = {
    "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril",
    "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
    "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro",
}

# Ordem de urgência do diagnóstico: o que dói primeiro aparece primeiro.
PESO_NIVEL = [("🔴", 0), ("🔥", 1), ("⚠️", 2), ("✅", 3), ("ℹ️", 4)]


def _nome_mes(mes: str) -> str:
    try:
        ano, m = mes.split("-")
        return f"{MESES[m]}/{ano}"
    except Exception:
        return mes


def _peso(nivel: str) -> int:
    for icone, p in PESO_NIVEL:
        if icone in nivel:
            return p
    return 5


def _icone(nivel: str) -> str:
    for icone, _ in PESO_NIVEL:
        if icone in nivel:
            return icone
    return "•"


def _kpi(resultado: dict, chave: str) -> dict | None:
    return (resultado.get("kpis") or {}).get(chave)


def _linha_kpi(resultado: dict, chave: str, rotulo: str | None = None) -> str | None:
    k = _kpi(resultado, chave)
    if not k:
        return None
    nome = rotulo or k["rotulo"]
    marca = ""
    if k.get("meta_tipo"):
        marca = "  ✅" if k.get("dentro_da_meta") else "  ⚠️"
    return f"• {nome}: *{k['texto']}*{marca}"


def _variacao(atual: dict, anterior: dict | None, chave: str, melhor: str) -> str | None:
    """Comparação com o mês anterior, com o sinal certo para cada indicador."""
    if not anterior:
        return None
    a, b = atual.get(chave), anterior.get(chave)
    if a is None or b is None or b == 0:
        return None
    dif = (a - b) / abs(b)
    if abs(dif) < 0.03:  # abaixo de 3% é ruído, não notícia
        return None
    subiu = dif > 0
    bom = subiu if melhor == "sobe" else not subiu
    return f"{'📈' if subiu else '📉'} {abs(dif):.0%} {'melhor' if bom else 'pior'} que o mês passado"


def gerar_texto(
    resultado: dict[str, Any],
    nome_cliente: str,
    mes_referencia: str,
    kpis_anteriores: dict | None = None,
    completo: bool = False,
    assinatura: str | None = None,
) -> str:
    """Monta a mensagem. `completo` inclui mais conclusões e a nota da planilha."""
    partes: list[str] = []
    kpis = resultado.get("kpis") or {}
    resumo_atual = {k: v["valor"] for k, v in kpis.items()}

    partes.append(f"*{nome_cliente} — {_nome_mes(mes_referencia)}*")
    partes.append("")

    # ---- os números que o dono do negócio cobra
    linhas = [
        _linha_kpi(resultado, "inv", "Investido em anúncio"),
        _linha_kpi(resultado, "leads", "Leads gerados"),
        _linha_kpi(resultado, "real", "Reuniões realizadas"),
        _linha_kpi(resultado, "fec", "Clientes fechados"),
    ]
    partes.extend([l for l in linhas if l])
    partes.append("")

    # ---- os dois que decidem se valeu a pena
    # Rótulos limpos: "⭐ ASSERTIVIDADE (fechados ÷ realizadas)" é linguagem de
    # painel; quem lê no WhatsApp é o dono do negócio.
    destaque = [
        _linha_kpi(resultado, "assert", "Assertividade (fechados ÷ reuniões)"),
        _linha_kpi(resultado, "cac", "Custo por cliente (CAC)"),
    ]
    if kpis.get("roas"):
        destaque.append(_linha_kpi(resultado, "roas", "ROAS (retorno do anúncio)"))
    if kpis.get("rec"):
        destaque.append(_linha_kpi(resultado, "rec", "Receita fechada"))
    partes.extend([l for l in destaque if l])

    for chave, melhor, rotulo in [("assert", "sobe", "Assertividade"), ("cac", "desce", "CAC")]:
        v = _variacao(resumo_atual, kpis_anteriores, chave, melhor)
        if v:
            partes.append(f"  _{rotulo}: {v}_")
    partes.append("")

    # ---- o que só o Neriah diz
    pipeline = (resultado.get("tabelas") or {}).get("pipeline") or []
    quentes = [p for p in pipeline if "Quente" in str(p.get("Temperatura", ""))]

    diagnostico = sorted(resultado.get("diagnostico") or [], key=lambda d: _peso(d.get("Nível", "")))
    relevantes = [
        d
        for d in diagnostico
        if _peso(d.get("Nível", "")) <= (3 if completo else 2)
        # "Dados" fala da qualidade da planilha — assunto de quem opera, não de
        # quem recebe o relatório. Vira a nota da planilha no modo completo.
        and d.get("Área") != "Dados"
        # o alerta de clientes quentes vira seção própria; aqui seria repetição
        and not (quentes and "quentes para fechar" in d.get("Diagnóstico", ""))
    ]
    if relevantes:
        partes.append("*O que os números estão dizendo*")
        for d in relevantes[: 6 if completo else 3]:
            partes.append(f"{_icone(d['Nível'])} {d['Diagnóstico']}")
        partes.append("")

    # ---- o que fazer agora
    if quentes:
        nomes = ", ".join(str(p.get("Cliente")) for p in quentes[:6])
        partes.append(f"*Para fechar esta semana* ({len(quentes)})")
        partes.append(nomes + ("…" if len(quentes) > 6 else ""))
        partes.append("")

    if completo:
        cob = resultado.get("cobertura") or {}
        faltando = cob.get("faltando_alto_impacto") or []
        if faltando:
            partes.append(
                f"_Sua planilha está em {cob.get('encontrados')}/{cob.get('total')} campos. "
                f"Preencher {', '.join(faltando[:3])} libera mais indicadores._"
            )
            partes.append("")

    partes.append(assinatura or "_Relatório gerado pela Neriah Data._")
    # colapsa linhas em branco repetidas
    texto = "\n".join(partes)
    while "\n\n\n" in texto:
        texto = texto.replace("\n\n\n", "\n\n")
    return texto.strip()
