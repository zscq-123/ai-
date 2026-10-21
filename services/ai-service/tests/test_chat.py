import hashlib
import hmac
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from ai_service.api import chat as chat_api
from ai_service.main import app

client = TestClient(app)


def trusted_headers(
    *, customer_id: UUID | None = None, merchant_id: UUID | None = None
) -> dict[str, str]:
    content = f"{customer_id or ''}\n{merchant_id or ''}".encode()
    signature = hmac.new(
        chat_api.settings.trusted_context_secret.encode(), content, hashlib.sha256
    ).hexdigest()
    headers = {"X-Nova-Context-Signature": signature}
    if customer_id is not None:
        headers["X-Nova-Customer-Id"] = str(customer_id)
    if merchant_id is not None:
        headers["X-Nova-Merchant-Id"] = str(merchant_id)
    return headers


def test_grounded_answer_contains_citation() -> None:
    response = client.post("/v1/support/chat", json={"message": "第三方商品是谁提供的？"})
    assert response.status_code == 200
    assert response.json()["citations"]


def test_refund_requires_authentication_and_confirmation() -> None:
    response = client.post("/v1/support/chat", json={"message": "我要退款"})
    assert response.status_code == 200
    assert response.json()["requires_confirmation"] is True


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


def test_chat_rejects_unknown_or_inactive_merchant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_api.recorder, "merchant_is_active", lambda _merchant_id: False)

    response = client.post(
        "/v1/support/chat",
        json={"message": "商品什么时候发货？"},
        headers=trusted_headers(merchant_id=uuid4()),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Active merchant not found"}
