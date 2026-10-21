from dataclasses import dataclass

from ai_service.domain.models import Intent, SupportReply
from ai_service.domain.ports import KnowledgeRetriever, ModelProvider


@dataclass(frozen=True)
class SupportContext:
    message: str
    authenticated: bool

    @property
    def normalized(self) -> str:
        return self.message.strip().lower()


class EmotionRiskModule:
    """Detects signals that require a human instead of an unsafe automatic answer."""

    _handoff_signals = ("人工", "投诉", "律师", "报警")

    def requires_handoff(self, context: SupportContext) -> bool:
        return any(signal in context.normalized for signal in self._handoff_signals)


class IntentRoutingModule:
    """Routes a request to an internal capability without exposing separate bots."""

    def route(self, context: SupportContext) -> Intent:
        message = context.normalized
        if any(word in message for word in ("退款", "退货", "取消订单", "改价", "售后")):
            return Intent.AFTER_SALES
        if any(word in message for word in ("订单", "物流", "快递", "发货")):
            return Intent.ORDER
        if any(word in message for word in ("商品", "规格", "型号", "推荐", "选购")):
            return Intent.PRODUCT
        return Intent.FAQ


class AfterSalesModule:
    """Converts sensitive after-sales operations into a request for more information."""

    def prepare(self, context: SupportContext, intent: Intent) -> SupportReply | None:
        if intent is not Intent.AFTER_SALES:
            return None
        if not context.authenticated:
            return SupportReply(
                "此操作涉及订单与资金，请先登录并完成身份校验。",
                intent,
                requires_confirmation=True,
            )
        return SupportReply(
            "我可以协助发起申请，但提交前需要你确认订单和退款金额。",
            intent,
            requires_confirmation=True,
        )


class ResponseAuditModule:
    """Final policy gate shared by every internal specialist."""

    def review(self, reply: SupportReply, context: SupportContext) -> SupportReply:
        if not reply.answer.strip():
            return SupportReply(
                "我还需要更多商品或订单信息才能继续，请补充具体问题。",
                reply.intent,
                reply.citations,
                requires_confirmation=True,
            )
        if reply.intent is Intent.AFTER_SALES and not reply.requires_confirmation:
            return SupportReply(
                reply.answer,
                reply.intent,
                reply.citations,
                reply.requires_human,
                requires_confirmation=True,
            )
        return reply


class SupportOrchestrator:
    """Single public support agent coordinating private specialist modules."""

    def __init__(self, retriever: KnowledgeRetriever, model: ModelProvider) -> None:
        self._retriever = retriever
        self._model = model
        self._emotion = EmotionRiskModule()
        self._router = IntentRoutingModule()
        self._after_sales = AfterSalesModule()
        self._audit = ResponseAuditModule()

    async def answer(self, message: str, *, authenticated: bool = False) -> SupportReply:
        context = SupportContext(message=message, authenticated=authenticated)
        if self._emotion.requires_handoff(context):
            return SupportReply(
                "已为你转接人工客服，请保留当前页面。",
                Intent.HUMAN_HANDOFF,
                requires_human=True,
            )

        intent = self._router.route(context)
        prepared = self._after_sales.prepare(context, intent)
        if prepared is not None:
            return self._audit.review(prepared, context)

        results = await self._retriever.search(message)
        answer = await self._model.answer(
            question=message,
            context=[content for content, _ in results],
        )
        reply = SupportReply(
            answer,
            intent,
            tuple(citation for _, citation in results),
        )
        return self._audit.review(reply, context)
