from fastapi import FastAPI

from ai_service.api.health import router as health_router
from ai_service.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Commerce AI Customer Service",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
    )
    app.include_router(health_router)
    return app


app = create_app()
