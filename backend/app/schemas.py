"""Contratos de entrada e saída da API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---- Autenticação ----------------------------------------------------------- #
class CadastroEmpresa(BaseModel):
    empresa: str = Field(min_length=2, max_length=160)
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("A senha deve misturar letras e números.")
        return v


class Login(BaseModel):
    email: EmailStr
    senha: str


class NovoUsuario(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    papel: str = Field(default="membro", pattern="^(admin|membro)$")


class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    slug: str
    plano: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    papel: str
    empresa: EmpresaOut


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ---- Análises --------------------------------------------------------------- #
class AnaliseResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mes_referencia: str
    versao: int
    status: str
    erro: str | None = None
    criada_em: datetime
    kpis_resumo: dict[str, Any] | None = None


class AnaliseDetalhe(AnaliseResumo):
    resultado: dict[str, Any] | None = None


class ConfigAnaliseIn(BaseModel):
    """Configuração editável pelo cliente no painel."""

    metas: dict[str, float] | None = None
    marcacoes_nao_pagas: list[str] | None = None
    classificar_perda_pela_observacao: bool | None = None
    prob_fechamento_negociacao: float | None = Field(default=None, ge=0, le=1)
    dias_alerta_pipeline: int | None = Field(default=None, ge=1, le=365)
    origens_trafego_pago: list[str] | None = None
    sem_origem_considerar_pago: bool | None = None
    coluna_leads_meta: str | None = None
    status_manual: dict[str, str] | None = None

    def apenas_preenchidos(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}
