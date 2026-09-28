"""Contratos de entrada e saída da API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _senha_forte(v: str) -> str:
    if v.isdigit() or v.isalpha():
        raise ValueError("A senha deve misturar letras e números.")
    return v


# ---- Autenticação ----------------------------------------------------------- #
class CadastroOrganizacao(BaseModel):
    """Cria a organização e o primeiro cliente da carteira."""

    organizacao: str = Field(min_length=2, max_length=160)
    tipo: str = Field(default="direta", pattern="^(agencia|direta)$")
    # Para tipo "direta" costuma ser o mesmo nome da organização; para agência, o 1º cliente.
    empresa: str | None = Field(default=None, max_length=160)
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)

    _v = field_validator("senha")(_senha_forte)


class Login(BaseModel):
    email: EmailStr
    senha: str


class NovoUsuario(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    papel: str = Field(default="membro", pattern="^(admin|membro|cliente)$")
    # Obrigatório quando papel = "cliente": quais empresas ele enxerga
    empresas: list[int] = Field(default_factory=list)

    _v = field_validator("senha")(_senha_forte)


class TipoOrganizacao(BaseModel):
    """Liga/desliga o modo agência."""

    tipo: str = Field(pattern="^(agencia|direta)$")


class NovaEmpresa(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    segmento: str | None = Field(default=None, max_length=80)


class OrganizacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    slug: str
    tipo: str
    plano: str


class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    slug: str
    segmento: str | None = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    papel: str
    organizacao: OrganizacaoOut
    empresas: list[EmpresaOut] = Field(default_factory=list)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ---- Carteira --------------------------------------------------------------- #
class ItemCarteira(BaseModel):
    """Uma linha do painel multicliente da agência."""

    empresa: EmpresaOut
    ultima_analise_id: int | None = None
    ultimo_mes: str | None = None
    total_analises: int = 0
    kpis: dict[str, Any] | None = None
    variacao: dict[str, float] | None = None
    erro: str | None = None


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
