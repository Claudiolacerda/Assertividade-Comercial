"""O relatório do mês em PDF.

É o arquivo que o cliente recebe por e-mail ou WhatsApp sem abrir a planilha,
então o que importa aqui não é a diagramação: é que os números do documento
sejam os mesmos da tela, que nenhuma seção suma em silêncio e que o texto saia
legível (pontuação brasileira, sem quadrado preto no lugar de emoji).

O extrator abaixo lê o texto do próprio PDF em vez de confiar nas funções que
o montaram — um defeito que sumiu com a seção 1 inteira passou despercebido
justamente porque os testes olhavam só para as peças.
"""

from __future__ import annotations

import base64
import re
import zlib
from datetime import date

import pytest

from app.core.pdf_analise import _numero, _situacao, gerar_pdf


# --------------------------------------------------------------------- #
# Ler o texto de volta do PDF
# --------------------------------------------------------------------- #
_LITERAL = re.compile(rb"\((?:\\.|[^()\\])*\)", re.S)
_OCTAL = re.compile(rb"\\([0-7]{1,3})")
_STREAM = re.compile(rb"stream\r?\n(.*?)endstream", re.S)


def texto_do_pdf(dados: bytes) -> str:
    """Junta as cadeias de texto do PDF, descomprimindo os fluxos de página.

    Ler o texto de volta do arquivo, em vez de inspecionar as funções que o
    montaram, é o que pega um defeito que apaga uma seção inteira sem erro.
    """
    partes = []
    for fluxo in _STREAM.findall(dados):
        # reportlab grava /ASCII85Decode + /FlateDecode; nem todo fluxo é texto.
        try:
            conteudo = zlib.decompress(base64.a85decode(fluxo.strip(), adobe=True))
        except Exception:
            try:
                conteudo = zlib.decompress(fluxo)
            except zlib.error:
                conteudo = fluxo
        for bruto in _LITERAL.findall(conteudo):
            corpo = bruto[1:-1]
            corpo = re.sub(rb"\\([()\\])", rb"\1", corpo)
            corpo = _OCTAL.sub(lambda m: bytes([int(m.group(1), 8)]), corpo)
            partes.append(corpo.decode("latin-1"))
    return " ".join(partes)


# --------------------------------------------------------------------- #
# Um resultado gravado, no formato que sai do banco
# --------------------------------------------------------------------- #
@pytest.fixture
def payload() -> dict:
    return {
        "mes_referencia": "2026-09",
        "nome_mes": "setembro/2026",
        "tem_valor": False,
        "avisos": ["A planilha não tem coluna de valor; receita e ticket ficam de fora."],
        "cobertura": {
            "encontrados": 6,
            "total": 8,
            "campos": [
                {"rotulo": "Valor do contrato", "encontrado": False},
                {"rotulo": "Origem", "encontrado": False},
                {"rotulo": "Cliente", "encontrado": True},
            ],
        },
        # Como o banco guarda: lista de dicionários, não de tuplas.
        "blocos": [
            {"titulo": "comercial — todas as origens", "chaves": ["fec", "assert", "fecm"]},
            {"titulo": "tráfego", "chaves": ["inv", "leads"]},
        ],
        "kpis": {
            "fec": {"rotulo": "Clientes fechados", "valor": 10.0, "formato": "int"},
            "assert": {
                "rotulo": "✅ Assertividade",
                "valor": 0.2273,
                "formato": "pct",
                "meta_tipo": "min",
                "meta_valor": 0.30,
                "dentro_da_meta": False,
                "faixa": {"veredito": "indistinguivel"},
            },
            "fecm": {
                "rotulo": "Fechados com marcação no nome (Tayron)",
                "valor": 4.0,
                "formato": "int",
            },
            "inv": {"rotulo": "Investimento", "valor": 3651.02, "formato": "brl"},
            "leads": {"rotulo": "Leads", "valor": 144456.0, "formato": "int"},
        },
        "diagnostico": [
            {"Nível": "🔴 Crítico", "Diagnóstico": "A assertividade caiu pelo segundo mês."},
            {"Nível": "✅ OK", "Diagnóstico": "O custo por lead ficou dentro da meta."},
        ],
        "tabelas": {
            "funil_topo": [
                {"Etapa": "Leads / conversas (Meta)", "Quantidade": 81,
                 "Conversão da etapa anterior (%)": None},
                {"Etapa": "Reuniões agendadas", "Quantidade": 46,
                 "Conversão da etapa anterior (%)": 0.568},
                {"Etapa": "Clientes fechados", "Quantidade": 10,
                 "Conversão da etapa anterior (%)": 0.227},
            ],
            "fechamentos": [
                {"Cliente": f"Cliente {i}", "Marcação": "Tayron" if i < 4 else "(sem marcação)",
                 "Status na planilha": "Fechado", "Data da reunião": "2026-09-04",
                 "Responsável": "(sem responsável)"}
                for i in range(10)
            ],
            "por_marcacao": [
                {"Marcação no nome": "(sem marcação)", "Reuniões agendadas": 41, "Fechados": 6},
                {"Marcação no nome": "Tayron", "Reuniões agendadas": 5, "Fechados": 4},
            ],
            "por_responsavel": [
                {"Responsável": "Cláudio", "Reuniões agendadas": 6, "Fechados": 1},
            ],
            "motivos_perda": [{"Motivo": "Preço", "Quantidade": 7}],
        },
    }


