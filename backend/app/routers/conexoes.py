"""Conexões com o CRM do cliente: cadastro, teste e importação.

O token nunca sai daqui. Os esquemas de saída não têm o campo, a listagem
devolve só se existe um token guardado, e a edição aceita token vazio
querendo dizer "mantém o que já está lá" — assim a tela consegue editar o
endereço sem pedir o segredo de novo.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from ..core.conectores import (
    CONECTORES,
    Credencial,
    ErroDeConexao,
    Periodo,
    escrever_csv,
    montar,
)
from ..core.conectores.base import COLUNAS_SAIDA
from ..db import sessao_tenant
from ..deps import Atual, admin_atual, usuario_atual
from ..models import ConexaoCrm
from ..schemas import ConexaoIn, ConexaoOut, ConexaoUp
from ..security import SegredoIlegivel, cifrar, decifrar

router = APIRouter(prefix="/api/conexoes", tags=["conexões"])


def _periodo_do_mes(mes: str) -> Periodo:
    try:
        referencia = datetime.strptime(mes, "%Y-%m").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O mês deve estar no formato AAAA-MM (ex.: 2026-09).",
        ) from None
    ultimo = calendar.monthrange(referencia.year, referencia.month)[1]
    return Periodo(de=referencia, ate=referencia.replace(day=ultimo))


def _conector_de(conexao: ConexaoCrm):
    try:
        token = decifrar(conexao.token_cifrado)
    except SegredoIlegivel as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    try:
        return montar(conexao.provedor, Credencial(token=token), conexao.config or {})
    except ErroDeConexao as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


def _anotar(schema: str, conexao_id: int, erro: str | None) -> None:
    """Grava o desfecho da última chamada, em transação própria.

    Transação própria porque o caminho de erro termina em HTTPException, e a
    sessão em que a conexão está carregada faz rollback ao subir a exceção —
    levando embora justamente a anotação do erro. Era por isso que a tela
    nunca dizia desde quando a conexão parou: a informação existia por um
    instante e era desfeita junto com a falha.
    """
    with sessao_tenant(schema) as st:
        conexao = st.get(ConexaoCrm, conexao_id)
        if conexao is None:
            return
        conexao.ultimo_erro = erro[:1000] if erro else None
        if erro is None:
            conexao.ultima_importacao = datetime.now(timezone.utc)


def _avisos_do_mapa(conexao: ConexaoCrm) -> list[str]:
    """Mapa sem nenhuma data faz o negócio em aberto sumir do mês, calado.

    O motor situa cada linha no tempo por alguma data. Um mapa que só traz a
    data de fechamento descreve bem quem fechou e deixa todo o resto sem lugar
    no calendário — e o que some é exatamente o denominador das taxas.
    """
    campos = set((conexao.config or {}).get("campos") or {})
    if conexao.provedor != "generico":
        return []
    if not campos & {"Data do lead", "Data da reunião"}:
        return [
            (
                "O mapa desta conexão não traz 'Data do lead' nem 'Data da reunião'. "
                "Negócios ainda em aberto não têm data nenhuma e ficam de fora do mês — "
                "o que derruba o denominador de todas as taxas. Aponte uma das duas."
            )
        ]
    return []


def _buscar(conexao: ConexaoCrm, periodo: Periodo, schema: str):
    """Chama o CRM e registra o desfecho na conexão."""
    conector = _conector_de(conexao)
    try:
        importacao = conector.buscar(periodo)
    except ErroDeConexao as e:
        _anotar(schema, conexao.id, str(e))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    _anotar(schema, conexao.id, None)
    importacao.avisos = list(importacao.avisos) + _avisos_do_mapa(conexao)
    return importacao


def importar_para_arquivo(conexao: ConexaoCrm, mes: str, destino_pasta, schema: str) -> tuple:
    """Busca o mês no CRM e grava o CSV. Usado pelo roteador de análises."""
    importacao = _buscar(conexao, _periodo_do_mes(mes), schema)
    if not importacao.linhas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"O CRM não devolveu nenhum negócio para {mes}. Confira o período e os "
                "filtros da conexão."
            ),
        )
    nome = f"{conexao.provedor}_{mes}.csv"
    caminho = escrever_csv(importacao, destino_pasta / nome)
    return caminho, importacao


# --------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------- #
@router.get("/provedores")
def provedores(_: Atual = Depends(usuario_atual)):
    """O que a tela precisa para montar o formulário de cada CRM."""
    return {
        "colunas": COLUNAS_SAIDA,
        "provedores": [
            {"nome": c.nome, "rotulo": c.rotulo, "ajuda": c.ajuda}
            for c in sorted(CONECTORES.values(), key=lambda c: c.rotulo)
        ],
    }


# --------------------------------------------------------------------- #
# Cadastro
# --------------------------------------------------------------------- #
@router.get("", response_model=list[ConexaoOut])
def listar(atual: Atual = Depends(usuario_atual)):
    with sessao_tenant(atual.schema) as st:
        conexoes = st.scalars(select(ConexaoCrm).order_by(ConexaoCrm.nome)).all()
        return [ConexaoOut.de(c) for c in conexoes]


@router.post("", response_model=ConexaoOut, status_code=status.HTTP_201_CREATED)
def criar(dados: ConexaoIn, atual: Atual = Depends(admin_atual)):
    if dados.provedor not in CONECTORES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CRM desconhecido: {dados.provedor!r}. Os disponíveis são: "
            + ", ".join(sorted(CONECTORES)) + ".",
        )
    with sessao_tenant(atual.schema) as st:
        if st.scalar(select(ConexaoCrm.id).where(ConexaoCrm.nome == dados.nome.strip())):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe uma conexão chamada {dados.nome.strip()!r}.",
            )
        conexao = ConexaoCrm(
            nome=dados.nome.strip(),
            provedor=dados.provedor,
            token_cifrado=cifrar(dados.token),
            config=dados.config,
            criada_por=atual.usuario.id,
        )
        st.add(conexao)
        st.flush()
        return ConexaoOut.de(conexao)


@router.put("/{conexao_id}", response_model=ConexaoOut)
def editar(conexao_id: int, dados: ConexaoUp, atual: Atual = Depends(admin_atual)):
    with sessao_tenant(atual.schema) as st:
        conexao = st.get(ConexaoCrm, conexao_id)
        if conexao is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexão não encontrada.")
        if dados.nome is not None:
            conexao.nome = dados.nome.strip()
        if dados.config is not None:
            conexao.config = dados.config
        if dados.ativa is not None:
            conexao.ativa = dados.ativa
        # Token vazio quer dizer "não mexe": é o que permite corrigir o
        # endereço sem obrigar a pessoa a ir buscar o segredo de novo.
        if dados.token:
            conexao.token_cifrado = cifrar(dados.token)
            conexao.ultimo_erro = None
        st.flush()
        return ConexaoOut.de(conexao)


@router.delete("/{conexao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(conexao_id: int, atual: Atual = Depends(admin_atual)):
    with sessao_tenant(atual.schema) as st:
        conexao = st.get(ConexaoCrm, conexao_id)
        if conexao is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexão não encontrada.")
        st.delete(conexao)


# --------------------------------------------------------------------- #
# Usar
# --------------------------------------------------------------------- #
@router.post("/{conexao_id}/testar")
def testar(conexao_id: int, atual: Atual = Depends(usuario_atual)):
    """Bate no CRM agora e diz o que voltou, antes de depender disso numa análise."""
    hoje = date.today()
    with sessao_tenant(atual.schema) as st:
        conexao = st.get(ConexaoCrm, conexao_id)
        if conexao is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexão não encontrada.")
        importacao = _buscar(conexao, Periodo(de=hoje.replace(day=1), ate=hoje), atual.schema)
        preenchidas = sorted(
            {c for linha in importacao.linhas for c, v in linha.items() if v not in (None, "")}
        )
        return {
            "ok": True,
            "quantidade": importacao.quantidade,
            "paginas": importacao.paginas,
            "colunas_preenchidas": preenchidas,
            "colunas_vazias": [c for c in COLUNAS_SAIDA if c not in preenchidas],
            "avisos": importacao.avisos,
            "amostra": importacao.linhas[:3],
        }


@router.post("/{conexao_id}/importar")
def importar(conexao_id: int, mes: str, atual: Atual = Depends(usuario_atual)):
    """Puxa o mês e grava o CSV, sem rodar análise — para conferir o arquivo antes."""
    from pathlib import Path

    from ..config import settings

    with sessao_tenant(atual.schema) as st:
        conexao = st.get(ConexaoCrm, conexao_id)
        if conexao is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexão não encontrada.")
        pasta = Path(settings.dir_uploads) / atual.empresa.slug / mes
        pasta.mkdir(parents=True, exist_ok=True)
        caminho, importacao = importar_para_arquivo(conexao, mes, pasta, atual.schema)
        return {
            "arquivo": caminho.name,
            "quantidade": importacao.quantidade,
            "paginas": importacao.paginas,
            "avisos": importacao.avisos,
        }
