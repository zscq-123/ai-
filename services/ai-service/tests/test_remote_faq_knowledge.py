import hashlib
import hmac
import json
from uuid import uuid4

import httpx

from ai_service.infrastructure.remote_faq_knowledge import RemoteFaqKnowledgeRetriever


async def test_exact_published_faq_is_returned_with_merchant_scope() -> None:
    merchant_id = uuid4()
    secret = "s" * 32

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/internal/support/knowledge-search"
        body = request.content.decode()
        assert json.loads(body) == {
            "query": "能开发票吗？",
            "merchantId": str(merchant_id),
        }
        timestamp = request.headers["X-Nova-Timestamp"]
        expected = hmac.new(
            secret.encode(),
            f"{timestamp}\nPOST\n{request.url.path}\n{body}".encode(),
            hashlib.sha256,
        ).hexdigest()
        assert request.headers["X-Nova-Signature"] == expected
        return httpx.Response(
            200,
            json=[
                {
                    "documentId": "81000000-0000-0000-0000-000000000001",
                    "title": "发票政策",
                    "content": "能否开票以商品说明为准。",
                    "source": "knowledge://merchant/invoice",
                }
            ],
        )

    retriever = RemoteFaqKnowledgeRetriever(
        "http://commerce.test", secret, transport=httpx.MockTransport(handler)
    )
    results = await retriever.search("能开发票吗？", merchant_id=merchant_id)

    assert results[0][0] == "能否开票以商品说明为准。"
    assert results[0][1].reference == "knowledge://merchant/invoice"


async def test_remote_failure_returns_empty_for_local_fallback() -> None:
    retriever = RemoteFaqKnowledgeRetriever(
        "http://commerce.test",
        "s" * 32,
        transport=httpx.MockTransport(lambda _: httpx.Response(503)),
    )

    assert await retriever.search("能开发票吗？", merchant_id=uuid4()) == []


async def test_remote_failure_uses_cooldown_before_retrying() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    retriever = RemoteFaqKnowledgeRetriever(
        "http://commerce.test",
        "s" * 32,
        failure_cooldown_seconds=30,
        transport=httpx.MockTransport(handler),
    )

    merchant_id = uuid4()
    assert await retriever.search("能开发票吗？", merchant_id=merchant_id) == []
    assert await retriever.search("怎么退货？", merchant_id=merchant_id) == []
    assert calls == 1
