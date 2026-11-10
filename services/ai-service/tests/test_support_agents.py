import asyncio
import hashlib
import hmac
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_service.api import integrations
from ai_service.application.support_agents import (
    AgentScope,
    EvidenceTools,
    SupportAgentCoordinator,
    ToolDenied,
    unsafe_answer,
)
from ai_service.config import Settings, settings
from ai_service.infrastructure.agent_model import AgentModelError, JsonAgentModel
from ai_service.main import app


def records():
    return [
        integrations.Evidence(
            content="订单 O7 当前状态：已取消；订单金额 14.70 SGD。未提供物流轨迹。",
            title="当前账号订单",
            reference="order://buzud/O7",
        ),
        integrations.Evidence(
            content="客服邮箱为 current@example.test。",
            title="联系方式",
            reference="faq://buzud/contact",
            keywords=["联系", "邮箱", "contact"],
        ),
        integrations.Evidence(
            content="未拆封且凭证齐全的商品可在收货后 7 天内申请退货，最终由客服审核。",
            title="售后政策",
            reference="faq://buzud/aftersales",
            keywords=["退货", "售后", "return"],
        ),
    ]


def scope(question="订单状态如何，退货条件和联系邮箱是什么？", **kwargs):
    return AgentScope.from_items(
        source="buzud",
        authenticated=kwargs.pop("authenticated", True),
        question=question,
        english=False,
        topic=kwargs.pop("topic", None),
        items=kwargs.pop("items", records()),
        **kwargs,
    )


def canonical(question):
    return integrations.order_reply("buzud", question, records(), False)


class ScriptedModel:
    def __init__(self, roles=("order", "knowledge", "aftersales"), *, reject=False):
        self.roles = roles
        self.reject = reject
        self.calls = []
        self.completed = set()

    async def complete(self, *, role, system, messages):
        self.calls.append((role, system, json.loads(json.dumps(messages))))
        if role == "supervisor":
            return {"tasks": [{"agent": r, "question": "查询当前信息"} for r in self.roles]}
        if role == "reviewer":
            return {"approved": not self.reject, "unsupported_claims": []}
        tool_results = [
            json.loads(m["content"])["tool_result"] for m in messages[1:] if m["role"] == "user"
        ]
        if not tool_results:
            if role == "aftersales" and "order" in self.roles:
                assert "order" in self.completed
            return {
                "action": "tool",
                "tool": {
                    "order": "read_order",
                    "knowledge": "search_knowledge",
                    "aftersales": "read_after_sales_policy",
                }[role],
                "query": "联系邮箱",
            }
        if role == "aftersales" and "order" in self.roles and len(tool_results) == 1:
            return {"action": "tool", "tool": "read_order_result"}
        self.completed.add(role)
        evidence = [e for result in tool_results for e in result]
        return {
            "action": "finish",
            "answer": "\n".join(e["content"] for e in evidence),
            "evidence_ids": [e["id"] for e in evidence],
        }


async def run(model, current=None, **options):
    return await SupportAgentCoordinator(model, Settings(_env_file=None, **options)).run(
        current or scope(), canonical_order=canonical
    )


async def test_three_specialists_use_independent_contexts_and_order_dependency():
    model = ScriptedModel()
    reply, trace = await run(model)
    assert not trace.fallback_used
    assert trace.planner == "model" and trace.reviewer == "approved"
    assert trace.model_calls == 9
    assert "已取消" in reply.answer and "14.70 SGD" in reply.answer
    assert "未拆封" in reply.answer and "current@example.test" in reply.answer
    assert len(reply.citations) == 3
    after = next(t for t in trace.tasks if t.agent == "aftersales")
    assert after.depends_on == ["order"]
    assert [t["tool"] for t in after.tools] == ["read_after_sales_policy", "read_order_result"]
    for role, _, messages in model.calls:
        if role in {"knowledge", "order", "aftersales"}:
            first = json.loads(messages[0]["content"])
            assert "14.70" not in messages[0]["content"]  # Only a tool exposes order facts.
            assert "dependencies" in first
    log = json.dumps(trace.public_record())
    assert "current@example.test" not in log and "14.70" not in log
    assert scope().question not in log


async def test_independent_agents_run_concurrently():
    arrived = set()
    both = asyncio.Event()

    class Parallel(ScriptedModel):
        async def complete(self, **kwargs):
            role = kwargs["role"]
            if role in {"order", "knowledge"} and len(kwargs["messages"]) == 1:
                arrived.add(role)
                if len(arrived) == 2:
                    both.set()
                await asyncio.wait_for(both.wait(), timeout=1)
            return await super().complete(**kwargs)

    _, trace = await run(Parallel(("order", "knowledge")), scope("订单状态和联系邮箱？"))
    assert arrived == {"order", "knowledge"} and not trace.fallback_used


