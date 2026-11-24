import asyncio
import contextlib
import imaplib
import ipaddress
import json
import logging
import re
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import formatdate, make_msgid, parseaddr, parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr, field_validator

from ai_service.config import settings

router = APIRouter(prefix="/v1/mailboxes", tags=["mailboxes"])

QQ_IMAP_HOST = "imap.qq.com"
QQ_IMAP_PORT = 993
QQ_SMTP_HOST = "smtp.qq.com"
QQ_SMTP_PORT = 465


class QQMailboxTestRequest(BaseModel):
    email: str = Field(min_length=6, max_length=254)
    authorization_code: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_qq_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9._%+-]+@(qq|foxmail)\.com", normalized):
            raise ValueError("请输入有效的 @qq.com 或 @foxmail.com 邮箱地址")
        return normalized


class QQMailboxTestResponse(BaseModel):
    connected: bool
    server: str
    messages: int
    unread: int
    last_uid: int


class QQMailboxSyncRequest(QQMailboxTestRequest):
    after_uid: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=20)
    mailbox_id: str | None = Field(default=None, min_length=1, max_length=80)
    store_id: str | None = Field(default=None, min_length=1, max_length=80)


class QQSyncedMessage(BaseModel):
    uid: int
    message_id: str
    sender_name: str
    sender_email: str
    subject: str
    text: str
    received_at: str


class QQMailboxSyncResponse(BaseModel):
    last_uid: int
    messages: list[QQSyncedMessage]


class QQMailboxReplyRequest(QQMailboxTestRequest):
    uid: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=10_000)

    @field_validator("text")
    @classmethod
    def validate_reply_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("回复内容不能为空")
        return normalized


class QQMailboxReplyResponse(BaseModel):
    sent: bool
    recipient: str
    subject: str


class LocalMailboxConversation(BaseModel):
    id: str = Field(min_length=5, max_length=160, pattern=r"^qq-")
    name: str = Field(min_length=1, max_length=254)
    initials: str = Field(min_length=1, max_length=8)
    store_id: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=998)
    preview: str = Field(max_length=500)
    time: str = Field(min_length=1, max_length=20)
    unread: bool = True
    urgent: bool = False
    color: str = Field(default="blue", max_length=30)
    text: str = Field(max_length=4000)
    mailbox_id: str | None = Field(default=None, min_length=1, max_length=80)
    mailbox_uid: int | None = Field(default=None, ge=1)
    sender_email: str | None = Field(default=None, max_length=254)
    message_id: str | None = Field(default=None, max_length=998)


class LocalMailboxImportRequest(BaseModel):
    messages: list[LocalMailboxConversation] = Field(max_length=50)


class LocalMailboxAccount(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=6, max_length=254)
    provider: str = Field(min_length=1, max_length=80)
    store_id: str = Field(min_length=1, max_length=80)
    enabled: bool = True
    connection: str = Field(default="imap-verified", max_length=40)
    messages: int = Field(default=0, ge=0)
    unread: int = Field(default=0, ge=0)
    last_uid: int = Field(default=0, ge=0)


class LocalMailboxAccountImportRequest(BaseModel):
    accounts: list[LocalMailboxAccount] = Field(max_length=20)


class StorefrontConversationTurn(BaseModel):
    role: Literal["customer", "agent"]
    text: str = Field(min_length=1, max_length=4000)
    time: str = Field(min_length=1, max_length=20)


class StorefrontHumanReply(BaseModel):
    sequence: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)
    time: str = Field(min_length=1, max_length=20)
    agent_name: str = Field(min_length=1, max_length=80)


class StorefrontConversation(BaseModel):
    id: str = Field(min_length=47, max_length=160, pattern=r"^storefront-")
    name: str = Field(min_length=1, max_length=120)
    initials: str = Field(min_length=1, max_length=8)
    store_id: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=200)
    preview: str = Field(min_length=1, max_length=500)
    time: str = Field(min_length=1, max_length=20)
    unread: bool = True
    urgent: bool = False
    status: Literal["open", "resolved"] = "open"
    color: str = Field(default="green", max_length=30)
    messages: list[StorefrontConversationTurn] = Field(max_length=80)
    handoff_status: Literal["none", "pending", "claimed", "resolved"] = "none"
    assigned_to: str | None = Field(default=None, min_length=1, max_length=80)
    human_replies: list[StorefrontHumanReply] = Field(default_factory=list, max_length=80)


