from collections.abc import AsyncIterator
from uuid import UUID

from ai_service.application.support_orchestrator import (
    SupportOrchestrator,
    SupportStreamEvent,
)
from ai_service.domain.models import SupportReply
from ai_service.domain.ports import KnowledgeRetriever, ModelProvider, SupportToolProvider


class ChatService:
    def __init__(
        self,
        retriever: KnowledgeRetriever,
        model: ModelProvider,
        tools: SupportToolProvider | None = None,
    ) -> None:
        self._orchestrator = SupportOrchestrator(retriever, model, tools)

    async def answer(
        self,
        message: str,
        *,
        authenticated: bool = False,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> SupportReply:
        return await self._orchestrator.answer(
            message,
            authenticated=authenticated,
            customer_id=customer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            sku_id=sku_id,
        )

    async def stream(
        self,
        message: str,
        *,
        authenticated: bool = False,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> AsyncIterator[SupportStreamEvent]:
        async for event in self._orchestrator.stream(
            message,
            authenticated=authenticated,
            customer_id=customer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            sku_id=sku_id,
        ):
            yield event
