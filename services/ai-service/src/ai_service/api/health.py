from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from ai_service.config import settings

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["ai-service"]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="ai-service")


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    service: Literal["ai-service"]
    model: Literal["external", "local-fallback"]
    buzud_integration_configured: bool
    store_url: str
    conversation_persistence: bool
    mailbox_connector: bool
    mailbox_state_persistence: bool


@router.get("/ready", response_model=ReadinessResponse)
def readiness(response: Response) -> ReadinessResponse:
    model_configured = settings.provider == "mlx" or bool(settings.api_key)
    buzud_configured = bool(settings.buzud_integration_secret)
    production_ready = model_configured and buzud_configured
    ready = settings.environment.lower() != "production" or production_ready
    if not ready:
        response.status_code = 503
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        service="ai-service",
        model="external" if model_configured else "local-fallback",
        buzud_integration_configured=buzud_configured,
        store_url=settings.buzud_store_url,
        conversation_persistence=settings.persist_conversations,
        mailbox_connector=settings.mailbox_local_connector_enabled,
        mailbox_state_persistence=bool(settings.mailbox_state_file.strip()),
    )