def test_scope_filters_other_business_and_anonymous_order():
    other = integrations.Evidence(content="secret", title="other", reference="order://oms/PRIVATE")
    current = scope(authenticated=False, items=[*records(), other])
    assert all(e.reference.startswith("faq://buzud/") for e in current.evidence)
    with pytest.raises(ToolDenied, match="authentication"):
        EvidenceTools(current, "order", {}).call("read_order", "")
    with pytest.raises(ToolDenied, match="not_allowed"):
        EvidenceTools(scope(), "knowledge", {}).call("read_order", "PRIVATE")
    with pytest.raises(ToolDenied, match="not_allowed"):
        EvidenceTools(scope(), "aftersales", {}).call("issue_refund", "O7")


def catalogue_records():
    return [
        integrations.Evidence(
            content=(
                "商品：HCG Pregnancy Rapid Test\n售价：SGD 9.90\n"
                "库存：可售库存 3 件\n商品页：/zh/p/hcg-pregnancy-rapid-test-8885020710595/"
            ),
            title="商品资料",
            reference="catalog://buzud/8885020710595",
            keywords=["hcg", "pregnancy", "早孕检测"],
        )
    ]


def test_catalogue_scope_is_source_scoped_and_read_for_product_questions():
    foreign = integrations.Evidence(
        content="other merchant product", title="other", reference="catalog://oms/1"
    )
    product_scope = scope(
        question="这个多少钱", topic="products", items=[*records(), *catalogue_records(), foreign]
    )
    references = {e.reference for e in product_scope.evidence}
    assert "catalog://buzud/8885020710595" in references
    assert "catalog://oms/1" not in references

    tools = EvidenceTools(product_scope, "knowledge", {})
    result = tools.call("search_knowledge", "这个多少钱")
    assert any(item["reference"] == "catalog://buzud/8885020710595" for item in result)
    assert any("SGD 9.90" in item["content"] for item in result)


def test_unrelated_policy_question_without_catalogue_reads_only_faq():
    product_scope = scope(question="你们的联系邮箱是什么", topic="contact", items=records())
    tools = EvidenceTools(product_scope, "knowledge", {})
    result = tools.call("search_knowledge", "联系邮箱")
    assert result
    assert all(item["reference"].startswith("faq://") for item in result)


@pytest.mark.parametrize("violation", ["unknown_tool", "unread_citation", "unread_dependency"])
async def test_invalid_specialist_actions_fail_closed(violation):
    class Bad(ScriptedModel):
        async def complete(self, **kwargs):
            value = await super().complete(**kwargs)
            if kwargs["role"] == "knowledge":
                if violation == "unknown_tool":
                    return {"action": "tool", "tool": "read_order"}
                if violation == "unread_citation" and value.get("action") == "finish":
                    value["evidence_ids"] = ["e0"]
            if (
                kwargs["role"] == "aftersales"
                and violation == "unread_dependency"
                and len(kwargs["messages"]) > 1
            ):
                return {"action": "finish", "answer": "可以退", "evidence_ids": ["e2"]}
            return value

    _, trace = await run(Bad())
    assert trace.fallback_used
    assert any(t.status == "degraded" for t in trace.tasks)


@pytest.mark.parametrize(
    "answer",
    [
        "退款已经到账。",
        "不能帮你改订单，退款已经到账。",
        "人工客服已接通。",
        "退货可在30天内办理。",
        "请联系 hacker@example.test。",
    ],
)
def test_unverified_actions_numbers_and_email_rejected(answer):
    assert unsafe_answer(answer, scope().evidence)


def test_negated_refund_and_known_policy_are_allowed():
    assert not unsafe_answer("取消状态不代表退款已经到账。", scope().evidence)
    assert not unsafe_answer(records()[2].content, scope().evidence)


@pytest.mark.parametrize("review_failure", ["reject", "unavailable"])
async def test_reviewer_failure_never_publishes_unchecked_draft(review_failure):
    class BadReview(ScriptedModel):
        async def complete(self, **kwargs):
            value = await super().complete(**kwargs)
            if kwargs["role"] == "knowledge" and value.get("action") == "finish":
                value["answer"] = "UNVERIFIED PRODUCT CLAIM"
            if kwargs["role"] == "reviewer":
                if review_failure == "unavailable":
                    raise AgentModelError("unavailable")
                return {"approved": False, "unsupported_claims": ["unverified"]}
            return value

    reply, trace = await run(BadReview(("knowledge",)), scope("联系邮箱是什么？"))
    assert "UNVERIFIED" not in reply.answer
    assert trace.fallback_used
    assert trace.reviewer in {"unavailable", "rejected"}


