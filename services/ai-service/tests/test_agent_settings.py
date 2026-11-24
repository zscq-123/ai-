from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from ai_service.api import agent_settings
from ai_service.config import settings
from ai_service.domain.models import Intent, SupportReply
from ai_service.main import app


@pytest.fixture(autouse=True)
def isolated_agent_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    monkeypatch.setattr(settings, "mailbox_state_file", str(tmp_path / "mailboxes.json"))


def test_agent_defaults_are_owned_by_backend() -> None:
    response = TestClient(app).get("/v1/agent/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft"] is True
    assert payload["handoff"] is True
    assert payload["translate"] is True
    assert payload["tone"] == "亲切自然"
    assert payload["cost_mode"] == "balanced"
    assert [skill["id"] for skill in payload["skills"]] == [
        "order-query",
        "product-recommendation",
        "after-sales-intake",
        "coupon-guidance",
    ]


def test_agent_settings_and_skills_persist_on_backend(tmp_path) -> None:
    client = TestClient(app)
    updated = client.put(
        "/v1/agent/settings",
        json={"tone": "简洁专业", "cost_mode": "quality", "translate": False},
    )
    skill = client.patch(
        "/v1/agent/skills/coupon-guidance",
        json={"enabled": True},
    )
    created = client.post("/v1/agent/skills", json={})

    assert updated.status_code == 200
    assert updated.json()["tone"] == "简洁专业"
    assert skill.status_code == 200
    assert skill.json()["enabled"] is True
    assert created.status_code == 201
    assert created.json()["id"].startswith("custom-")
    state_file = tmp_path / "agent-settings.json"
    assert state_file.exists()
    assert state_file.stat().st_mode & 0o777 == 0o600

    reloaded = client.get("/v1/agent/settings").json()
    assert reloaded["translate"] is False
    assert reloaded["cost_mode"] == "quality"
    assert reloaded["skills"][0]["id"].startswith("custom-")
    assert next(item for item in reloaded["skills"] if item["id"] == "coupon-guidance")[
        "enabled"
    ] is True


def test_agent_draft_uses_backend_service_and_runtime_settings(monkeypatch) -> None:
    answer = AsyncMock(
        return_value=SupportReply(
            "请提供订单号，我来帮您核对。",
            Intent.ORDER,
            requires_human=True,
        )
    )
    monkeypatch.setattr(agent_settings, "_answer_with_integration", answer)
    client = TestClient(app)

    response = client.post(
        "/v1/agent/draft",
        json={
            "channel": "email",
            "customer_name": "Customer",
            "subject": "Order",
            "message": "Where is my order?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "请提供订单号，我来帮您核对。"
    assert payload["intent"] == "order"
    assert payload["requires_human"] is True
    assert payload["handoff_recommended"] is True
    assert payload["language_assist_applied"] is True
    assert payload["skill_id"] == "order-query"
    answer.assert_awaited_once()
    assert answer.await_args.args[0].message == "Where is my order?"


def test_agent_draft_reuses_buzud_integration_without_storing_conversation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "buzud_integration_secret", "test-secret")
    response = TestClient(app).post(
        "/v1/agent/draft",
        json={
            "channel": "chat",
            "customer_name": "客户",
            "subject": "问候",
            "message": "你好",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].startswith("你好呀")
    assert payload["intent"] == "faq"
    assert payload["requires_human"] is False
    assert payload["skill_id"] is None


def test_disabled_reply_suggestion_is_enforced_by_backend(monkeypatch) -> None:
    answer = AsyncMock()
    monkeypatch.setattr(agent_settings, "_answer_with_integration", answer)
    client = TestClient(app)
    disabled = client.put("/v1/agent/settings", json={"draft": False})

    response = client.post(
        "/v1/agent/draft",
        json={
            "channel": "chat",
            "customer_name": "客户",
            "subject": "咨询",
            "message": "想了解这款商品",
        },
    )

    assert disabled.status_code == 200
    assert response.status_code == 409
    assert response.json()["detail"] == "回复建议已在 Agent 设置中停用"
    answer.assert_not_awaited()


def test_disabled_skill_is_enforced_by_backend(monkeypatch) -> None:
    answer = AsyncMock()
    monkeypatch.setattr(agent_settings, "_answer_with_integration", answer)
    client = TestClient(app)
    disabled = client.patch(
        "/v1/agent/skills/coupon-guidance",
        json={"enabled": False},
    )

    response = client.post(
        "/v1/agent/draft",
        json={
            "channel": "chat",
            "customer_name": "客户",
            "subject": "优惠券",
            "message": "优惠券怎么领取？",
        },
    )

    assert disabled.status_code == 200
    assert response.status_code == 409
    assert response.json()["detail"] == "优惠券说明技能当前已停用"
    answer.assert_not_awaited()
