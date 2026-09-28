"""Aplicação FastAPI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .db import criar_schemas_base
from .routers import analises, auth

log = logging.getLogger("assertividade")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    criar_schemas_base()
    settings.dir_uploads.mkdir(parents=True, exist_ok=True)
    log.info("Banco pronto. Ambiente: %s", settings.ambiente)
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "Cruza o relatório de tráfego da Meta com a planilha de assertividade comercial "
        "e devolve KPIs, diagnóstico automático e a planilha formatada."
    ),
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.lista_origens,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analises.router)
app.include_router(analises.config_router)


@app.exception_handler(ValueError)
async def erro_de_valor(request: Request, exc: ValueError):
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


@app.get("/api/saude", tags=["infra"])
def saude():
    return {"status": "ok", "ambiente": settings.ambiente}
