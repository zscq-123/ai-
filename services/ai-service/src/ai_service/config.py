from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_", env_file=".env", extra="ignore")

    environment: str = "local"
    provider: str = "deepseek"
    api_key: str = Field(
        default="", validation_alias=AliasChoices("DEEPSEEK_API_KEY", "AI_API_KEY")
    )
    model: str = "deepseek-flash"
    model_base_url: str = "https://api.deepseek.com"
    model_timeout_seconds: float = 20.0
    thinking: bool = False
    database_url: str = "postgresql+psycopg://commerce:commerce_local@localhost:55432/commerce"
    commerce_api_url: str = "http://localhost:8080"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    persist_conversations: bool = True
    retriever: str = "auto"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_cache_dir: str = str(Path.home() / ".cache" / "nova" / "fastembed")
    embedding_local_only: bool = True
    embedding_min_score: float = 0.45
    knowledge_file: str = ""
    trusted_context_secret: str = "local-ai-context-secret"
    commerce_tool_secret: str = ""
    commerce_tool_timeout_seconds: float = 3.0
    oms_integration_secret: str = ""
    buzud_integration_secret: str = ""
    integration_agents_enabled: bool = False
    agent_total_timeout_seconds: float = Field(default=24.0, gt=0, le=26)
    agent_call_timeout_seconds: float = Field(default=6.0, gt=0, le=10)
    agent_max_calls: int = Field(default=11, ge=1, le=12)

    @model_validator(mode="after")
    def require_production_context_secret(self) -> "Settings":
        if self.environment.lower() == "production" and (
            not self.trusted_context_secret
            or self.trusted_context_secret == "local-ai-context-secret"
        ):
            raise ValueError("AI_TRUSTED_CONTEXT_SECRET must be configured in production")
        if self.environment.lower() == "production" and (
            not self.commerce_tool_secret
            or self.commerce_tool_secret == "local-support-tool-secret"
        ):
            raise ValueError("AI_COMMERCE_TOOL_SECRET must be configured in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
