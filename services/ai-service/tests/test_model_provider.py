import json

import httpx
import pytest

from ai_service.config import Settings
from ai_service.domain.models import Intent, ReplyGuidance
from ai_service.infrastructure.model_provider import (
    DeepSeekModel,
    GroundedLocalModel,
    build_model_provider,
)


def test_mlx_provider_uses_openai_compatible_local_endpoint_without_api_key() -> None:
    settings = Settings(
        _env_file=None,
        provider="mlx",
        api_key="",
        model="data/models/Qwen3-4B-Instruct-2507-4bit",
        model_base_url="http://127.0.0.1:18080/v1",
    )

    provider = build_model_provider(settings)

    assert isinstance(provider, DeepSeekModel)
    assert provider._temperature == 0.0


@pytest.mark.asyncio
async def test_deepseek_provider_uses_grounded_context() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer test-key"
        assert body["model"] == "deepseek-flash"
        assert body["max_tokens"] == 800
        assert "现货商品通常在付款后 24 小时内出库" in body["messages"][0]["content"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "现货商品通常在付款后 24 小时内出库。"}}]},
        )

    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    answer = await provider.answer(
        question="多久发货？", context=["现货商品通常在付款后 24 小时内出库"]
    )

    assert answer == "现货商品通常在付款后 24 小时内出库。"


@pytest.mark.asyncio
async def test_deepseek_provider_falls_back_when_api_is_unavailable() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    answer = await provider.answer(question="多久发货？", context=["现货商品 24 小时内出库。"])

    assert "现货商品 24 小时内出库" in answer


@pytest.mark.asyncio
async def test_deepseek_provider_applies_scenario_script_and_examples() -> None:
    captured: dict[str, list[dict[str, str]]] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["messages"] = json.loads(request.content)["messages"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "可以申请退款。"}}]},
        )

    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    answer = await provider.answer(
        question="我要退款",
        context=["签收后 7 天内、不影响二次销售可以申请退货。"],
        guidance=ReplyGuidance(intent=Intent.AFTER_SALES, authenticated=False),
    )

    messages = captured["messages"]
    system = messages[0]["content"]
    assert "退款规则咨询" in system
    assert "本场景禁止" in system
    assert "未登录" in system
    assert messages[-1] == {"role": "user", "content": "我要退款"}
    assert "独立的表达示例" in system
    assert len(messages) == 2
    assert answer == "可以申请退款。"


@pytest.mark.asyncio
async def test_deepseek_provider_streams_deltas() -> None:
    sse = (
        'data: {"choices":[{"delta":{"content":"可以"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"申请退款。"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    seen_stream_flag: list[bool] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_stream_flag.append(json.loads(request.content)["stream"])
        return httpx.Response(
            200,
            content=sse.encode(),
            headers={"content-type": "text/event-stream"},
        )

    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    chunks = [
        chunk
        async for chunk in provider.stream_answer(
            question="我要退款",
            context=["签收后 7 天内可以申请退货。"],
            guidance=ReplyGuidance(intent=Intent.AFTER_SALES, authenticated=False),
        )
    ]

    assert seen_stream_flag == [True]
    assert "".join(chunks) == "可以申请退款。"


@pytest.mark.asyncio
async def test_stream_falls_back_when_knowledge_is_required_but_missing() -> None:
    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        transport=httpx.MockTransport(lambda _: httpx.Response(500)),
    )

    chunks = [
        chunk
        async for chunk in provider.stream_answer(
            question="能开发票吗", context=[], guidance=ReplyGuidance(intent=Intent.FAQ)
        )
    ]

    assert "没有查到准确信息" in "".join(chunks)


@pytest.mark.parametrize("stream", [False, True])
async def test_outage_keeps_conversational_answers_without_unrelated_order_request(
    stream: bool,
) -> None:
    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        transport=httpx.MockTransport(lambda _: httpx.Response(503)),
    )
    cases = (
        ("在吗", [], "在的，您说。"),
        ("没事了谢谢", [], "不客气，有需要再来找我。"),
        ("能开发票吗", ["这款仅支持电子普通发票。"], "这款仅支持电子普通发票。"),
    )
    for question, context, expected in cases:
        if stream:
            answer = "".join(
                [
                    chunk
                    async for chunk in provider.stream_answer(question=question, context=context)
                ]
            )
        else:
            answer = await provider.answer(question=question, context=context)
        assert answer == expected


async def test_delay_fallback_does_not_invent_a_logistics_node_or_completed_action() -> None:
    answer = await GroundedLocalModel().answer(
        question="都五天了还没到",
        context=[],
        guidance=ReplyGuidance(intent=Intent.ORDER),
    )

    assert "五天" in answer
    assert "物流记录" in answer
    assert "{" not in answer
    assert "已" not in answer
    assert "24" not in answer


