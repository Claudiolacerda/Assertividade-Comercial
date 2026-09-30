"""Fluxos de cadência: modelos, sugestão a partir da análise, e o canvas salvo."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from ..core.cadencia import MODELOS, modelo, sugerir_de_analise
from ..db import sessao_tenant
from ..deps import Atual, usuario_atual
from ..models import Analise, Cadencia
from ..schemas import CadenciaDetalhe, CadenciaIn, CadenciaResumo, NovaCadencia

router = APIRouter(prefix="/api/cadencias", tags=["cadência"])


@router.get("/modelos")
def listar_modelos():
    """Modelos prontos, para quem não quer começar do zero."""
    return [
        {"chave": c, "nome": m["nome"], "descricao": m["descricao"], "etapas": len(m["etapas"])}
        for c, m in MODELOS.items()
    ]


@router.get("", response_model=list[CadenciaResumo])
def listar(atual: Atual = Depends(usuario_atual)):
    with sessao_tenant(atual.schema) as st:
        itens = st.scalars(
            select(Cadencia).where(Cadencia.ativa.is_(True)).order_by(Cadencia.atualizada_em.desc())
        ).all()
        return [
            CadenciaResumo(
                id=c.id,
                nome=c.nome,
                descricao=c.descricao,
                etapas=len((c.fluxo or {}).get("nos") or []),
                atualizada_em=c.atualizada_em,
            )
            for c in itens
        ]


@router.post("", response_model=CadenciaDetalhe, status_code=status.HTTP_201_CREATED)
def criar(dados: NovaCadencia, atual: Atual = Depends(usuario_atual)):
    """Cria em branco, a partir de um modelo, ou sugerida por uma análise."""
    base: dict = {"nome": dados.nome or "Nova cadência", "descricao": None, "fluxo": {"nos": [], "ligacoes": []}}
    origem = None

    if dados.modelo:
        if dados.modelo not in MODELOS:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo não encontrado.")
        base = modelo(dados.modelo)
    elif dados.analise_id:
        with sessao_tenant(atual.schema) as st:
            analise = st.get(Analise, dados.analise_id)
            if analise is None or not analise.resultado:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada.")
            sugerida = sugerir_de_analise(analise.resultado)
        origem = {"analise_id": dados.analise_id, "motivos": sugerida.get("origem", [])}
        base = {"nome": sugerida["nome"], "descricao": sugerida["descricao"], "fluxo": sugerida["fluxo"]}

    if dados.nome:
        base["nome"] = dados.nome

    with sessao_tenant(atual.schema) as st:
        cadencia = Cadencia(
            nome=base["nome"],
            descricao=base.get("descricao"),
            fluxo=base["fluxo"],
            origem=origem,
            criada_por=atual.usuario.id,
        )
        st.add(cadencia)
        st.flush()
        return CadenciaDetalhe.model_validate(cadencia)


@router.get("/{cadencia_id}", response_model=CadenciaDetalhe)
def detalhar(cadencia_id: int, atual: Atual = Depends(usuario_atual)):
    with sessao_tenant(atual.schema) as st:
        c = st.get(Cadencia, cadencia_id)
        if c is None or not c.ativa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadência não encontrada.")
        return CadenciaDetalhe.model_validate(c)


@router.put("/{cadencia_id}", response_model=CadenciaDetalhe)
def salvar(cadencia_id: int, dados: CadenciaIn, atual: Atual = Depends(usuario_atual)):
    with sessao_tenant(atual.schema) as st:
        c = st.get(Cadencia, cadencia_id)
        if c is None or not c.ativa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadência não encontrada.")
        if dados.nome is not None:
            c.nome = dados.nome
        if dados.descricao is not None:
            c.descricao = dados.descricao
        if dados.fluxo is not None:
            c.fluxo = dados.fluxo
        st.flush()
        return CadenciaDetalhe.model_validate(c)


@router.delete("/{cadencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(cadencia_id: int, atual: Atual = Depends(usuario_atual)):
    with sessao_tenant(atual.schema) as st:
        c = st.get(Cadencia, cadencia_id)
        if c is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadência não encontrada.")
        # arquiva em vez de apagar: cadência costuma ser reaproveitada
        c.ativa = False
