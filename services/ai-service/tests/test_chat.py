from fastapi.testclient import TestClient

from ai_service.main import app

client = TestClient(app)


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