async def test_deadline_and_call_budget_are_bounded():
    class Slow(ScriptedModel):
        async def complete(self, **kwargs):
            if kwargs["role"] != "supervisor":
                await asyncio.sleep(2)
            return await super().complete(**kwargs)

    started = time.monotonic()
    _, trace = await run(Slow(), agent_total_timeout_seconds=0.03)
    assert time.monotonic() - started < 0.5
    assert trace.fallback_used and trace.reviewer == "unavailable"
    assert any(t.status == "cancelled" for t in trace.tasks)
    _, trace = await run(ScriptedModel(), agent_max_calls=2)
    assert trace.model_calls == 2 and trace.fallback_used


async def test_invalid_plan_falls_back_and_unrelated_faq_is_not_an_answer():
    class Invalid(ScriptedModel):
        async def complete(self, **kwargs):
            if kwargs["role"] == "supervisor":
                return {
                    "tasks": [{"agent": "knowledge", "question": "x", "depends_on": ["knowledge"]}]
                }
            raise AgentModelError("offline")

    reply, trace = await run(Invalid(), scope("月球引力是多少？"))
    assert trace.planner == "fallback" and trace.fallback_used
    assert not reply.citations and "current@example.test" not in reply.answer


async def test_cancelled_order_cannot_become_awaiting_payment_or_refunded():
    reply, trace = await run(ScriptedModel(("order",)), scope("订单还需要付款吗，退款到账了吗？"))
    assert not trace.fallback_used
    assert "不需要继续付款" in reply.answer and "不代表退款已经到账" in reply.answer
    assert "待付款" not in reply.answer


async def test_json_provider_has_isolated_messages_and_safe_failure():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}}]})

    model = JsonAgentModel(
        Settings(_env_file=None, AI_API_KEY="test-key"), transport=httpx.MockTransport(handler)
    )
    for role in ("knowledge", "order"):
        assert await model.complete(
            role=role, system="Return JSON only.", messages=[{"role": "user", "content": role}]
        ) == {"ok": True}
    assert bodies[1]["messages"][-1]["content"] == "order"
    assert len(bodies[1]["messages"]) == 2
    assert bodies[0]["response_format"] == {"type": "json_object"}
    assert bodies[0]["thinking"] == {"type": "disabled"}
    model.transport = httpx.MockTransport(lambda _: httpx.Response(500, text="SECRET"))
    with pytest.raises(AgentModelError, match="^agent_model_unavailable$"):
        await model.complete(role="order", system="JSON", messages=[])


def test_signed_endpoint_preserves_contract_and_refreshes_request_evidence(monkeypatch):
    model = ScriptedModel(("knowledge",))
    monkeypatch.setattr(settings, "integration_agents_enabled", True)
    monkeypatch.setattr(settings, "buzud_integration_secret", "test-secret")
    monkeypatch.setattr(integrations, "agent_model", model)
    integrations.conversations.clear()
    client = TestClient(app)

    def send(email):
        item = records()[1].model_dump()
        item["content"] = f"客服邮箱为 {email}。"
        body = json.dumps({"message": "联系邮箱是什么？", "evidence": [item]}).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(
            b"test-secret", b"buzud\n" + timestamp.encode() + b"\n" + body, hashlib.sha256
        ).hexdigest()
        return client.post(
            "/v1/integrations/buzud/chat",
            content=body,
            headers={"X-Support-Timestamp": timestamp, "X-Support-Signature": signature},
        )

    for email in ("first@example.test", "updated@example.test"):
        response = send(email)
        assert response.status_code == 200 and email in response.json()["answer"]
        assert response.headers["X-Support-Agent-Degraded"] == "false"
        assert response.headers["X-Support-Agent-Roles"] == "knowledge"
        assert set(response.json()) == {
            "answer",
            "intent",
            "citations",
            "requires_human",
            "requires_confirmation",
        }
    before = len(model.calls)
    assert client.post("/v1/integrations/buzud/chat", json={"message": "邮箱"}).status_code == 401
    assert len(model.calls) == before


@pytest.mark.parametrize(
    "question,blocked",
    [
        ("订单状态是什么，退货条件和客服邮箱是什么？", False),
        ("查一下别人的订单和客服邮箱", True),
        ("查一下订单的客户邮箱以及客服邮箱", True),
    ],
)
def test_compound_public_contact_keeps_identity_guards(question, blocked):
    from ai_service.application.support_orchestrator import SafetyBoundaryModule, SupportContext
    from ai_service.domain.models import Intent

    reply = SafetyBoundaryModule().prepare(SupportContext(question, True), Intent.FAQ, [])
    assert (reply is not None) == blocked
