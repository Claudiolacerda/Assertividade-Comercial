"""Testes do JEV.

O teste que importa é `test_payload_nao_leva_nome_nem_texto_livre`. Ele é a
razão de este arquivo existir: o usuário escolheu que só agregado sai da
máquina, e uma promessa dessas vale o que vale a verificação dela. O teste
monta o payload a partir da planilha real, junta todo nome de cliente e toda
observação que existem nela, e falha se qualquer um aparecer no que seria
enviado. Se alguém acrescentar um campo ao payload e esse campo trouxer texto
do cliente junto, o teste quebra antes de o dado sair.

O resto cobre a outra promessa: o JEV é aditivo. Sem chave, sem pacote, sem
rede ou com o modelo recusando, a análise continua saindo inteira.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core import analisar
from app.core.jev import CATEGORIAS_SINAL, LeituraJev, avaliar, montar_payload, pedir_leitura

DADOS = Path(__file__).resolve().parents[2] / "dados"
META = DADOS / "meta" / "Campanhas-Exemplo-1-de-set-de-2026-24-de-set-de-2026.csv"
REUNIOES = DADOS / "reunioes" / "Controle_Comercial_Exemplo_-_Setembro.csv"

pytestmark = pytest.mark.skipif(
    not (META.exists() and REUNIOES.exists()), reason="arquivos de exemplo não disponíveis"
)


@pytest.fixture(scope="module")
def res():
    return analisar([META], [REUNIOES])


@pytest.fixture(scope="module")
def payload(res):
    return montar_payload(res)


# --------------------------------------------------------------------- #
# A promessa: só agregado sai da máquina
# --------------------------------------------------------------------- #
def test_payload_nao_leva_nome_nem_texto_livre(res, payload):
    """Nenhum nome de cliente e nenhuma observação pode estar no que sai daqui.

    Os nomes saem com fronteira de palavra, porque um nome curto pode ser
    pedaço legítimo de outra coisa. As observações saem por substring: são
    frases longas, e qualquer pedaço delas aparecendo no payload já é
    vazamento.
    """
    enviado = json.dumps(payload, ensure_ascii=False, default=str)

    base = res.tabelas["base_reunioes"]
    col_cliente = next(c for c in base.columns if "liente" in c)
    nomes = {str(v).strip() for v in base[col_cliente].dropna() if str(v).strip()}
    assert len(nomes) > 20, "a planilha de exemplo deveria ter dezenas de clientes"

    L = r"A-Za-zÀ-ÿ"
    vazou_nome = [
        n for n in nomes
        if re.search(rf"(?<![{L}]){re.escape(n)}(?![{L}])", enviado)
    ]
    assert vazou_nome == [], f"nome de cliente no payload: {vazou_nome}"

    obs = res.tabelas["observacoes"]
    col_obs = next(c for c in obs.columns if "bserva" in c)
    textos = {str(v).strip() for v in obs[col_obs].dropna() if len(str(v).strip()) > 12}
    assert len(textos) > 10, "a planilha de exemplo deveria ter observações"
    vazou_obs = [o for o in textos if o in enviado]
    assert vazou_obs == [], f"observação no payload: {vazou_obs}"


def test_payload_nao_leva_quem_fez_a_reuniao(res, payload):
    """Responsável é funcionário do cliente: também é pessoa."""
    enviado = json.dumps(payload, ensure_ascii=False, default=str)
    base = res.tabelas["base_reunioes"]
    col = next((c for c in base.columns if "espons" in c.lower()), None)
    if col is None:
        pytest.skip("a planilha de exemplo não tem coluna de responsável")
    L = r"A-Za-zÀ-ÿ"
    nomes = {str(v).strip() for v in base[col].dropna() if str(v).strip()}
    vazou = [n for n in nomes if re.search(rf"(?<![{L}]){re.escape(n)}(?![{L}])", enviado)]
    assert vazou == [], f"nome de responsável no payload: {vazou}"


def test_sinais_saem_como_rotulo_fixo_e_contagem(payload):
    """A categoria vem do vocabulário do código, não do texto do cliente."""
    sinais = payload["sinais_nas_observacoes"]
    assert sinais, "a planilha de exemplo tem observações classificadas"
    assert all(rotulo in CATEGORIAS_SINAL for rotulo in sinais)
    assert all(isinstance(qtd, int) for qtd in sinais.values())


def test_payload_leva_os_numeros_que_o_modelo_precisa(payload):
    """O que sobra depois do corte ainda tem de sustentar um diagnóstico."""
    assert payload["kpis"]["assert"]["texto"]
    assert payload["kpis"]["cac"]["texto"]
    assert payload["score"]["valor"] is not None
    assert len(payload["indicadores"]) >= 8
    assert payload["campanhas"], "sem campanha não dá para falar de verba"
    assert payload["planilha"]["liga_campanha_a_cliente"] in (True, False)


def test_kpi_novo_no_pipeline_nao_vaza_sozinho(res):
    """A lista do payload é de inclusão: campo novo fica fora até ser incluído."""
    res.kpis["segredo_qualquer"] = {
        "rotulo": "Campo que ninguém revisou", "texto": "xyzzy-marcador", "valor": 1,
    }
    try:
        enviado = json.dumps(montar_payload(res), ensure_ascii=False, default=str)
        assert "xyzzy-marcador" not in enviado
    finally:
        del res.kpis["segredo_qualquer"]


# --------------------------------------------------------------------- #
# A outra promessa: o JEV é aditivo
# --------------------------------------------------------------------- #
def test_desligado_devolve_motivo_sem_chamar_a_api(res):
    with patch("app.core.jev.pedir_leitura") as chamada:
        saida = avaliar(res, chave_api=None, ativo=False)
    chamada.assert_not_called()
    assert saida["ativo"] is False and saida["leitura"] is None and saida["motivo"]


def test_falha_da_api_nao_derruba_a_analise(res):
    with patch("app.core.jev.pedir_leitura", return_value=None):
        saida = avaliar(res, chave_api="sk-ant-qualquer", ativo=True)
    assert saida["leitura"] is None
    assert "não dependem dela" in saida["motivo"]


def test_erro_de_rede_vira_none_em_vez_de_excecao():
    import anthropic

    falso = MagicMock()
    falso.messages.parse.side_effect = anthropic.APIConnectionError(request=MagicMock())
    with patch("anthropic.Anthropic", return_value=falso):
        assert pedir_leitura({"qualquer": "coisa"}, "sk-ant-qualquer") is None


def test_recusa_do_modelo_vira_none():
    falso = MagicMock()
    falso.messages.parse.return_value = MagicMock(stop_reason="refusal")
    with patch("anthropic.Anthropic", return_value=falso):
        assert pedir_leitura({"qualquer": "coisa"}, "sk-ant-qualquer") is None


def test_sem_o_pacote_instalado_nao_quebra(monkeypatch):
    import builtins

    real = builtins.__import__

    def sem_anthropic(nome, *args, **kwargs):
        if nome == "anthropic":
            raise ImportError("sem o pacote")
        return real(nome, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", sem_anthropic)
    assert pedir_leitura({"qualquer": "coisa"}, None) is None


def test_leitura_valida_passa_inteira():
    leitura = LeituraJev(
        leitura="O mês entregou volume e falhou em custo.",
        primeiro_passo="Cortar a campanha de pior CAC.",
        pontos=[{"titulo": "Cortar a pior campanha", "porque": "CAC acima do teto",
                 "indicadores": ["CAC (custo por cliente)"]}],
        onde_mover_verba="Mover a verba da pior para a de melhor nota.",
    )
    falso = MagicMock()
    falso.messages.parse.return_value = MagicMock(stop_reason="end_turn", parsed_output=leitura)
    with patch("anthropic.Anthropic", return_value=falso):
        obtida = pedir_leitura({"qualquer": "coisa"}, "sk-ant-qualquer")
    assert obtida is not None and obtida.primeiro_passo.startswith("Cortar")


def test_a_chamada_usa_o_modelo_e_o_formato_combinados():
    falso = MagicMock()
    falso.messages.parse.return_value = MagicMock(stop_reason="end_turn", parsed_output=None)
    with patch("anthropic.Anthropic", return_value=falso):
        pedir_leitura({"mes": "setembro"}, "sk-ant-qualquer")
    kwargs = falso.messages.parse.call_args.kwargs
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["output_format"] is LeituraJev
    assert kwargs["thinking"] == {"type": "adaptive"}
    # o payload vai no corpo da mensagem, não no system
    assert "setembro" in kwargs["messages"][0]["content"]
    assert "NÃO CALCULE NADA" in kwargs["system"]
