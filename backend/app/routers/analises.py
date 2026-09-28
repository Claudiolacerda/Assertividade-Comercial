"""Upload das planilhas, execução da análise, histórico e export do Excel."""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..core import ConfigAnalise, analisar, gerar_excel
from ..core.pipeline import ErroDeAnalise
from ..db import get_db, sessao_tenant
from ..deps import Atual, admin_atual, usuario_atual
from ..models import Analise, Arquivo, Empresa
from ..schemas import AnaliseDetalhe, AnaliseResumo, ConfigAnaliseIn

router = APIRouter(prefix="/api/analises", tags=["análises"])

EXT_META = {".csv", ".xlsx"}
EXT_REUNIOES = {".csv", ".xlsx", ".xlsm", ".xls"}
# KPIs guardados achatados para o gráfico de evolução entre meses
KPIS_EVOLUCAO = [
    "inv", "leads", "cpl", "ctr", "ag", "real", "fec", "assert", "cac", "roas", "rec", "cpr", "l2r",
]


def _pasta(atual: Atual, mes: str) -> Path:
    destino = Path(settings.dir_uploads) / atual.empresa.slug / mes
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _salvar(arquivo: UploadFile, destino: Path, extensoes: set[str]) -> tuple[Path, int, str]:
    nome = Path(arquivo.filename or "arquivo").name  # descarta qualquer caminho vindo do cliente
    ext = Path(nome).suffix.lower()
    if ext not in extensoes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{nome}': formato {ext or 'desconhecido'} não aceito. Envie {', '.join(sorted(extensoes))}.",
        )
    limite = settings.tamanho_max_upload_mb * 1024 * 1024
    caminho = destino / nome
    md5 = hashlib.md5()
    tamanho = 0
    with caminho.open("wb") as saida:
        while pedaco := arquivo.file.read(1024 * 1024):
            tamanho += len(pedaco)
            if tamanho > limite:
                saida.close()
                caminho.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"'{nome}' passa de {settings.tamanho_max_upload_mb} MB.",
                )
            md5.update(pedaco)
            saida.write(pedaco)
    if tamanho == 0:
        caminho.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{nome}' está vazio.")
    return caminho, tamanho, md5.hexdigest()


def _resumir(res) -> dict[str, float]:
    return {k: res.kpi(k) for k in KPIS_EVOLUCAO if k in res.kpis}


@router.post("", response_model=AnaliseDetalhe, status_code=status.HTTP_201_CREATED)
def criar_analise(
    arquivos_meta: list[UploadFile] = File(..., description="CSV/XLSX exportado do Gerenciador de Anúncios"),
    arquivos_reunioes: list[UploadFile] = File(..., description="Planilha de assertividade comercial"),
    mes_referencia: str | None = Form(None, description='"2026-09" ou vazio para detectar automaticamente'),
    atual: Atual = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    """Recebe as planilhas, roda a análise e guarda o resultado no schema da empresa."""
    if mes_referencia:
        mes_referencia = mes_referencia.strip()
        try:
            datetime.strptime(mes_referencia, "%Y-%m")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mês de referência deve estar no formato AAAA-MM (ex.: 2026-09).",
            ) from None

    provisoria = _pasta(atual, mes_referencia or "_detectando")
    salvos: list[tuple[Path, int, str, str]] = []
    try:
        for arq in arquivos_meta:
            caminho, tam, md5 = _salvar(arq, provisoria, EXT_META)
            salvos.append((caminho, tam, md5, "meta"))
        for arq in arquivos_reunioes:
            caminho, tam, md5 = _salvar(arq, provisoria, EXT_REUNIOES)
            salvos.append((caminho, tam, md5, "reunioes"))

        cfg = ConfigAnalise.from_dict(atual.empresa.config_analise)
        if mes_referencia:
            cfg.mes_referencia = mes_referencia
        try:
            res = analisar(
                [c for c, _, _, t in salvos if t == "meta"],
                [c for c, _, _, t in salvos if t == "reunioes"],
                cfg,
            )
        except ErroDeAnalise as e:
            # Erro que o cliente resolve na planilha: devolve a mensagem dele, não um 500.
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

        # Agora que o mês é conhecido, move os arquivos para a pasta definitiva
        definitiva = _pasta(atual, res.mes_referencia)
        if definitiva != provisoria:
            movidos = []
            for caminho, tam, md5, tipo in salvos:
                novo = definitiva / caminho.name
                shutil.move(str(caminho), novo)
                movidos.append((novo, tam, md5, tipo))
            salvos = movidos
            if not any(provisoria.iterdir()):
                provisoria.rmdir()

        with sessao_tenant(atual.schema) as st:
            versao = (
                st.scalar(
                    select(Analise.versao)
                    .where(Analise.mes_referencia == res.mes_referencia)
                    .order_by(Analise.versao.desc())
                    .limit(1)
                )
                or 0
            ) + 1
            analise = Analise(
                mes_referencia=res.mes_referencia,
                versao=versao,
                status="concluida",
                resultado=res.to_payload(),
                kpis_resumo=_resumir(res),
                config_usada=cfg.to_dict(),
                criada_por=atual.usuario.id,
                concluida_em=datetime.now(timezone.utc),
            )
            st.add(analise)
            st.flush()

            caminho_excel = definitiva / f"Assertividade_{res.mes_referencia}_v{versao}.xlsx"
            gerar_excel(res, caminho_excel)
            analise.caminho_excel = str(caminho_excel)

            for caminho, tam, md5, tipo in salvos:
                st.add(
                    Arquivo(
                        analise_id=analise.id,
                        tipo=tipo,
                        nome_original=caminho.name,
                        caminho=str(caminho),
                        tamanho_bytes=tam,
                        hash_md5=md5,
                        enviado_por=atual.usuario.id,
                    )
                )
            st.flush()
            return AnaliseDetalhe.model_validate(analise)
    except HTTPException:
        raise
    except Exception as e:  # falha inesperada: não deixa arquivo órfão sem registro
        for caminho, *_ in salvos:
            Path(caminho).unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível concluir a análise: {e}",
        ) from e


