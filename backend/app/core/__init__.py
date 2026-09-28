"""Motor de análise de assertividade comercial (Meta Ads × planilha comercial)."""

from .config_analise import ConfigAnalise
from .excel import gerar_excel
from .pipeline import ErroDeAnalise, Resultado, analisar

__all__ = ["ConfigAnalise", "Resultado", "ErroDeAnalise", "analisar", "gerar_excel"]
