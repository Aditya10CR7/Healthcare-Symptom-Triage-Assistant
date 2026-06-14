from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "LangGraph Symptom Triage Assistant"
    database_url: str = "postgresql+psycopg://triage:triage@localhost:5432/triage"
    persist_cases: bool = True
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    admin_username: str = "admin"
    admin_password: str = "change-me"
    admin_secret: str = Field(default="replace-this-local-secret", min_length=12)
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
