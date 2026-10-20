from ai_service.domain.models import Intent, SupportReply
from ai_service.domain.ports import KnowledgeRetriever, ModelProvider


class ChatService:
    def __init__(self, retriever: KnowledgeRetriever, model: ModelProvider) -> None:
        self._retriever = retriever
        self._model = model

    async def answer(self, message: str, *, authenticated: bool = False) -> SupportReply:
        normalized = message.strip().lower()
        if any(word in normalized for word in ("人工", "投诉", "律师", "报警")):
            return SupportReply(
                "已为你转接人工客服，请保留当前页面。", Intent.HUMAN_HANDOFF, requires_human=True
            )
        if any(word in normalized for word in ("退款", "取消订单", "改价")):
            if not authenticated:
                return SupportReply(
                    "此操作涉及订单与资金，请先登录并完成身份校验。",
                    Intent.AFTER_SALES,
                    requires_confirmation=True,
                )
            return SupportReply(
                "我可以协助发起申请，但提交前需要你确认订单和退款金额。",
                Intent.AFTER_SALES,
                requires_confirmation=True,
            )
        results = await self._retriever.search(message)
        context = [text for text, _ in results]
        answer = await self._model.answer(question=message, context=context)
        citations = tuple(citation for _, citation in results)
        intent = (
            Intent.ORDER
            if "订单" in normalized or "物流" in normalized
            else Intent.PRODUCT
            if "商品" in normalized
            else Intent.FAQ
        )
        return SupportReply(answer, intent, citations)