@router.get("", response_model=list[AnaliseResumo])
def listar(atual: Atual = Depends(usuario_atual)):
    """Histórico da empresa, mais recente primeiro."""
    with sessao_tenant(atual.schema) as st:
        analises = st.scalars(
            select(Analise).order_by(Analise.mes_referencia.desc(), Analise.versao.desc())
        ).all()
        return [AnaliseResumo.model_validate(a) for a in analises]


@router.get("/evolucao")
def evolucao(atual: Atual = Depends(usuario_atual)):
    """Série mês a mês (última versão de cada mês) — é o gráfico de tendência do painel."""
    with sessao_tenant(atual.schema) as st:
        analises = st.scalars(
            select(Analise)
            .where(Analise.status == "concluida")
            .order_by(Analise.mes_referencia.asc(), Analise.versao.asc())
        ).all()
        por_mes: dict[str, dict] = {}
        for a in analises:  # versão maior sobrescreve a anterior do mesmo mês
            por_mes[a.mes_referencia] = {
                "mes_referencia": a.mes_referencia,
                "analise_id": a.id,
                **(a.kpis_resumo or {}),
            }
        return {"meses": list(por_mes.values()), "kpis": KPIS_EVOLUCAO}


@router.get("/{analise_id}", response_model=AnaliseDetalhe)
def detalhar(analise_id: int, atual: Atual = Depends(usuario_atual)):
    with sessao_tenant(atual.schema) as st:
        analise = st.get(Analise, analise_id)
        if analise is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada.")
        return AnaliseDetalhe.model_validate(analise)


@router.get("/{analise_id}/excel")
def baixar_excel(analise_id: int, atual: Atual = Depends(usuario_atual)):
    """Baixa a planilha formatada. Se o arquivo não existir mais no disco, regenera."""
    with sessao_tenant(atual.schema) as st:
        analise = st.get(Analise, analise_id)
        if analise is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada.")
        nome = f"Assertividade_{analise.mes_referencia}_v{analise.versao}.xlsx"
        if analise.caminho_excel and Path(analise.caminho_excel).exists():
            dados = Path(analise.caminho_excel).read_bytes()
        else:
            arquivos = st.scalars(select(Arquivo).where(Arquivo.analise_id == analise.id)).all()
            meta = [a.caminho for a in arquivos if a.tipo == "meta" and Path(a.caminho).exists()]
            reun = [a.caminho for a in arquivos if a.tipo == "reunioes" and Path(a.caminho).exists()]
            if not meta or not reun:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="A planilha desta análise não está mais disponível. Rode a análise novamente.",
                )
            res = analisar(meta, reun, ConfigAnalise.from_dict(analise.config_usada))
            dados = gerar_excel(res, analise.caminho_excel)
        return Response(
            content=dados,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{nome}"'},
        )


@router.delete("/{analise_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(analise_id: int, atual: Atual = Depends(admin_atual)):
    with sessao_tenant(atual.schema) as st:
        analise = st.get(Analise, analise_id)
        if analise is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada.")
        for arq in st.scalars(select(Arquivo).where(Arquivo.analise_id == analise.id)).all():
            Path(arq.caminho).unlink(missing_ok=True)
        if analise.caminho_excel:
            Path(analise.caminho_excel).unlink(missing_ok=True)
        st.delete(analise)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Configuração da empresa ------------------------------------------------ #
config_router = APIRouter(prefix="/api/configuracao", tags=["configuração"])


@config_router.get("")
def ler_config(atual: Atual = Depends(usuario_atual)):
    cfg = ConfigAnalise.from_dict(atual.empresa.config_analise)
    return {
        "metas": cfg.metas,
        "marcacoes_nao_pagas": cfg.marcacoes_nao_pagas,
        "classificar_perda_pela_observacao": cfg.classificar_perda_pela_observacao,
        "prob_fechamento_negociacao": cfg.prob_fechamento_negociacao,
        "dias_alerta_pipeline": cfg.dias_alerta_pipeline,
        "origens_trafego_pago": cfg.origens_trafego_pago,
        "sem_origem_considerar_pago": cfg.sem_origem_considerar_pago,
        "coluna_leads_meta": cfg.coluna_leads_meta,
        "status_manual": cfg.status_manual,
    }


@config_router.put("")
def salvar_config(dados: ConfigAnaliseIn, atual: Atual = Depends(admin_atual), db: Session = Depends(get_db)):
    """Salva metas e ajustes da empresa. Vale para as próximas análises."""
    atualizacao = dados.apenas_preenchidos()
    if "metas" in atualizacao:
        validas = set(ConfigAnalise().metas)
        desconhecidas = set(atualizacao["metas"]) - validas
        if desconhecidas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Metas desconhecidas: {', '.join(sorted(desconhecidas))}.",
            )
    empresa = db.get(Empresa, atual.empresa.id)
    atual_cfg = ConfigAnalise.from_dict(empresa.config_analise).to_dict()
    if "metas" in atualizacao:
        atualizacao["metas"] = {**atual_cfg["metas"], **atualizacao["metas"]}
    empresa.config_analise = {**atual_cfg, **atualizacao}
    db.commit()
    return ler_config(atual)
