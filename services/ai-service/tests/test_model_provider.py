import json

import httpx
import pytest

from ai_service.infrastructure.model_provider import DeepSeekModel


@pytest.mark.asyncio
async def test_deepseek_provider_uses_grounded_context() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer test-key"
        assert body["model"] == "deepseek-flash"
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
