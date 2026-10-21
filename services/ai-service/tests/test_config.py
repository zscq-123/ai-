import pytest
from pydantic import ValidationError

from ai_service.config import Settings


def test_production_rejects_default_trusted_context_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", trusted_context_secret="local-ai-context-secret")


def test_production_accepts_explicit_trusted_context_secret() -> None:
    settings = Settings(environment="production", trusted_context_secret="production-secret")
    assert settings.trusted_context_secret == "production-secret"
