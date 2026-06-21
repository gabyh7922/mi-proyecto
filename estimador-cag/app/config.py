"""Configuración del proyecto cargada desde variables de entorno (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Proveedor de LLM a usar: "openai" o "anthropic"
    llm_provider: str = "anthropic"

    # API keys (se cargan desde .env, NUNCA se escriben en el código)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Modelos económicos para este ejercicio
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-haiku-4-5"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración (cacheada para no releer el .env en cada llamada)."""
    return Settings()
