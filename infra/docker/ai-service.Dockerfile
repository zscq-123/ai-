FROM python:3.14-slim AS build
WORKDIR /workspace
COPY services/ai-service services/ai-service
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir ./services/ai-service
RUN mkdir -p /opt/nova/fastembed && \
    /opt/venv/bin/python -c "from ai_service.infrastructure.embeddings import FastEmbedEmbedder; model = FastEmbedEmbedder(cache_dir='/opt/nova/fastembed', local_files_only=False); model.embed_query('商品库存查询')"

FROM python:3.14-slim
RUN useradd --system --uid 10001 commerce
COPY --from=build /opt/venv /opt/venv
COPY --from=build --chown=10001:10001 /opt/nova/fastembed /opt/nova/fastembed
ENV AI_EMBEDDING_CACHE_DIR=/opt/nova/fastembed \
    AI_EMBEDDING_LOCAL_ONLY=true
WORKDIR /app
USER commerce
EXPOSE 8000
ENTRYPOINT ["/opt/venv/bin/uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
