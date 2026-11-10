from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.middleware.base import RequestResponseEndpoint

from ai_service.api.chat import router as chat_router
from ai_service.api.health import router as health_router
from ai_service.api.integrations import router as integrations_router
from ai_service.config import settings

CHAT_REQUESTS = Counter("commerce_ai_chat_requests_total", "AI support requests", ["route"])


def create_app() -> FastAPI:
    app = FastAPI(
        title="Commerce AI Customer Service",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(integrations_router)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.middleware("http")
    async def count_chat_requests(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path in {"/v1/support/chat", "/v1/support/stream"}:
            CHAT_REQUESTS.labels(route=path).inc()
        return await call_next(request)

    return app


app = create_app()