# --------------------------------------------------------------------- #
# O arquivo
# --------------------------------------------------------------------- #
def test_sai_um_pdf_valido_com_conteudo(payload):
    dados = gerar_pdf(payload, empresa="Contabilidade Conforme", organizacao="Neriah Data")
    assert dados[:5] == b"%PDF-"
    assert len(dados) > 4000, "um relatório de várias páginas não é menor que isso"


def test_salva_no_caminho_pedido(payload, tmp_path):
    destino = tmp_path / "sub" / "mes.pdf"
    gerar_pdf(payload, empresa="X", destino=destino)
    assert destino.exists() and destino.read_bytes()[:5] == b"%PDF-"


def test_a_capa_identifica_mes_empresa_versao_e_data(payload):
    texto = texto_do_pdf(gerar_pdf(
        payload, empresa="Contabilidade Conforme", organizacao="Neriah Data",
        versao=2, emitido_em=date(2026, 11, 11),
    ))
    assert "setembro/2026" in texto
    assert "Contabilidade Conforme" in texto
    assert "versão 2" in texto
    assert "11/11/2026" in texto


# --------------------------------------------------------------------- #
# A seção 1 — o defeito que passou em silêncio
# --------------------------------------------------------------------- #
def test_os_indicadores_aparecem_com_blocos_no_formato_do_banco(payload):
    """No payload gravado cada bloco é um dicionário, não uma tupla.

    Desempacotar a tupla direto não quebrava nada: iterar o dicionário devolve
    as chaves, e a seção inteira saía VAZIA no PDF que o cliente recebia.
    """
    texto = texto_do_pdf(gerar_pdf(payload, empresa="X"))
    assert "Clientes fechados" in texto
    assert "Assertividade" in texto
    assert "Investimento" in texto
    assert "chaves" not in texto, "o nome da chave do dicionário vazando para o documento"


def test_os_fechados_por_marcacao_entram_no_relatorio(payload):
    """A separação do Tayron é o motivo de o cliente abrir este PDF."""
    texto = texto_do_pdf(gerar_pdf(payload, empresa="X"))
    assert "Tayron" in texto
    assert "Por marcação no nome" in texto


def test_meta_e_situacao_acompanham_o_indicador(payload):
    texto = texto_do_pdf(gerar_pdf(payload, empresa="X"))
    assert "mín. 30,0%" in texto


# --------------------------------------------------------------------- #
# Texto legível
# --------------------------------------------------------------------- #
def test_nao_sobra_emoji_no_documento(payload):
    """Helvetica não tem glifo de emoji: cada um vira um quadrado preto."""
    dados = gerar_pdf(payload, empresa="X")
    for emoji in ("✅", "🔴", "⚠️", "📈"):
        assert emoji.encode("utf-8") not in dados


def test_numeros_saem_com_a_pontuacao_brasileira(payload):
    texto = texto_do_pdf(gerar_pdf(payload, empresa="X"))
    assert "R$ 3.651,02" in texto
    assert "144.456" in texto, "br() só troca os separadores dentro de R$, % e x"
    assert "3,651.02" not in texto


def test_numero_formata_fora_de_reais_e_porcento():
    assert _numero(144456.0, "int") == "144.456"
    assert _numero(3651.02, "brl") == "R$ 3.651,02"
    assert _numero(0.227, "pct") == "22,7%"


# --------------------------------------------------------------------- #
# A situação repete o veredito estatístico da tela
# --------------------------------------------------------------------- #
def test_amostra_pequena_nao_vira_fora_da_meta():
    """A tela diz "ainda não dá para dizer"; o PDF não pode condenar o mês."""
    kpi = {"meta_tipo": "min", "dentro_da_meta": False, "faixa": {"veredito": "amostra_pequena"}}
    assert _situacao(kpi) == "ainda não dá para dizer"
    kpi["faixa"] = {"veredito": "fora"}
    assert _situacao(kpi) == "fora da meta"


