from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from ai_service.domain.models import Citation, ReplyGuidance


class KnowledgeRetriever(Protocol):
    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]: ...


class SupportToolProvider(Protocol):
    async def lookup(
        self,
        message: str,
        *,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> list[tuple[str, Citation]]: ...


class ModelProvider(Protocol):
    async def answer(
        self,
        *,
        question: str,
        context: list[str],
        guidance: ReplyGuidance | None = None,
    ) -> str: ...

    def stream_answer(
        self,
        *,
        question: str,
        context: list[str],
        guidance: ReplyGuidance | None = None,
    ) -> AsyncIterator[str]: ...
