from ai_service.application.support_orchestrator import SupportOrchestrator
from ai_service.domain.models import SupportReply
from ai_service.domain.ports import KnowledgeRetriever, ModelProvider


class ChatService:
    def __init__(self, retriever: KnowledgeRetriever, model: ModelProvider) -> None:
        self._orchestrator = SupportOrchestrator(retriever, model)

    async def answer(self, message: str, *, authenticated: bool = False) -> SupportReply:
        return await self._orchestrator.answer(message, authenticated=authenticated)
