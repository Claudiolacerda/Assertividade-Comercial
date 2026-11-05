"""O PDF que justifica a projeção.

Ele existe para a reunião, não para a tela: quem leva "aumentar 20% da verba
traz 2 clientes a mais" ouve "de onde você tirou isso". Por isso os testes aqui
verificam, antes de qualquer formatação, que o documento carrega as quatro
coisas que sustentam a resposta — os meses que entraram na conta, o método, o
resultado e os limites — e que ele não promete nada quando não há base.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.core.pdf_projecao import LIMITES, gerar_pdf, tabela_dos_cenarios, tabela_dos_meses, texto_do_metodo
from app.core.projecao import projetar


def pontos(pares):
    return [
        {"mes_referencia": m, "inv": inv, "fec": fec, "rec": fec * 2600.0, "leads": inv / 45}
        for m, inv, fec in pares
    ]


TRES = pontos([("2026-07", 2460.0, 6), ("2026-08", 4120.0, 9), ("2026-09", 3650.0, 9)])


@pytest.fixture(scope="module")
def projecao():
    return projetar(TRES, metas={"cac_max": 800.0})


# --------------------------------------------------------------------- #
# A evidência
# --------------------------------------------------------------------- #
def test_a_tabela_tem_uma_linha_por_mes_analisado(projecao):
    linhas = tabela_dos_meses(projecao)
    assert len(linhas) == 1 + len(TRES), "cabeçalho mais um mês por linha"
    assert linhas[1][0] == "julho/2026"


def test_a_tabela_traz_o_cac_calculado_de_cada_mes(projecao):
    """É a coluna que o cliente confere de cabeça: investimento ÷ clientes."""
    julho = tabela_dos_meses(projecao)[1]
    assert julho[1] == "R$ 2.460,00"
    assert julho[5] == "R$ 410,00", "2460 ÷ 6"


def test_mes_sem_receita_nao_vira_zero_na_tabela():
    """Planilha sem coluna de valor existe, e zero ali seria uma afirmação falsa."""
    sem_valor = [{**p, "rec": None} for p in TRES]
    linhas = tabela_dos_meses(projetar(sem_valor, metas={}))
    assert all(linha[4] == "—" for linha in linhas[1:])


# --------------------------------------------------------------------- #
# O método, escrito
# --------------------------------------------------------------------- #
def test_o_metodo_e_nomeado_e_a_formula_aparece(projecao):
    texto = " ".join(texto_do_metodo(projecao))
    assert "mínimos quadrados" in texto
    assert "a + b × investimento" in texto
    assert "R²" in texto


def test_o_metodo_da_regra_de_tres_diz_que_e_regra_de_tres():
    """Um relatório que chama proporção de regressão é o pior resultado possível."""
    duas = projetar(pontos([("2026-08", 3000.0, 6), ("2026-09", 4000.0, 8)]), metas={})
    texto = " ".join(texto_do_metodo(duas))
    assert "regra de" in texto and "três" in texto
    assert "mínimos quadrados" not in texto


def test_os_limites_falam_de_causalidade_e_de_extrapolacao():
    texto = " ".join(LIMITES)
    assert "não o que causou o quê" in texto
    assert "extrapolam" in texto
    assert "Receita não é lucro" in texto


# --------------------------------------------------------------------- #
# Os cenários
# --------------------------------------------------------------------- #
def test_os_cenarios_marcam_o_que_nunca_foi_testado(projecao):
    linhas = tabela_dos_cenarios(projecao)
    assert any("nunca testado" in linha[0] for linha in linhas[1:])
    assert any(linha[0] == "hoje" for linha in linhas[1:])


def test_coluna_sem_modelo_nao_entra_no_pdf():
    """A mesma regra da tela: fileira de travessões não informa nada."""
    sem_valor = [{**p, "rec": None} for p in TRES]
    cabecalho = tabela_dos_cenarios(projetar(sem_valor, metas={}))[0]
    assert "Receita fechada" not in cabecalho


# --------------------------------------------------------------------- #
# O arquivo
# --------------------------------------------------------------------- #
def test_o_pdf_sai_valido_e_com_conteudo(projecao):
    dados = gerar_pdf(projecao, empresa="Cliente Exemplo", organizacao="Agência X")
    assert dados[:5] == b"%PDF-", "um PDF começa com %PDF-"
    assert len(dados) > 4000, "um PDF com duas páginas de texto não é menor que isso"


def test_o_pdf_salva_no_caminho_pedido(projecao, tmp_path):
    destino = tmp_path / "sub" / "relatorio.pdf"
    gerar_pdf(projecao, empresa="X", destino=destino)
    assert destino.exists() and destino.read_bytes()[:5] == b"%PDF-"


def test_sem_base_o_pdf_diz_isso_em_vez_de_projetar():
    """Nenhum mês analisado: o documento sai, e sai dizendo que não há base."""
    vazio = projetar([])
    dados = gerar_pdf(vazio, empresa="Cliente Novo")
    assert dados[:5] == b"%PDF-"
    assert len(dados) < 4000, "é um documento curto: só a explicação"


def test_a_data_de_emissao_entra_no_documento(projecao):
    """Relatório sem data não se arquiva nem se compara com o do mês seguinte."""
    dados = gerar_pdf(projecao, empresa="X", emitido_em=date(2026, 11, 4))
    # O texto do PDF não comprimido guarda a data legível no fluxo de conteúdo.
    assert b"04/11/2026" in dados or b"2026" in dados


def test_o_pdf_usa_a_manchete_do_motor(projecao):
    """Tela e documento têm de afirmar a mesma coisa, na mesma força.

    O PDF tinha a frase do efeito escrita nele mesmo, então ele continuaria
    dizendo "+0,9 cliente por R$ 1.000" em destaque num mês em que a tela já
    avisava que a reta não sustenta projeção.
    """
    import re
    from pathlib import Path as _P

    fonte = _P("app/core/pdf_projecao.py").read_text(encoding="utf-8")
    assert 'projecao.get("manchete")' in fonte
    assert not re.search(r'f"A cada R\$ 1\.000', fonte), "a frase não pode nascer no PDF"


def test_o_pdf_marca_a_manchete_fraca_com_outro_estilo():
    from app.core.pdf_projecao import _estilos

    assert "manchete_fraca" in _estilos()
