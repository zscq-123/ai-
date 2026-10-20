FROM python:3.14-slim AS build
WORKDIR /workspace
COPY services/ai-service services/ai-service
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir ./services/ai-service

FROM python:3.14-slim
RUN useradd --system --uid 10001 commerce
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
USER commerce
EXPOSE 8000
ENTRYPOINT ["/opt/venv/bin/uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
