"""Dedicated OMS/BUZUD integration process; no NOVA database or commerce routes."""
from fastapi import FastAPI
from ai_service.api.health import router as health_router
from ai_service.api.integrations import router as integration_router

app = FastAPI(title="OMS and BUZUD support", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(health_router)
app.include_router(integration_router)
