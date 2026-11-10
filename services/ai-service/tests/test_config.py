from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_service.config import Settings


def test_embedding_cache_is_persistent_by_default() -> None:
    cache_dir = Path(Settings().embedding_cache_dir).expanduser()

    assert cache_dir == Path.home() / ".cache" / "nova" / "fastembed"


def test_production_rejects_default_trusted_context_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", trusted_context_secret="local-ai-context-secret")


def test_production_accepts_explicit_trusted_context_secret() -> None:
    settings = Settings(
        environment="production",
        trusted_context_secret="production-secret",
        commerce_tool_secret="production-tool-secret",
    )
    assert settings.trusted_context_secret == "production-secret"


def test_production_rejects_missing_commerce_tool_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", trusted_context_secret="production-secret")
