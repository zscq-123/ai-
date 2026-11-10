import hashlib
import hmac
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from ai_service.api import chat as chat_api
from ai_service.config import settings as test_settings
from ai_service.domain.models import Intent, SupportReply
from ai_service.main import app

client = TestClient(app)


def trusted_headers(
    *,
    customer_id: UUID | None = None,
    merchant_id: UUID | None = None,
    product_id: UUID | None = None,
    sku_id: UUID | None = None,
) -> dict[str, str]:
    content = (
        f"{customer_id or ''}\n{merchant_id or ''}\n{product_id or ''}\n{sku_id or ''}"
    ).encode()
    signature = hmac.new(
        test_settings.trusted_context_secret.encode(), content, hashlib.sha256
    ).hexdigest()
    headers = {"X-Nova-Context-Signature": signature}
    if customer_id is not None:
        headers["X-Nova-Customer-Id"] = str(customer_id)
    if merchant_id is not None:
        headers["X-Nova-Merchant-Id"] = str(merchant_id)
    if product_id is not None:
        headers["X-Nova-Product-Id"] = str(product_id)
    if sku_id is not None:
        headers["X-Nova-Sku-Id"] = str(sku_id)
    return headers


def test_grounded_answer_contains_citation() -> None:
    response = client.post("/v1/support/chat", json={"message": "第三方商品是谁提供的？"})
    assert response.status_code == 200
    assert response.json()["citations"]


def test_refund_operation_requires_human_fund_review() -> None:
    response = client.post("/v1/support/chat", json={"message": "我要退款"})
    assert response.status_code == 200
    assert response.json()["requires_human"] is True


def test_human_handoff() -> None:
    response = client.post("/v1/support/chat", json={"message": "我要投诉并转人工"})
    assert response.json()["requires_human"] is True


def test_chat_passes_merchant_to_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    merchant_id = uuid4()
    recorded: list[UUID | None] = []

    def record(*_: object, merchant_id: UUID | None) -> None:
        recorded.append(merchant_id)

    monkeypatch.setattr(chat_api.recorder, "record", record)

    response = client.post(
        "/v1/support/chat",
        json={"message": "商品什么时候发货？"},
        headers=trusted_headers(merchant_id=merchant_id),
    )

    assert response.status_code == 200
    assert recorded == [merchant_id]


def test_stream_passes_merchant_and_returns_complete_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    merchant_id = uuid4()
    recorded: list[UUID | None] = []

    def record(*_: object, merchant_id: UUID | None) -> None:
        recorded.append(merchant_id)

    monkeypatch.setattr(chat_api.recorder, "record", record)

    response = client.post(
        "/v1/support/stream",
        json={"message": "我要投诉并转人工"},
        headers=trusted_headers(merchant_id=merchant_id),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: answer" in response.text
    assert "event: done" in response.text
    assert '"requires_human": true' in response.text
    assert recorded == [merchant_id]


def test_chat_keeps_legacy_request_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[UUID | None] = []

    def record(*_: object, merchant_id: UUID | None) -> None:
        recorded.append(merchant_id)

    monkeypatch.setattr(chat_api.recorder, "record", record)

    response = client.post("/v1/support/chat", json={"message": "商品什么时候发货？"})

    assert response.status_code == 200
    assert recorded == [None]


def test_chat_rejects_client_asserted_identity() -> None:
    response = client.post(
        "/v1/support/chat",
        json={"message": "商品什么时候发货？", "merchant_id": "not-a-uuid"},
    )

    assert response.status_code == 422


def test_chat_rejects_unsigned_trusted_context() -> None:
    response = client.post(
        "/v1/support/chat",
        json={"message": "商品什么时候发货？"},
        headers={"X-Nova-Merchant-Id": str(uuid4())},
    )
    assert response.status_code == 401


def test_chat_passes_signed_product_context_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    product_id = uuid4()
    sku_id = uuid4()
    received: list[tuple[UUID | None, UUID | None]] = []

    async def answer(_: str, **kwargs: object) -> SupportReply:
        received.append(
            (
                cast(UUID | None, kwargs.get("product_id")),
                cast(UUID | None, kwargs.get("sku_id")),
            )
        )
        return SupportReply("已核对。", Intent.PRODUCT)

    monkeypatch.setattr(chat_api.service, "answer", answer)

    response = client.post(
        "/v1/support/chat",
        json={"message": "这款有现货吗？"},
        headers=trusted_headers(product_id=product_id, sku_id=sku_id),
    )

    assert response.status_code == 200
    assert received == [(product_id, sku_id)]


def test_chat_rejects_unknown_or_inactive_merchant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_api.recorder, "merchant_is_active", lambda _merchant_id: False)

    response = client.post(
        "/v1/support/chat",
        json={"message": "商品什么时候发货？"},
        headers=trusted_headers(merchant_id=uuid4()),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Active merchant not found"}


def test_stream_emits_delta_for_model_answers() -> None:
    response = client.post("/v1/support/stream", json={"message": "你好"})

    assert response.status_code == 200
    assert "event: delta" in response.text
    assert "event: answer" in response.text
    assert "event: done" in response.text
