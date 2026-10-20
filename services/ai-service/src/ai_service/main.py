from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_service.api.chat import router as chat_router
from ai_service.api.health import router as health_router
from ai_service.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Commerce AI Customer Service",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(health_router)
    app.include_router(chat_router)
    return app


app = create_app()
