from fastapi.testclient import TestClient

from ai_service.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-service"}


def test_metrics_are_exposed() -> None:
    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert "commerce_ai_chat_requests_total" in response.text
