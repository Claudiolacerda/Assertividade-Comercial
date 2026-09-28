"""A carteira: os clientes que uma organização analisa.

É a tela que faltava para o comprador real do Neriah — o gestor de tráfego que
atende dez contas e precisa ver as dez num lugar só, em vez de dez logins.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db, sessao_tenant
from ..deps import Sessao, admin_sessao, empresas_visiveis, sessao_atual
from ..models import Analise, Empresa
from ..schemas import EmpresaOut, ItemCarteira, NovaEmpresa
from .auth import criar_empresa

router = APIRouter(prefix="/api/empresas", tags=["carteira"])

# Indicadores mostrados na carteira, em ordem de importância para o gestor
KPIS_CARTEIRA = ["assert", "cac", "cpl", "inv", "fec", "roas"]


@router.get("", response_model=list[EmpresaOut])
def listar(sessao: Sessao = Depends(sessao_atual), db: Session = Depends(get_db)):
    """Clientes que este usuário pode abrir."""
    return [EmpresaOut.model_validate(e) for e in empresas_visiveis(db, sessao)]


@router.get("/carteira", response_model=list[ItemCarteira])
def carteira(sessao: Sessao = Depends(sessao_atual), db: Session = Depends(get_db)):
    """Visão geral: a última análise de cada cliente, com a variação sobre o mês anterior.

    Consulta o schema de cada empresa separadamente. São N consultas pequenas —
    aceitável para uma carteira de dezenas de clientes, que é a escala real aqui.
    """
    itens: list[ItemCarteira] = []
    for empresa in empresas_visiveis(db, sessao):
        item = ItemCarteira(empresa=EmpresaOut.model_validate(empresa))
        try:
            with sessao_tenant(empresa.schema_banco) as st:
                item.total_analises = st.scalar(select(func.count(Analise.id))) or 0
                # última versão de cada um dos dois últimos meses
                recentes = st.scalars(
                    select(Analise)
                    .where(Analise.status == "concluida")
                    .order_by(Analise.mes_referencia.desc(), Analise.versao.desc())
                    .limit(6)
                ).all()
                por_mes: dict[str, Analise] = {}
                for a in recentes:
                    por_mes.setdefault(a.mes_referencia, a)
                meses = sorted(por_mes, reverse=True)
                if meses:
                    atual = por_mes[meses[0]]
                    item.ultima_analise_id = atual.id
                    item.ultimo_mes = atual.mes_referencia
                    item.kpis = {k: v for k, v in (atual.kpis_resumo or {}).items() if k in KPIS_CARTEIRA}
                    if len(meses) > 1:
                        anterior = por_mes[meses[1]].kpis_resumo or {}
                        item.variacao = {
                            k: round(item.kpis[k] - anterior[k], 6)
                            for k in item.kpis
                            if k in anterior and anterior[k] is not None and item.kpis[k] is not None
                        }
        except Exception as e:  # um cliente com problema não pode derrubar a carteira inteira
            item.erro = f"Não consegui ler os dados deste cliente: {e}"
        itens.append(item)

    # quem tem análise primeiro; depois por nome
    itens.sort(key=lambda i: (i.ultimo_mes is None, i.empresa.nome))
    return itens


@router.post("", response_model=EmpresaOut, status_code=status.HTTP_201_CREATED)
def adicionar(dados: NovaEmpresa, sessao: Sessao = Depends(admin_sessao), db: Session = Depends(get_db)):
    """Adiciona um cliente à carteira — cria o schema isolado dele no banco."""
    nome = dados.nome.strip()
    ja_existe = db.scalar(
        select(Empresa.id).where(
            Empresa.organizacao_id == sessao.organizacao.id, func.lower(Empresa.nome) == nome.lower()
        )
    )
    if ja_existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Já existe um cliente com esse nome na sua carteira."
        )
    empresa = criar_empresa(db, sessao.organizacao, nome, dados.segmento)
    db.commit()
    return EmpresaOut.model_validate(empresa)


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def arquivar(empresa_id: int, sessao: Sessao = Depends(admin_sessao), db: Session = Depends(get_db)):
    """Tira o cliente da carteira.

    Só marca como inativo: o schema e as análises continuam no banco. Apagar dado
    de cliente é decisão consciente, não efeito colateral de um clique — e a LGPD
    pede que a exclusão definitiva seja um pedido explícito.
    """
    empresa = db.get(Empresa, empresa_id)
    if empresa is None or empresa.organizacao_id != sessao.organizacao.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    restantes = db.scalar(
        select(func.count(Empresa.id)).where(
            Empresa.organizacao_id == sessao.organizacao.id, Empresa.ativa.is_(True)
        )
    )
    if restantes <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sua carteira ficaria vazia. Adicione outro cliente antes de arquivar este.",
        )
    empresa.ativa = False
    db.commit()
