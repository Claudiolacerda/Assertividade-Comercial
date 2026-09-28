"""Configuração da aplicação, lida do ambiente (.env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Assertividade Comercial"
    ambiente: str = "desenvolvimento"

    # Banco (Postgres — o isolamento por schema exige Postgres)
    database_url: str = "postgresql+psycopg2://assert_app:assert_dev_pwd@localhost:5432/assertividade"

    # Autenticação
    jwt_secret: str = "troque-esta-chave-em-producao"
    jwt_algoritmo: str = "HS256"
    jwt_expira_minutos: int = 60 * 12

    # Uploads
    dir_uploads: Path = Path("dados_clientes")
    tamanho_max_upload_mb: int = 25

    # CORS (origens do frontend)
    origens_permitidas: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Cadastro aberto: em produção normalmente False (você cria as contas dos clientes)
    permitir_autocadastro: bool = True

    @property
    def lista_origens(self) -> list[str]:
        return [o.strip() for o in self.origens_permitidas.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
