from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_", env_file=".env", extra="ignore")

    environment: str = "local"
    provider: str = "openai"
    api_key: str = ""
    database_url: str = "postgresql+psycopg://commerce:commerce_local@localhost:55432/commerce"
    commerce_api_url: str = "http://localhost:8080"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
