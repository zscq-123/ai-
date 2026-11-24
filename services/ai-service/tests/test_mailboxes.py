import imaplib
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from ai_service.api import mailboxes
from ai_service.config import settings
from ai_service.main import app


@pytest.fixture(autouse=True)
def isolated_mailbox_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "mailbox_state_file", str(tmp_path / "mailboxes.json"))
    mailboxes._loaded_state_path = None
    mailboxes._local_conversation_cache.clear()
    mailboxes._local_mailbox_account_cache.clear()
    mailboxes._storefront_conversation_cache.clear()


class _FakeQQIMAP:
    def __init__(self, host: str, port: int, timeout: int):
        assert host == "imap.qq.com"
        assert port == 993
        assert timeout in {10, 12}

    def login(self, email: str, authorization_code: str) -> tuple[str, list[bytes]]:
        assert email == "123456@qq.com"
        assert authorization_code == "abcdefghijklmnop"
        return "OK", [b"LOGIN completed"]

    def status(self, mailbox: str, query: str) -> tuple[str, list[bytes]]:
        assert mailbox == "INBOX"
        assert query == "(MESSAGES UNSEEN UIDNEXT)"
        return "OK", [b'"INBOX" (MESSAGES 12 UNSEEN 3 UIDNEXT 501)']

    def select(self, mailbox: str, readonly: bool = False) -> tuple[str, list[bytes]]:
        assert mailbox == "INBOX"
        assert readonly is True
        return "OK", [b"12"]

    def uid(self, command: str, *args: str | None) -> tuple[str, list[bytes | tuple[bytes, bytes]]]:
        if command == "search":
            assert args == (None, "UID 501:*")
            return "OK", [b"501"]
        assert command == "fetch"
        uid, query = args
        assert uid == "501"
        if query == "(RFC822.SIZE)":
            return "OK", [b"1 (UID 501 RFC822.SIZE 258)"]
        assert query == "(BODY.PEEK[])"
        raw = (
            b"From: Customer One <customer@example.com>\r\n"
            b"Subject: Order delivery question\r\n"
            b"Date: Sun, 23 Nov 2026 13:10:00 +0800\r\n"
            b"Message-ID: <message-501@example.com>\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
            b"Could you check my delivery status?"
        )
        return "OK", [(b"1 (UID 501 BODY[])", raw), b")"]

    def logout(self) -> tuple[str, list[bytes]]:
        return "BYE", [b"LOGOUT completed"]


class _FakeQQReplyIMAP(_FakeQQIMAP):
    def uid(self, command: str, *args: str | None) -> tuple[str, list[bytes | tuple[bytes, bytes]]]:
        assert command == "fetch"
        assert args == (
            "501",
            "(BODY.PEEK[HEADER.FIELDS (FROM REPLY-TO SUBJECT MESSAGE-ID REFERENCES)])",
        )
        raw = (
            b"From: Customer One <customer@example.com>\r\n"
            b"Reply-To: replies@example.com\r\n"
            b"Subject: Order delivery question\r\n"
            b"Message-ID: <message-501@example.com>\r\n"
            b"References: <earlier@example.com>\r\n\r\n"
        )
        return "OK", [(b"1 (UID 501 BODY[])", raw), b")"]


class _FakeQQSMTP:
    sent = []

    def __init__(self, host: str, port: int, timeout: int):
        assert host == "smtp.qq.com"
        assert port == 465
        assert timeout == 12

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def login(self, email: str, authorization_code: str) -> None:
        assert email == "123456@qq.com"
        assert authorization_code == "abcdefghijklmnop"

    def send_message(self, message) -> None:
        self.sent.append(message)


