from ai_service.application.support_orchestrator import SupportOrchestrator
from ai_service.domain.models import Citation, Intent


class StubRetriever:
    async def search(self, query: str) -> list[tuple[str, Citation]]:
        return [("现货商品通常在付款后 24 小时内出库。", Citation("配送说明", "kb://shipping"))]


class StubModel:
    def __init__(self, answer: str = "现货商品通常在付款后 24 小时内出库。") -> None:
        self.answer_text = answer

    async def answer(self, *, question: str, context: list[str]) -> str:
        return self.answer_text


async def test_single_agent_routes_product_guidance_to_automatic_reply() -> None:
    orchestrator = SupportOrchestrator(StubRetriever(), StubModel())

    reply = await orchestrator.answer("请推荐一个商品")

    assert reply.intent is Intent.PRODUCT
    assert reply.requires_human is False
    assert reply.requires_confirmation is False
    assert reply.citations


async def test_single_agent_routes_logistics_to_order_module() -> None:
    orchestrator = SupportOrchestrator(StubRetriever(), StubModel())

    reply = await orchestrator.answer("我的快递什么时候发货？")

    assert reply.intent is Intent.ORDER


async def test_single_agent_requests_information_for_after_sales() -> None:
    orchestrator = SupportOrchestrator(StubRetriever(), StubModel())

    reply = await orchestrator.answer("我要退款", authenticated=False)

    assert reply.intent is Intent.AFTER_SALES
    assert reply.requires_confirmation is True
    assert reply.requires_human is False


async def test_single_agent_hands_off_emotional_or_risky_request() -> None:
    orchestrator = SupportOrchestrator(StubRetriever(), StubModel())

    reply = await orchestrator.answer("物流太差了，我要投诉")

    assert reply.intent is Intent.HUMAN_HANDOFF
    assert reply.requires_human is True


async def test_audit_module_rejects_empty_automatic_reply() -> None:
    orchestrator = SupportOrchestrator(StubRetriever(), StubModel("  "))

    reply = await orchestrator.answer("这是什么？")

    assert reply.requires_confirmation is True
    assert "补充" in reply.answer