def test_indicador_sem_meta_nao_inventa_julgamento():
    assert _situacao({"rotulo": "Leads", "faixa": {}}) == "—"


# --------------------------------------------------------------------- #
# As ressalvas
# --------------------------------------------------------------------- #
def test_os_avisos_da_leitura_entram_no_pdf(payload):
    texto = texto_do_pdf(gerar_pdf(payload, empresa="X"))
    assert "não tem coluna de valor" in texto


def test_o_pdf_diz_quais_campos_faltam_na_planilha(payload):
    texto = texto_do_pdf(gerar_pdf(payload, empresa="X"))
    assert "Valor do contrato" in texto and "Origem" in texto
    assert "6 de 8" in texto


# --------------------------------------------------------------------- #
# Resultado incompleto não derruba o relatório
# --------------------------------------------------------------------- #
def test_analise_sem_tabelas_ainda_gera_documento():
    magro = {"mes_referencia": "2026-09", "nome_mes": "setembro/2026", "kpis": {}, "blocos": []}
    dados = gerar_pdf(magro, empresa="Cliente Novo")
    assert dados[:5] == b"%PDF-"


def test_tabela_longa_avisa_que_foi_cortada(payload):
    payload["tabelas"]["fechamentos"] = [
        {"Cliente": f"Cliente {i}", "Marcação": "(sem marcação)", "Status na planilha": "Fechado",
         "Data da reunião": "2026-09-04", "Responsável": "—"}
        for i in range(40)
    ]
    texto = texto_do_pdf(gerar_pdf(payload, empresa="X"))
    assert "de 40 linhas" in texto


# --------------------------------------------------------------------- #
# A tela
# --------------------------------------------------------------------- #
def _fonte(caminho: str) -> str:
    from pathlib import Path as _P

    return (_P(__file__).resolve().parents[2] / "frontend" / "src" / caminho).read_text(
        encoding="utf-8"
    )


def test_a_tela_da_analise_oferece_o_download_do_pdf():
    """Sem o botão, a rota existe e ninguém chega nela."""
    pagina = _fonte("pages/Analise.tsx")
    assert "baixarAnalisePdf" in pagina
    assert "Baixar PDF" in pagina
    assert "Baixar planilha (.xlsx)" in pagina, "o PDF acrescenta, não substitui a planilha"


def test_a_api_do_front_aponta_para_a_rota_do_pdf():
    assert '`/analises/${id}/pdf`' in _fonte("api.ts")


def test_um_download_de_cada_vez_nao_trava_o_outro_botao():
    """Um booleano só escrevia "Gerando…" nos dois botões ao mesmo tempo."""
    pagina = _fonte("pages/Analise.tsx")
    assert 'useState<"xlsx" | "pdf" | null>(null)' in pagina
    assert 'baixando === "pdf"' in pagina


def test_o_titulo_do_bloco_nao_levanta_as_palavras_de_ligacao():
    from app.core.pdf_analise import _titulo_de_bloco

    assert _titulo_de_bloco("COMERCIAL — TODAS AS ORIGENS") == "Comercial — Todas as Origens"
    assert _titulo_de_bloco("TRÁFEGO PAGO (META)") == "Tráfego Pago (Meta)"


def test_o_valor_do_indicador_e_o_mesmo_texto_da_tela():
    """Recalcular aqui é como tela e PDF passam a discordar no arredondamento."""
    from app.core.pdf_analise import _valor

    assert _valor({"rotulo": "x", "valor": 1.7608, "formato": "num", "texto": "1,8"}) == "1,8"
    assert _valor({"rotulo": "x", "valor": 1.7608, "formato": "num"}) == "1,8", "sem texto, calcula"


def test_numero_decimal_nao_perde_a_virgula():
    """fmt("num") já devolve a pontuação brasileira; traduzir de novo faz "1.8"."""
    assert _numero(1.7608, "num") == "1,8"


def test_emoji_do_diagnostico_tambem_sai():
    """A seção 2 não passava pelo filtro e a estrela virava quadrado preto."""
    payload = {
        "mes_referencia": "2026-09", "nome_mes": "setembro/2026", "kpis": {}, "blocos": [],
        "diagnostico": [{"Nível": "⚠️ Abaixo da meta", "Diagnóstico": "⭐ ASSERTIVIDADE: 22,7%"}],
    }
    dados = gerar_pdf(payload, empresa="X")
    assert "⭐".encode("utf-8") not in dados
    assert "ASSERTIVIDADE" in texto_do_pdf(dados)
