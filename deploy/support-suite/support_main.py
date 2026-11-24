"""Dedicated OMS/BUZUD integration and support-console mailbox process."""
from fastapi import FastAPI

from ai_service.api.agent_settings import router as agent_settings_router
from ai_service.api.health import router as health_router
from ai_service.api.integrations import router as integration_router
from ai_service.api.knowledge_documents import router as knowledge_documents_router
from ai_service.api.mailboxes import router as mailbox_router

app = FastAPI(title="OMS and BUZUD support", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(health_router)
app.include_router(integration_router)
app.include_router(mailbox_router)
app.include_router(agent_settings_router)
app.include_router(knowledge_documents_router)
