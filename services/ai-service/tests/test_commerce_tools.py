import hashlib
import hmac
import json
from uuid import uuid4

import httpx

from ai_service.infrastructure.commerce_tools import CommerceSupportTools


async def test_commerce_tools_signs_scoped_request_and_returns_evidence() -> None:
    customer_id = uuid4()
    merchant_id = uuid4()
    product_id = uuid4()
    sku_id = uuid4()

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        canonical = "\n".join(
            (str(customer_id), str(merchant_id), str(product_id), str(sku_id), "这款有现货吗？")
        )
        expected = hmac.new(b"tool-secret", canonical.encode(), hashlib.sha256).hexdigest()
        assert request.headers["X-Nova-Tool-Signature"] == expected
        assert body == {
            "message": "这款有现货吗？",
            "customerId": str(customer_id),
            "merchantId": str(merchant_id),
            "productId": str(product_id),
            "skuId": str(sku_id),
        }
        return httpx.Response(
            200,
            json=[
                {
                    "content": "当前可售库存 3 件。",
                    "title": "实时库存",
                    "reference": f"inventory://{sku_id}",
                }
            ],
        )

    tools = CommerceSupportTools(
        "http://commerce.test",
        "tool-secret",
        transport=httpx.MockTransport(handler),
    )

    evidence = await tools.lookup(
        "这款有现货吗？",
        customer_id=customer_id,
        merchant_id=merchant_id,
        product_id=product_id,
        sku_id=sku_id,
    )

    assert evidence[0][0] == "当前可售库存 3 件。"
    assert evidence[0][1].reference == f"inventory://{sku_id}"


async def test_commerce_tools_fail_closed_when_service_is_unavailable() -> None:
    tools = CommerceSupportTools(
        "http://commerce.test",
        "tool-secret",
        transport=httpx.MockTransport(lambda _: httpx.Response(503)),
    )

    assert await tools.lookup("我的订单到哪了", customer_id=uuid4()) == []
