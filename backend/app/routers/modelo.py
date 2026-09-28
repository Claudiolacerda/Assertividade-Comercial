"""Download da planilha-modelo.

Sem autenticação de propósito: o arquivo não tem dado de ninguém e serve também
como isca no site — quem baixa o modelo já está a um passo de subir a planilha.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from ..core.config_analise import CAMPOS_REUNIOES_INFO, ETAPAS_SUGERIDAS
from ..core.modelo import gerar_planilha_modelo

router = APIRouter(prefix="/api/modelo", tags=["modelo"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/planilha-comercial.xlsx")
def baixar_modelo():
    """Planilha pronta com as colunas que o sistema reconhece e lista de etapas."""
    dados = gerar_planilha_modelo()
    return Response(
        content=dados,
        media_type=XLSX,
        headers={
            "Content-Disposition": 'attachment; filename="Modelo_Comercial_Neriah.xlsx"',
            # o conteúdo só muda quando a versão muda: pode ficar em cache
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/campos")
def campos():
    """O que o sistema entende — alimenta a tela de ajuda e a nota da planilha."""
    return {
        "campos": [
            {"campo": c, "rotulo": i["rotulo"], "destrava": i["destrava"], "impacto": i["impacto"]}
            for c, i in CAMPOS_REUNIOES_INFO.items()
        ],
        "etapas": ETAPAS_SUGERIDAS,
    }
