import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
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


async def answer_and_record(message: str, *, authenticated: bool) -> SupportReply:
    timer = ConversationTimer()
    reply = await service.answer(message, authenticated=authenticated)
    await asyncio.to_thread(recorder.record, message, reply, timer.elapsed_ms())
    return reply


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    authenticated: bool = False


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
async def chat(request: ChatRequest) -> ChatResponse:
    reply = await answer_and_record(request.message, authenticated=request.authenticated)
    return ChatResponse(
        answer=reply.answer,
        intent=reply.intent.value,
        citations=[CitationResponse(title=c.title, reference=c.reference) for c in reply.citations],
        requires_human=reply.requires_human,
        requires_confirmation=reply.requires_confirmation,
    )


@router.post("/stream")
async def stream(request: ChatRequest) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        reply = await answer_and_record(request.message, authenticated=request.authenticated)
        answer_data = json.dumps({"answer": reply.answer}, ensure_ascii=False)
        done_data = json.dumps(
            {"intent": reply.intent.value, "requires_human": reply.requires_human},
            ensure_ascii=False,
        )
        yield f"event: answer\ndata: {answer_data}\n\n"
        yield f"event: done\ndata: {done_data}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
