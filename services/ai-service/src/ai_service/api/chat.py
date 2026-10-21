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
from ai_service.domain.models import SupportReply
from ai_service.infrastructure.conversation_repository import (
    ConversationRecorder,
    ConversationTimer,
)
from ai_service.infrastructure.local_knowledge import LocalKnowledgeRetriever
from ai_service.infrastructure.model_provider import build_model_provider

router = APIRouter(prefix="/v1/support", tags=["support"])
service = ChatService(LocalKnowledgeRetriever(), build_model_provider(settings))
recorder = ConversationRecorder(
    settings.database_url,
    settings.model,
    enabled=settings.persist_conversations,
)


async def answer_and_record(
    message: str, *, authenticated: bool, merchant_id: UUID | None
) -> SupportReply:
    if merchant_id is not None:
        merchant_is_active = await asyncio.to_thread(recorder.merchant_is_active, merchant_id)
        if merchant_is_active is False:
            raise HTTPException(status_code=404, detail="Active merchant not found")
    timer = ConversationTimer()
    reply = await service.answer(message, authenticated=authenticated)
    await asyncio.to_thread(
        recorder.record,
        message,
        reply,
        timer.elapsed_ms(),
        merchant_id=merchant_id,
    )
    return reply


class ChatRequest(BaseModel):
    model_config = {"extra": "forbid"}
    message: str = Field(min_length=1, max_length=2000)


@dataclass(frozen=True)
class TrustedSupportContext:
    customer_id: UUID | None
    merchant_id: UUID | None

    @property
    def authenticated(self) -> bool:
        return self.customer_id is not None


def trusted_context(
    customer_id: UUID | None,
    merchant_id: UUID | None,
    signature: str | None,
) -> TrustedSupportContext:
    """Accept identity only from a commerce gateway signed context.

    Compatibility: old request-body authenticated/merchant_id fields are rejected by
    ChatRequest.extra=forbid. Anonymous callers keep working with only `message`.
    """
    if customer_id is None and merchant_id is None:
        return TrustedSupportContext(None, None)
    content = f"{customer_id or ''}\n{merchant_id or ''}".encode()
    expected = hmac.new(
        settings.trusted_context_secret.encode(), content, hashlib.sha256
    ).hexdigest()
    if signature is None or not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid trusted support context")
    return TrustedSupportContext(customer_id, merchant_id)


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
    signature: Annotated[str | None, Header(alias="X-Nova-Context-Signature")] = None,
) -> ChatResponse:
    context = trusted_context(customer_id, merchant_id, signature)
    reply = await answer_and_record(
        request.message,
        authenticated=context.authenticated,
        merchant_id=context.merchant_id,
    )
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
    signature: Annotated[str | None, Header(alias="X-Nova-Context-Signature")] = None,
) -> StreamingResponse:
    context = trusted_context(customer_id, merchant_id, signature)
    async def events() -> AsyncIterator[str]:
        reply = await answer_and_record(
            request.message,
            authenticated=context.authenticated,
            merchant_id=context.merchant_id,
        )
        answer_data = json.dumps({"answer": reply.answer}, ensure_ascii=False)
        done_data = json.dumps(
            {"intent": reply.intent.value, "requires_human": reply.requires_human},
            ensure_ascii=False,
        )
        yield f"event: answer\ndata: {answer_data}\n\n"
        yield f"event: done\ndata: {done_data}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