def test_qq_mailbox_connector_is_disabled_by_default() -> None:
    response = TestClient(app).post(
        "/v1/mailboxes/qq/test",
        json={"email": "123456@qq.com", "authorization_code": "abcdefghijklmnop"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "本地邮箱连接器未启用"


def test_qq_mailbox_connection_returns_counts(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    monkeypatch.setattr(mailboxes.imaplib, "IMAP4_SSL", _FakeQQIMAP)

    response = TestClient(app).post(
        "/v1/mailboxes/qq/test",
        json={"email": "123456@qq.com", "authorization_code": "abcdefghijklmnop"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "server": "imap.qq.com:993",
        "messages": 12,
        "unread": 3,
        "last_uid": 500,
    }


def test_mailbox_connector_accepts_private_proxy_and_rejects_public_client(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)

    private_request = Request({"type": "http", "client": ("172.23.0.8", 43120)})
    mailboxes._require_local_connector(private_request)

    public_request = Request({"type": "http", "client": ("8.8.8.8", 43120)})
    with pytest.raises(HTTPException) as exc_info:
        mailboxes._require_local_connector(public_request)
    assert exc_info.value.status_code == 403


def test_qq_mailbox_sync_returns_only_new_messages(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    monkeypatch.setattr(mailboxes.imaplib, "IMAP4_SSL", _FakeQQIMAP)

    response = TestClient(app).post(
        "/v1/mailboxes/qq/sync",
        json={
            "email": "123456@qq.com",
            "authorization_code": "abcdefghijklmnop",
            "after_uid": 500,
            "limit": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_uid"] == 501
    assert payload["messages"] == [
        {
            "uid": 501,
            "message_id": "<message-501@example.com>",
            "sender_name": "Customer One",
            "sender_email": "customer@example.com",
            "subject": "Order delivery question",
            "text": "Could you check my delivery status?",
            "received_at": "2026-11-23T05:10:00+00:00",
        }
    ]


def test_qq_mailbox_reply_is_sent_without_persisting_demo_data(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    monkeypatch.setattr(mailboxes.imaplib, "IMAP4_SSL", _FakeQQReplyIMAP)
    monkeypatch.setattr(mailboxes.smtplib, "SMTP_SSL", _FakeQQSMTP)
    _FakeQQSMTP.sent.clear()

    response = TestClient(app).post(
        "/v1/mailboxes/qq/reply",
        json={
            "email": "123456@qq.com",
            "authorization_code": "abcdefghijklmnop",
            "uid": 501,
            "text": "您好，我们正在为您核实物流进度。",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "sent": True,
        "recipient": "replies@example.com",
        "subject": "Re: Order delivery question",
    }
    assert len(_FakeQQSMTP.sent) == 1
    sent = _FakeQQSMTP.sent[0]
    assert sent["To"] == "replies@example.com"
    assert sent["In-Reply-To"] == "<message-501@example.com>"
    assert "您好，我们正在为您核实物流进度。" in sent.get_content()
    assert mailboxes._local_conversation_cache == {}


def test_qq_mailbox_rejects_login_failure(monkeypatch) -> None:
    class RejectingQQIMAP(_FakeQQIMAP):
        def login(self, email: str, authorization_code: str) -> tuple[str, list[bytes]]:
            raise imaplib.IMAP4.error("authentication failed")

    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    monkeypatch.setattr(mailboxes.imaplib, "IMAP4_SSL", RejectingQQIMAP)

    response = TestClient(app).post(
        "/v1/mailboxes/qq/test",
        json={"email": "123456@qq.com", "authorization_code": "wrong-code"},
    )

    assert response.status_code == 401
    assert "授权码" in response.json()["detail"]


def test_local_conversations_are_shared_between_browser_sessions(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    mailboxes._local_conversation_cache.clear()
    payload = {
        "messages": [
            {
                "id": "qq-mailbox-501",
                "name": "Customer One",
                "initials": "CO",
                "store_id": "s1",
                "subject": "Order delivery question",
                "preview": "Could you check my delivery status?",
                "time": "13:10",
                "unread": True,
                "urgent": False,
                "color": "blue",
                "text": "Could you check my delivery status?",
            }
        ]
    }

    imported = TestClient(app).post("/v1/mailboxes/local/conversations", json=payload)
    listed = TestClient(app).get("/v1/mailboxes/local/conversations")

    assert imported.status_code == 204
    assert listed.status_code == 200
    assert listed.json() == payload["messages"]
    assert mailboxes._single_cached_mailbox_target() == ("mailbox", "s1")


def test_local_mailbox_accounts_are_shared_between_browser_sessions(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    mailboxes._local_mailbox_account_cache.clear()
    payload = {
        "accounts": [
            {
                "id": "mailbox",
                "email": "123456@qq.com",
                "provider": "QQ 邮箱",
                "store_id": "s1",
                "enabled": True,
                "connection": "imap-verified",
                "messages": 12,
                "unread": 3,
                "last_uid": 500,
            }
        ]
    }

    imported = TestClient(app).post("/v1/mailboxes/local/accounts", json=payload)
    listed = TestClient(app).get("/v1/mailboxes/local/accounts")

    assert imported.status_code == 204
    assert listed.status_code == 200
    assert listed.json() == payload["accounts"]


def test_local_mailbox_state_survives_process_reload(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    state_file = tmp_path / "persistent-mailboxes.json"
    monkeypatch.setattr(settings, "mailbox_state_file", str(state_file))
    mailboxes._loaded_state_path = None
    payload = {
        "accounts": [
            {
                "id": "mailbox",
                "email": "123456@qq.com",
                "provider": "QQ 邮箱",
                "store_id": "s1",
                "enabled": True,
                "connection": "imap-verified",
                "messages": 12,
                "unread": 3,
                "last_uid": 500,
            }
        ]
    }

    imported = TestClient(app).post("/v1/mailboxes/local/accounts", json=payload)
    mailboxes._local_mailbox_account_cache.clear()
    mailboxes._loaded_state_path = None
    listed = TestClient(app).get("/v1/mailboxes/local/accounts")

    assert imported.status_code == 204
    assert state_file.stat().st_mode & 0o777 == 0o600
    assert listed.json() == payload["accounts"]


def test_storefront_conversation_is_grouped_and_persisted(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    state_file = tmp_path / "persistent-mailboxes.json"
    monkeypatch.setattr(settings, "mailbox_state_file", str(state_file))
    conversation_id = uuid4()

    mailboxes.record_storefront_conversation(
        conversation_id,
        "这款血糖仪怎么使用？",
        "我来帮你说明使用步骤。",
        authenticated=False,
        product_id=None,
        requires_human=False,
    )
    mailboxes.record_storefront_conversation(
        conversation_id,
        "我要转人工",
        "好的，我会交给人工客服继续跟进。",
        authenticated=False,
        product_id=None,
        requires_human=True,
    )

    listed = TestClient(app).get("/v1/mailboxes/storefront/conversations")

    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload) == 1
    assert payload[0]["id"] == f"storefront-{conversation_id}"
    assert payload[0]["urgent"] is True
    assert payload[0]["subject"] == "需要人工跟进的商城咨询"
    assert payload[0]["handoff_status"] == "pending"
    assert [item["role"] for item in payload[0]["messages"]] == [
        "customer",
        "agent",
        "customer",
        "agent",
    ]

    mailboxes._storefront_conversation_cache.clear()
    mailboxes._loaded_state_path = None
    reloaded = TestClient(app).get("/v1/mailboxes/storefront/conversations")
    assert reloaded.json() == payload


def test_storefront_handoff_can_be_claimed_replied_and_resolved(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "mailbox_local_connector_enabled", True)
    monkeypatch.setattr(settings, "mailbox_state_file", str(tmp_path / "mailboxes.json"))
    conversation_id = uuid4()
    key = f"storefront-{conversation_id}"
    mailboxes.record_storefront_conversation(
        conversation_id,
        "我要转人工",
        "已为你提交人工请求。",
        authenticated=False,
        product_id=None,
        requires_human=True,
    )
    client = TestClient(app)

    claimed = client.patch(
        f"/v1/mailboxes/storefront/conversations/{key}/handoff",
        json={"status": "claimed", "assigned_to": "客服小诺"},
    )
    replied = client.post(
        f"/v1/mailboxes/storefront/conversations/{key}/replies",
        json={"text": "你好，我是人工客服，正在为你核实。", "agent_name": "客服小诺"},
    )

    assert claimed.status_code == 200
    assert claimed.json()["handoff_status"] == "claimed"
    assert replied.status_code == 200
    assert replied.json()["messages"][-1]["text"] == "你好，我是人工客服，正在为你核实。"
    assert replied.json()["human_replies"] == [
        {
            "sequence": 1,
            "text": "你好，我是人工客服，正在为你核实。",
            "time": replied.json()["human_replies"][0]["time"],
            "agent_name": "客服小诺",
        }
    ]
    snapshot = mailboxes.storefront_handoff_snapshot(conversation_id)
    assert snapshot["status"] == "claimed"
    assert len(snapshot["replies"]) == 1

    resolved = client.patch(
        f"/v1/mailboxes/storefront/conversations/{key}/handoff",
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["handoff_status"] == "resolved"
    assert resolved.json()["urgent"] is False
