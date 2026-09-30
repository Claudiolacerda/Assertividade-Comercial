"""Relatório de WhatsApp: gerar, revisar e enviar."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.relatorio_zap import gerar_texto
from ..db import get_db, sessao_tenant
from ..deps import Atual, admin_atual, usuario_atual
from ..envio_zap import ErroEnvio, enviar, link_whatsapp, provedor_configurado
from ..models import Analise, Empresa
from ..schemas import EnvioZap, RelatorioZap, TextoZap

router = APIRouter(prefix="/api/analises", tags=["relatório"])


def _montar(atual: Atual, analise_id: int, completo: bool) -> tuple[str, Analise]:
    with sessao_tenant(atual.schema) as st:
        analise = st.get(Analise, analise_id)
        if analise is None or not analise.resultado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada.")

        # KPIs do mês anterior, para o relatório poder dizer "melhor" ou "pior"
        anterior = st.scalars(
            select(Analise)
            .where(Analise.status == "concluida", Analise.mes_referencia < analise.mes_referencia)
            .order_by(Analise.mes_referencia.desc(), Analise.versao.desc())
            .limit(1)
        ).first()

        texto = gerar_texto(
            analise.resultado,
            nome_cliente=atual.empresa.nome,
            mes_referencia=analise.mes_referencia,
            kpis_anteriores=anterior.kpis_resumo if anterior else None,
            completo=completo,
            assinatura=f"_Relatório gerado por {atual.organizacao.nome} · Neriah Data._",
        )
        return texto, analise


@router.get("/{analise_id}/whatsapp", response_model=RelatorioZap)
def previa(analise_id: int, completo: bool = False, atual: Atual = Depends(usuario_atual)):
    """Texto pronto para revisão, com o link que abre o WhatsApp já preenchido."""
    texto, _ = _montar(atual, analise_id, completo)
    return RelatorioZap(
        texto=texto,
        link=link_whatsapp(atual.empresa.whatsapp, texto),
        numero=atual.empresa.whatsapp,
        envio_automatico=bool(provedor_configurado()),
        provedor=provedor_configurado() or None,
    )


@router.post("/{analise_id}/whatsapp/enviar")
def mandar(analise_id: int, dados: EnvioZap, atual: Atual = Depends(usuario_atual)):
    """Envia pelo provedor configurado.

    O texto vem do cliente porque a tela permite editar antes de mandar — quem
    assina o relatório é a agência, não o gerador.
    """
    numero = (dados.numero or atual.empresa.whatsapp or "").strip()
    if not numero:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o WhatsApp do cliente ou salve um número na configuração.",
        )
    texto = (dados.texto or "").strip()
    if not texto:
        texto, _ = _montar(atual, analise_id, dados.completo)
    try:
        resultado = enviar(numero, texto)
    except ErroEnvio as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return {"sucesso": resultado.sucesso, "provedor": resultado.provedor, "detalhe": resultado.detalhe}


# --------------------------------------------------------------------------- #
# WhatsApp do cliente
# --------------------------------------------------------------------------- #
zap_router = APIRouter(prefix="/api/whatsapp", tags=["relatório"])


@zap_router.get("")
def situacao(atual: Atual = Depends(usuario_atual)):
    return {
        "numero": atual.empresa.whatsapp,
        "envio_automatico": bool(provedor_configurado()),
        "provedor": provedor_configurado() or None,
    }


@zap_router.put("")
def salvar_numero(dados: TextoZap, atual: Atual = Depends(admin_atual), db: Session = Depends(get_db)):
    """Guarda o WhatsApp de destino deste cliente."""
    empresa = db.get(Empresa, atual.empresa.id)
    numero = (dados.numero or "").strip()
    if numero:
        from ..envio_zap import normalizar_numero

        try:
            normalizar_numero(numero)  # valida antes de gravar
        except ErroEnvio as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    empresa.whatsapp = numero or None
    db.commit()
    return {"numero": empresa.whatsapp}
