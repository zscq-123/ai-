import asyncio
import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_service.application.chat_service import ChatService
from ai_service.config import settings
from ai_service.domain.models import Intent, SupportReply
from ai_service.infrastructure.commerce_tools import build_support_tool_provider
from ai_service.infrastructure.conversation_repository import (
    ConversationRecorder,
    ConversationTimer,
)
from ai_service.infrastructure.model_provider import build_model_provider
from ai_service.infrastructure.retrieval import build_knowledge_retriever
from ai_service.prompts.library import EMPTY_ANSWER_REPLY

router = APIRouter(prefix="/v1/support", tags=["support"])
service = ChatService(
    build_knowledge_retriever(settings),
    build_model_provider(settings),
    build_support_tool_provider(settings),
)
recorder = ConversationRecorder(
    settings.database_url,
    settings.model,
    enabled=settings.persist_conversations,
)


async def answer_and_record(message: str, *, context: "TrustedSupportContext") -> SupportReply:
    if context.merchant_id is not None:
        merchant_is_active = await asyncio.to_thread(
            recorder.merchant_is_active, context.merchant_id
        )
        if merchant_is_active is False:
            raise HTTPException(status_code=404, detail="Active merchant not found")
    timer = ConversationTimer()
    reply = await service.answer(
        message,
        authenticated=context.authenticated,
        customer_id=context.customer_id,
        merchant_id=context.merchant_id,
        product_id=context.product_id,
        sku_id=context.sku_id,
    )
    await asyncio.to_thread(
        recorder.record,
        message,
        reply,
        timer.elapsed_ms(),
        merchant_id=context.merchant_id,
    )
    return reply


class ChatRequest(BaseModel):
    model_config = {"extra": "forbid"}
    message: str = Field(min_length=1, max_length=2000)


@dataclass(frozen=True)
class TrustedSupportContext:
    customer_id: UUID | None
    merchant_id: UUID | None
    product_id: UUID | None
    sku_id: UUID | None

    @property
    def authenticated(self) -> bool:
        return self.customer_id is not None


def trusted_context(
    customer_id: UUID | None,
    merchant_id: UUID | None,
    product_id: UUID | None,
    sku_id: UUID | None,
    signature: str | None,
) -> TrustedSupportContext:
    """Accept identity only from a commerce gateway signed context.

    Compatibility: old request-body authenticated/merchant_id fields are rejected by
    ChatRequest.extra=forbid. Anonymous callers keep working with only `message`.
    """
    if all(value is None for value in (customer_id, merchant_id, product_id, sku_id)):
        return TrustedSupportContext(None, None, None, None)
    contents = [
        f"{customer_id or ''}\n{merchant_id or ''}\n{product_id or ''}\n{sku_id or ''}".encode()
    ]
    if product_id is None and sku_id is None:
        contents.append(f"{customer_id or ''}\n{merchant_id or ''}".encode())
    expected = [
        hmac.new(settings.trusted_context_secret.encode(), content, hashlib.sha256).hexdigest()
        for content in contents
    ]
    if signature is None or not any(
        hmac.compare_digest(candidate, signature) for candidate in expected
    ):
        raise HTTPException(status_code=401, detail="Invalid trusted support context")
    return TrustedSupportContext(customer_id, merchant_id, product_id, sku_id)


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class CitationResponse(BaseModel):
    title: str
    reference: str


class ChatResponse(BaseModel):
    answer: str
    intent: str
    citations: list[CitationResponse]
    requires_human: bool
    requires_confirmation: bool


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    customer_id: Annotated[UUID | None, Header(alias="X-Nova-Customer-Id")] = None,
    merchant_id: Annotated[UUID | None, Header(alias="X-Nova-Merchant-Id")] = None,
    product_id: Annotated[UUID | None, Header(alias="X-Nova-Product-Id")] = None,
    sku_id: Annotated[UUID | None, Header(alias="X-Nova-Sku-Id")] = None,
    signature: Annotated[str | None, Header(alias="X-Nova-Context-Signature")] = None,
) -> ChatResponse:
    context = trusted_context(customer_id, merchant_id, product_id, sku_id, signature)
    reply = await answer_and_record(request.message, context=context)
    return ChatResponse(
        answer=reply.answer,
        intent=reply.intent.value,
        citations=[CitationResponse(title=c.title, reference=c.reference) for c in reply.citations],
        requires_human=reply.requires_human,
        requires_confirmation=reply.requires_confirmation,
    )


@router.post("/stream")
async def stream(
    request: ChatRequest,
    customer_id: Annotated[UUID | None, Header(alias="X-Nova-Customer-Id")] = None,
    merchant_id: Annotated[UUID | None, Header(alias="X-Nova-Merchant-Id")] = None,
    product_id: Annotated[UUID | None, Header(alias="X-Nova-Product-Id")] = None,
    sku_id: Annotated[UUID | None, Header(alias="X-Nova-Sku-Id")] = None,
    signature: Annotated[str | None, Header(alias="X-Nova-Context-Signature")] = None,
) -> StreamingResponse:
    context = trusted_context(customer_id, merchant_id, product_id, sku_id, signature)
    if context.merchant_id is not None:
        merchant_is_active = await asyncio.to_thread(
            recorder.merchant_is_active, context.merchant_id
        )
        if merchant_is_active is False:
            raise HTTPException(status_code=404, detail="Active merchant not found")

    async def events() -> AsyncIterator[str]:
        timer = ConversationTimer()
        final: SupportReply | None = None
        async for event in service.stream(
            request.message,
            authenticated=context.authenticated,
            customer_id=context.customer_id,
            merchant_id=context.merchant_id,
            product_id=context.product_id,
            sku_id=context.sku_id,
        ):
            if event.delta:
                yield _sse("delta", {"text": event.delta})
            if event.final is not None:
                final = event.final

        if final is None:
            final = SupportReply(EMPTY_ANSWER_REPLY, Intent.FAQ, requires_confirmation=True)

        await asyncio.to_thread(
            recorder.record,
            request.message,
            final,
            timer.elapsed_ms(),
            merchant_id=context.merchant_id,
        )
        yield _sse("answer", {"answer": final.answer})
        yield _sse(
            "done",
            {"intent": final.intent.value, "requires_human": final.requires_human},
        )

    return StreamingResponse(events(), media_type="text/event-stream")