class StorefrontHandoffUpdate(BaseModel):
    status: Literal["pending", "claimed", "resolved"]
    assigned_to: str | None = Field(default=None, min_length=1, max_length=80)


class StorefrontHumanReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    agent_name: str = Field(default="NOVA 客服", min_length=1, max_length=80)

    @field_validator("text", "agent_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("内容不能为空")
        return normalized


_local_conversation_cache: dict[str, LocalMailboxConversation] = {}
_local_mailbox_account_cache: dict[str, LocalMailboxAccount] = {}
_storefront_conversation_cache: dict[str, StorefrontConversation] = {}
_loaded_state_path: Path | None = None
logger = logging.getLogger(__name__)


def _mailbox_state_path() -> Path | None:
    configured = settings.mailbox_state_file.strip()
    return Path(configured).expanduser() if configured else None


def _ensure_local_state_loaded() -> None:
    global _loaded_state_path
    path = _mailbox_state_path()
    if path is None or _loaded_state_path == path:
        return
    _loaded_state_path = path
    _local_conversation_cache.clear()
    _local_mailbox_account_cache.clear()
    _storefront_conversation_cache.clear()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except (OSError, ValueError):
        logger.warning("mailbox_state_load_failed path=%s", path)
        return
    if not isinstance(payload, dict):
        return
    for item in payload.get("conversations", []):
        with contextlib.suppress(ValueError, TypeError):
            local_conversation = LocalMailboxConversation.model_validate(item)
            _local_conversation_cache[local_conversation.id] = local_conversation
    for item in payload.get("accounts", []):
        with contextlib.suppress(ValueError, TypeError):
            account = LocalMailboxAccount.model_validate(item)
            _local_mailbox_account_cache[account.id] = account
    for item in payload.get("storefront_conversations", []):
        with contextlib.suppress(ValueError, TypeError):
            storefront_conversation = StorefrontConversation.model_validate(item)
            _storefront_conversation_cache[storefront_conversation.id] = storefront_conversation


def _persist_local_state() -> None:
    path = _mailbox_state_path()
    if path is None:
        return
    _ensure_local_state_loaded()
    payload = {
        "version": 1,
        "conversations": [
            item.model_dump(mode="json", exclude_none=True)
            for item in _local_conversation_cache.values()
        ],
        "accounts": [
            item.model_dump(mode="json") for item in _local_mailbox_account_cache.values()
        ],
        "storefront_conversations": [
            item.model_dump(mode="json")
            for item in _storefront_conversation_cache.values()
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    temporary.replace(path)


def record_storefront_conversation(
    conversation_id: UUID,
    question: str,
    answer: str,
    *,
    authenticated: bool,
    product_id: UUID | None,
    requires_human: bool,
    occurred_at: datetime | None = None,
) -> None:
    if not settings.mailbox_local_connector_enabled:
        return
    _ensure_local_state_loaded()
    key = f"storefront-{conversation_id}"
    existing = _storefront_conversation_cache.get(key)
    recorded_at = occurred_at or datetime.now(ZoneInfo("Asia/Shanghai"))
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    timestamp = recorded_at.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%H:%M")
    turns = list(existing.messages) if existing else []
    turns.extend(
        [
            StorefrontConversationTurn(role="customer", text=question, time=timestamp),
            StorefrontConversationTurn(role="agent", text=answer, time=timestamp),
        ]
    )
    handoff_status: Literal["none", "pending", "claimed", "resolved"] = "none"
    assigned_to = existing.assigned_to if existing else None
    if existing and existing.handoff_status in {"pending", "claimed"}:
        handoff_status = existing.handoff_status
    if requires_human and handoff_status != "claimed":
        handoff_status = "pending"
    urgent = handoff_status in {"pending", "claimed"}
    subject = "商品咨询" if product_id else "商城在线咨询"
    if urgent:
        subject = "需要人工跟进的商城咨询"
    _storefront_conversation_cache[key] = StorefrontConversation(
        id=key,
        name="登录客户" if authenticated else "商城访客",
        initials="客",
        store_id="chungyip",
        subject=subject,
        preview=question[:120],
        time=timestamp,
        unread=True,
        urgent=urgent,
        status="open",
        color="green",
        messages=turns[-80:],
        handoff_status=handoff_status,
        assigned_to=assigned_to,
        human_replies=list(existing.human_replies) if existing else [],
    )
    try:
        _persist_local_state()
    except OSError:
        logger.exception("storefront_conversation_persist_failed id=%s", key)


def storefront_handoff_snapshot(
    conversation_id: UUID, after_sequence: int = 0
) -> dict[str, object]:
    _ensure_local_state_loaded()
    conversation = _storefront_conversation_cache.get(f"storefront-{conversation_id}")
    if conversation is None:
        return {"status": "none", "assigned_to": None, "replies": []}
    return {
        "status": conversation.handoff_status,
        "assigned_to": conversation.assigned_to,
        "replies": [
            reply.model_dump(mode="json")
            for reply in conversation.human_replies
            if reply.sequence > after_sequence
        ],
    }


def _storefront_conversation(conversation_id: str) -> StorefrontConversation:
    _ensure_local_state_loaded()
    conversation = _storefront_conversation_cache.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="商城会话不存在")
    return conversation


def _save_storefront_conversation(conversation: StorefrontConversation) -> StorefrontConversation:
    _storefront_conversation_cache[conversation.id] = conversation
    try:
        _persist_local_state()
    except OSError as exc:
        logger.exception("storefront_conversation_persist_failed id=%s", conversation.id)
        raise HTTPException(status_code=503, detail="商城会话状态暂时无法保存") from exc
    return conversation


def _cache_synced_messages(
    messages: list[QQSyncedMessage], mailbox_id: str, store_id: str
) -> None:
    _ensure_local_state_loaded()
    for message in messages:
        name = message.sender_name or message.sender_email or "QQ 邮箱客户"
        received = datetime.now(ZoneInfo("Asia/Shanghai"))
        if message.received_at:
            with contextlib.suppress(ValueError):
                received = datetime.fromisoformat(message.received_at).astimezone(
                    ZoneInfo("Asia/Shanghai")
                )
        text = message.text.strip() or "（邮件正文为空）"
        conversation = LocalMailboxConversation(
            id=f"qq-{mailbox_id}-{message.uid}",
            name=name,
            initials="".join(list(name)[:2]).upper(),
            store_id=store_id,
            subject=message.subject or "（无主题）",
            preview=text[:120],
            time=received.strftime("%H:%M"),
            unread=True,
            urgent=False,
            color="blue",
            text=text,
            mailbox_id=mailbox_id,
            mailbox_uid=message.uid,
            sender_email=message.sender_email,
            message_id=message.message_id,
        )
        _local_conversation_cache[conversation.id] = conversation


def _update_cached_mailbox_account(
    mailbox_id: str, messages: list[QQSyncedMessage], last_uid: int
) -> None:
    _ensure_local_state_loaded()
    account = _local_mailbox_account_cache.get(mailbox_id)
    if not account:
        return
    added = len(messages)
    _local_mailbox_account_cache[mailbox_id] = account.model_copy(
        update={
            "messages": account.messages + added,
            "unread": account.unread + added,
            "last_uid": max(account.last_uid, last_uid),
        }
    )


def _single_cached_mailbox_target() -> tuple[str, str] | None:
    _ensure_local_state_loaded()
    targets = {
        (message.id.removeprefix("qq-").rsplit("-", 1)[0], message.store_id)
        for message in _local_conversation_cache.values()
    }
    return next(iter(targets)) if len(targets) == 1 else None


@dataclass(frozen=True)
class _MailboxStatus:
    messages: int
    unread: int
    last_uid: int


@dataclass(frozen=True)
class _ReplyTarget:
    recipient: str
    subject: str
    message_id: str
    references: str


def _parse_status(data: list[bytes | None]) -> _MailboxStatus:
    raw = b" ".join(item for item in data if item)
    values = {name.upper(): int(value) for name, value in re.findall(
        rb"(MESSAGES|UNSEEN|UIDNEXT)\s+(\d+)", raw, re.IGNORECASE
    )}
    uid_next = values.get(b"UIDNEXT", 1)
    return _MailboxStatus(
        messages=values.get(b"MESSAGES", 0),
        unread=values.get(b"UNSEEN", 0),
        last_uid=max(0, uid_next - 1),
    )


def _test_qq_imap(email: str, authorization_code: str) -> _MailboxStatus:
    client: imaplib.IMAP4_SSL | None = None
    try:
        client = imaplib.IMAP4_SSL(QQ_IMAP_HOST, QQ_IMAP_PORT, timeout=10)
        client.login(email, authorization_code)
        status, data = client.status("INBOX", "(MESSAGES UNSEEN UIDNEXT)")
        if status != "OK":
            raise OSError("QQ IMAP did not return mailbox status")
        return _parse_status(data)
    finally:
        if client is not None:
            with contextlib.suppress(imaplib.IMAP4.error, OSError):
                client.logout()


def _payload_bytes(data: list[bytes | tuple[bytes, bytes] | None]) -> bytes:
    return b"\n".join(item[1] for item in data if isinstance(item, tuple) and item[1])


def _plain_text(message: Message) -> str:
    candidates: list[str] = []
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type not in {"text/plain", "text/html"}:
            continue
        payload = part.get_payload(decode=True)
        if isinstance(payload, bytes):
            content = payload.decode(
                part.get_content_charset() or "utf-8",
                errors="replace",
            )
        else:
            raw_payload = part.get_payload()
            content = raw_payload if isinstance(raw_payload, str) else ""
        if content_type == "text/html":
            content = re.sub(
                r"<style\b[^>]*>.*?</style>|<script\b[^>]*>.*?</script>",
                " ",
                content,
                flags=re.IGNORECASE | re.DOTALL,
            )
            content = re.sub(r"<[^>]+>", " ", content)
            content = unescape(content)
        normalized = re.sub(r"\s+", " ", content).strip()
        if normalized:
            candidates.append(normalized)
        if content_type == "text/plain" and normalized:
            break
    return (candidates[0] if candidates else "（邮件正文为空）")[:4000]


def _parse_message(uid: int, raw: bytes, *, oversized: bool = False) -> QQSyncedMessage:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    sender_name, sender_email = parseaddr(str(message.get("From", "")))
    subject = str(message.get("Subject", "（无主题）")) or "（无主题）"
    message_id = str(message.get("Message-ID", "")).strip() or f"qq-imap-{uid}"
    date_header = str(message.get("Date", ""))
    try:
        received = parsedate_to_datetime(date_header)
        if received.tzinfo is None:
            received = received.replace(tzinfo=UTC)
        received_at = received.astimezone(UTC).isoformat()
    except (TypeError, ValueError, OverflowError):
        received_at = ""
    text = (
        "邮件内容较大，当前仅同步标题，请在 QQ 邮箱中查看全文。"
        if oversized
        else _plain_text(message)
    )
    return QQSyncedMessage(
        uid=uid,
        message_id=message_id,
        sender_name=sender_name.strip() or sender_email or "QQ 邮箱客户",
        sender_email=sender_email.strip().lower(),
        subject=subject,
        text=text,
        received_at=received_at,
    )


def _sync_qq_imap(
    email: str,
    authorization_code: str,
    after_uid: int,
    limit: int,
) -> QQMailboxSyncResponse:
    client: imaplib.IMAP4_SSL | None = None
    try:
        client = imaplib.IMAP4_SSL(QQ_IMAP_HOST, QQ_IMAP_PORT, timeout=12)
        client.login(email, authorization_code)
        status, _ = client.select("INBOX", readonly=True)
        if status != "OK":
            raise OSError("QQ IMAP did not open INBOX")
        status, search_data = cast(Any, client.uid)(
            "search", None, f"UID {after_uid + 1}:*"
        )
        if status != "OK":
            raise OSError("QQ IMAP search failed")
        uid_bytes = search_data[0] if search_data and search_data[0] else b""
        uids = [
            int(value)
            for value in uid_bytes.split()
            if value.isdigit() and int(value) > after_uid
        ]
        selected = uids[:limit]
        messages: list[QQSyncedMessage] = []
        for uid in selected:
            size_status, size_data = client.uid("fetch", str(uid), "(RFC822.SIZE)")
            if size_status != "OK":
                continue
            size_blob = b" ".join(
                item[0] if isinstance(item, tuple) else item
                for item in size_data
                if item
            )
            size_match = re.search(rb"RFC822\.SIZE\s+(\d+)", size_blob, re.IGNORECASE)
            oversized = bool(size_match and int(size_match.group(1)) > 262_144)
            fetch_query = (
                "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])"
                if oversized
                else "(BODY.PEEK[])"
            )
            fetch_status, fetch_data = client.uid("fetch", str(uid), fetch_query)
            if fetch_status != "OK":
                continue
            raw = _payload_bytes(fetch_data)
            if raw:
                messages.append(_parse_message(uid, raw, oversized=oversized))
        return QQMailboxSyncResponse(
            last_uid=max([after_uid, *[message.uid for message in messages]]),
            messages=messages,
        )
    finally:
        if client is not None:
            with contextlib.suppress(imaplib.IMAP4.error, OSError):
                client.logout()


def _qq_reply_target(
    email: str,
    authorization_code: str,
    uid: int,
) -> _ReplyTarget:
    client: imaplib.IMAP4_SSL | None = None
    try:
        client = imaplib.IMAP4_SSL(QQ_IMAP_HOST, QQ_IMAP_PORT, timeout=12)
        client.login(email, authorization_code)
        status, _ = client.select("INBOX", readonly=True)
        if status != "OK":
            raise OSError("QQ IMAP did not open INBOX")
        fetch_status, fetch_data = client.uid(
            "fetch",
            str(uid),
            "(BODY.PEEK[HEADER.FIELDS (FROM REPLY-TO SUBJECT MESSAGE-ID REFERENCES)])",
        )
        if fetch_status != "OK":
            raise OSError("QQ IMAP reply target fetch failed")
        raw = _payload_bytes(fetch_data)
        if not raw:
            raise OSError("QQ IMAP message does not exist")
        message = BytesParser(policy=policy.default).parsebytes(raw)
        _, recipient = parseaddr(
            str(message.get("Reply-To") or message.get("From") or "")
        )
        recipient = recipient.strip().lower()
        if not recipient or "@" not in recipient:
            raise ValueError("原邮件没有可用的回复地址")
        original_subject = str(message.get("Subject") or "（无主题）").strip()
        subject = (
            original_subject
            if re.match(r"^re\s*:", original_subject, re.IGNORECASE)
            else f"Re: {original_subject}"
        )
        message_id = str(message.get("Message-ID") or "").strip()
        references = str(message.get("References") or "").strip()
        return _ReplyTarget(
            recipient=recipient,
            subject=subject[:998],
            message_id=message_id[:998],
            references=references[:3000],
        )
    finally:
        if client is not None:
            with contextlib.suppress(imaplib.IMAP4.error, OSError):
                client.logout()


def _send_qq_smtp(
    email: str,
    authorization_code: str,
    target: _ReplyTarget,
    text: str,
) -> None:
    message = EmailMessage(policy=policy.SMTP)
    message["From"] = email
    message["To"] = target.recipient
    message["Subject"] = target.subject
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain=email.rsplit("@", 1)[-1])
    if target.message_id:
        message["In-Reply-To"] = target.message_id
        message["References"] = " ".join(
            item for item in (target.references, target.message_id) if item
        )[:3998]
    message.set_content(text)
    with smtplib.SMTP_SSL(QQ_SMTP_HOST, QQ_SMTP_PORT, timeout=12) as client:
        client.login(email, authorization_code)
        client.send_message(message)


def _reply_to_qq_message(
    email: str,
    authorization_code: str,
    uid: int,
    text: str,
) -> _ReplyTarget:
    target = _qq_reply_target(email, authorization_code, uid)
    _send_qq_smtp(email, authorization_code, target, text)
    return target


def _require_local_connector(request: Request) -> None:
    if not settings.mailbox_local_connector_enabled:
        raise HTTPException(status_code=404, detail="本地邮箱连接器未启用")
    host = request.client.host if request.client else ""
    trusted = host == "testclient"
    with contextlib.suppress(ValueError):
        client_ip = ipaddress.ip_address(host)
        trusted = client_ip.is_loopback or any(
            client_ip in network
            for network in (
                ipaddress.ip_network("10.0.0.0/8"),
                ipaddress.ip_network("172.16.0.0/12"),
                ipaddress.ip_network("192.168.0.0/16"),
            )
        )
    if not trusted:
        raise HTTPException(status_code=403, detail="邮箱连接器仅允许本机访问")


@router.post("/qq/test", response_model=QQMailboxTestResponse)
async def test_qq_mailbox(
    payload: QQMailboxTestRequest, request: Request
) -> QQMailboxTestResponse:
    _require_local_connector(request)
    try:
        status = await asyncio.to_thread(
            _test_qq_imap,
            payload.email,
            payload.authorization_code.get_secret_value(),
        )
    except imaplib.IMAP4.error as exc:
        raise HTTPException(
            status_code=401,
            detail="QQ 邮箱拒绝登录。请确认已开启 IMAP/SMTP，并使用授权码而不是 QQ 密码。",
        ) from exc
    except (OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail="暂时无法连接 QQ 邮箱服务器，请检查网络后重试。",
        ) from exc
    return QQMailboxTestResponse(
        connected=True,
        server=f"{QQ_IMAP_HOST}:{QQ_IMAP_PORT}",
        messages=status.messages,
        unread=status.unread,
        last_uid=status.last_uid,
    )


@router.post("/qq/sync", response_model=QQMailboxSyncResponse)
async def sync_qq_mailbox(
    payload: QQMailboxSyncRequest, request: Request
) -> QQMailboxSyncResponse:
    _require_local_connector(request)
    try:
        result = await asyncio.to_thread(
            _sync_qq_imap,
            payload.email,
            payload.authorization_code.get_secret_value(),
            payload.after_uid,
            payload.limit,
        )
    except imaplib.IMAP4.error as exc:
        raise HTTPException(
            status_code=401,
            detail="QQ 邮箱授权已失效，请重新生成授权码后启动同步。",
        ) from exc
    except (OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail="暂时无法同步 QQ 邮箱，请检查网络后重试。",
        ) from exc
    target = (
        (payload.mailbox_id, payload.store_id)
        if payload.mailbox_id and payload.store_id
        else _single_cached_mailbox_target()
    )
    if target:
        _cache_synced_messages(result.messages, *target)
        _update_cached_mailbox_account(target[0], result.messages, result.last_uid)
        _persist_local_state()
    return result


@router.post("/qq/reply", response_model=QQMailboxReplyResponse)
async def reply_to_qq_mailbox_message(
    payload: QQMailboxReplyRequest,
    request: Request,
) -> QQMailboxReplyResponse:
    _require_local_connector(request)
    try:
        target = await asyncio.to_thread(
            _reply_to_qq_message,
            payload.email,
            payload.authorization_code.get_secret_value(),
            payload.uid,
            payload.text,
        )
    except (imaplib.IMAP4.error, smtplib.SMTPAuthenticationError) as exc:
        raise HTTPException(
            status_code=401,
            detail="QQ 邮箱授权已失效，请重新输入授权码后发送。",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (OSError, TimeoutError, smtplib.SMTPException) as exc:
        raise HTTPException(
            status_code=502,
            detail="暂时无法通过 QQ 邮箱发送回复，请稍后重试。",
        ) from exc
    return QQMailboxReplyResponse(
        sent=True,
        recipient=target.recipient,
        subject=target.subject,
    )


@router.post("/local/conversations", status_code=204)
async def import_local_conversations(
    payload: LocalMailboxImportRequest, request: Request
) -> None:
    _require_local_connector(request)
    _ensure_local_state_loaded()
    for message in payload.messages:
        _local_conversation_cache[message.id] = message
    _persist_local_state()


@router.get(
    "/local/conversations",
    response_model=list[LocalMailboxConversation],
    response_model_exclude_none=True,
)
async def list_local_conversations(request: Request) -> list[LocalMailboxConversation]:
    _require_local_connector(request)
    _ensure_local_state_loaded()
    return list(_local_conversation_cache.values())


@router.post("/local/accounts", status_code=204)
async def import_local_mailbox_accounts(
    payload: LocalMailboxAccountImportRequest, request: Request
) -> None:
    _require_local_connector(request)
    _ensure_local_state_loaded()
    for account in payload.accounts:
        existing = _local_mailbox_account_cache.get(account.id)
        _local_mailbox_account_cache[account.id] = account.model_copy(
            update={
                "messages": max(account.messages, existing.messages if existing else 0),
                "unread": max(account.unread, existing.unread if existing else 0),
                "last_uid": max(account.last_uid, existing.last_uid if existing else 0),
            }
        )
    _persist_local_state()


@router.get("/local/accounts", response_model=list[LocalMailboxAccount])
async def list_local_mailbox_accounts(request: Request) -> list[LocalMailboxAccount]:
    _require_local_connector(request)
    _ensure_local_state_loaded()
    return list(_local_mailbox_account_cache.values())


@router.get(
    "/storefront/conversations",
    response_model=list[StorefrontConversation],
)
async def list_storefront_conversations(request: Request) -> list[StorefrontConversation]:
    _require_local_connector(request)
    _ensure_local_state_loaded()
    return sorted(
        _storefront_conversation_cache.values(),
        key=lambda item: item.time,
        reverse=True,
    )


@router.patch(
    "/storefront/conversations/{conversation_id}/handoff",
    response_model=StorefrontConversation,
)
async def update_storefront_handoff(
    conversation_id: str,
    payload: StorefrontHandoffUpdate,
    request: Request,
) -> StorefrontConversation:
    _require_local_connector(request)
    conversation = _storefront_conversation(conversation_id)
    assigned_to = payload.assigned_to or conversation.assigned_to
    if payload.status == "claimed" and not assigned_to:
        assigned_to = "NOVA 客服"
    resolved = payload.status == "resolved"
    updated = conversation.model_copy(
        update={
            "handoff_status": payload.status,
            "assigned_to": assigned_to,
            "urgent": not resolved,
            "status": "resolved" if resolved else "open",
            "subject": (
                "已完成人工跟进的商城咨询"
                if resolved
                else "需要人工跟进的商城咨询"
            ),
        }
    )
    return _save_storefront_conversation(updated)


@router.post(
    "/storefront/conversations/{conversation_id}/replies",
    response_model=StorefrontConversation,
)
async def reply_to_storefront_conversation(
    conversation_id: str,
    payload: StorefrontHumanReplyRequest,
    request: Request,
) -> StorefrontConversation:
    _require_local_connector(request)
    conversation = _storefront_conversation(conversation_id)
    timestamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%H:%M")
    next_sequence = max((reply.sequence for reply in conversation.human_replies), default=0) + 1
    reply = StorefrontHumanReply(
        sequence=next_sequence,
        text=payload.text,
        time=timestamp,
        agent_name=payload.agent_name,
    )
    updated = conversation.model_copy(
        update={
            "messages": [
                *conversation.messages,
                StorefrontConversationTurn(role="agent", text=payload.text, time=timestamp),
            ][-80:],
            "human_replies": [*conversation.human_replies, reply][-80:],
            "handoff_status": "claimed",
            "assigned_to": payload.agent_name,
            "urgent": True,
            "status": "open",
            "subject": "人工客服接待中的商城咨询",
            "time": timestamp,
            "unread": False,
        }
    )
    return _save_storefront_conversation(updated)
