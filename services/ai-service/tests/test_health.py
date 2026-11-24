from fastapi.testclient import TestClient

from ai_service.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-service"}


def test_local_readiness_reports_online_store_configuration() -> None:
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["store_url"] == "https://154.36.185.46:18083"
    assert payload["mailbox_state_persistence"] is True


def test_metrics_are_exposed() -> None:
    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert "commerce_ai_chat_requests_total" in response.text
