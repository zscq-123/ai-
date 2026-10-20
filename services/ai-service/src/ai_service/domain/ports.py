from typing import Protocol

from ai_service.domain.models import Citation


class KnowledgeRetriever(Protocol):
    async def search(self, query: str, *, limit: int = 4) -> list[tuple[str, Citation]]: ...


class ModelProvider(Protocol):
    async def answer(self, *, question: str, context: list[str]) -> str: ...