async def test_grounded_fallback_prefers_live_tool_evidence_for_order_status() -> None:
    answer = await GroundedLocalModel().answer(
        question="我的订单到哪了",
        context=["订单 NO123 当前状态为已付款。"],
        guidance=ReplyGuidance(intent=Intent.ORDER, authenticated=True),
    )

    assert answer == "订单 NO123 当前状态为已付款。"


async def test_grounded_fallback_normalizes_signed_delivery_evidence() -> None:
    answer = await GroundedLocalModel().answer(
        question="订单 NO124 签收了吗？",
        context=["可用知识：\n- 订单 NO124 已于 12:08 签收。"],
        guidance=ReplyGuidance(intent=Intent.ORDER, authenticated=True),
    )

    assert "已签收" in answer
    assert "12:08" in answer


async def test_grounded_fallback_does_not_flip_in_transit_evidence_to_signed() -> None:
    provider = GroundedLocalModel()

    answer = await provider.answer(
        question="这个包裹签收了吗？",
        context=["可用知识：\n- 当前状态为运输中，尚未签收。"],
        guidance=ReplyGuidance(intent=Intent.ORDER, authenticated=True),
    )

    assert "运输中" in answer
    assert "尚未签收" in answer
    assert "已签收" not in answer


@pytest.mark.parametrize("stream", [False, True])
async def test_style_examples_are_never_sent_as_current_user_history(stream: bool) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        messages = json.loads(request.content)["messages"]
        assert [item for item in messages if item["role"] == "user"] == [
            {"role": "user", "content": "有什么推荐"}
        ]
        assert not any(item["role"] == "assistant" for item in messages)
        assert "示例 1" in messages[0]["content"]  # 示例留在系统提示中，不伪装成会话历史。
        if stream:
            return httpx.Response(
                200,
                content='data: {"choices":[{"delta":{"content":"您想挑哪类商品？"}}]}\n\n',
                headers={"content-type": "text/event-stream"},
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": "您想挑哪类商品？"}}]})

    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )
    if stream:
        answer = "".join(
            [
                chunk
                async for chunk in provider.stream_answer(
                    question="有什么推荐", context=[], guidance=ReplyGuidance(intent=Intent.PRODUCT)
                )
            ]
        )
    else:
        answer = await provider.answer(
            question="有什么推荐", context=[], guidance=ReplyGuidance(intent=Intent.PRODUCT)
        )
    assert answer == "您想挑哪类商品？"


@pytest.mark.asyncio
async def test_grounded_fallback_summarizes_multiple_product_facts() -> None:
    context = [
        "商品：BUZUD Blood Pressure Monitor 30S\n售价：SGD 78.00\n"
        "商品页：/zh/p/buzud-blood-pressure-monitor-30s-8885020711097/",
        "商品：BUZUD Blood Pressure Monitor 30C\n售价：SGD 85.00\n"
        "商品页：/zh/p/buzud-blood-pressure-monitor-30c-8885020711103/",
    ]

    answer = await GroundedLocalModel().answer(
        question="家里老人血压高，推荐一款血压计", context=context
    )

    assert "为您找到以下商品" in answer
    assert "30S" in answer and "SGD 78.00" in answer
    assert "30C" in answer and "SGD 85.00" in answer
    assert "\n商品：" not in answer


@pytest.mark.asyncio
async def test_deepseek_flash_can_disable_thinking_for_support_answers() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["thinking"] == {"type": "disabled"}
        assert body["max_tokens"] == 800
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "为您找到以下商品。"}}]},
        )

    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        thinking=False,
        transport=httpx.MockTransport(handler),
    )

    answer = await provider.answer(question="推荐一款血压计", context=["商品资料"])

    assert answer == "为您找到以下商品。"


@pytest.mark.asyncio
async def test_deepseek_general_answer_uses_general_prompt_and_no_thinking() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["messages"][0]["role"] == "system"
        assert "general-purpose AI assistant" in body["messages"][0]["content"]
        assert body["thinking"] == {"type": "disabled"}
        assert body["max_tokens"] == 800
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Paris is the capital of France."}}]},
        )

    provider = DeepSeekModel(
        api_key="test-key",
        model="deepseek-flash",
        base_url="https://api.deepseek.com",
        timeout_seconds=2,
        thinking=False,
        transport=httpx.MockTransport(handler),
    )

    answer = await provider.answer_general(question="What is the capital of France?", english=True)

    assert answer == "Paris is the capital of France."


@pytest.mark.asyncio
async def test_grounded_general_answer_is_explicit_when_model_is_unavailable() -> None:
    answer = await GroundedLocalModel().answer_general(question="讲个笑话", english=False)

    assert "暂时无法回答通用问题" in answer
