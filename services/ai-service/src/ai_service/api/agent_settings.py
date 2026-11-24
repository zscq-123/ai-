import contextlib
import hashlib
import hmac
import json
import re
import threading
import time
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from ai_service.api.mailboxes import _require_local_connector
from ai_service.config import settings
from ai_service.domain.models import Citation, Intent, SupportReply

router = APIRouter(prefix="/v1/agent", tags=["agent"])

Tone = Literal["亲切自然", "简洁专业"]
CostMode = Literal["economy", "balanced", "quality"]
SkillType = Literal["官方技能", "自定义技能"]


class AgentSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=500)
    type: SkillType
    tools: int = Field(default=0, ge=0, le=20)
    enabled: bool = True


class AgentConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft: bool = True
    handoff: bool = True
    translate: bool = True
    tone: Tone = "亲切自然"
    cost_mode: CostMode = "balanced"
    skills: list[AgentSkill]


class AgentSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft: bool | None = None
    handoff: bool | None = None
    translate: bool | None = None
    tone: Tone | None = None
    cost_mode: CostMode | None = None


class AgentSkillUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=80)
    text: str | None = Field(default=None, min_length=1, max_length=500)
    tools: int | None = Field(default=None, ge=0, le=20)
    enabled: bool | None = None


class AgentSkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="新建技能", min_length=1, max_length=80)
    text: str = Field(
        default="请补充触发条件、处理流程与可调用工具。",
        min_length=1,
        max_length=500,
    )
    tools: int = Field(default=0, ge=0, le=20)


class AgentDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel: Literal["chat", "email", "review"]
    customer_name: str = Field(default="客户", min_length=1, max_length=120)
    subject: str = Field(default="客户咨询", min_length=1, max_length=998)
    message: str = Field(min_length=1, max_length=4000)


class AgentDraftResponse(BaseModel):
    answer: str
    intent: str
    requires_human: bool
    handoff_recommended: bool
    language_assist_applied: bool
    skill_id: str | None
    tone: Tone
    cost_mode: CostMode


DEFAULT_SKILLS = (
    AgentSkill(
        id="order-query",
        title="订单查询",
        text="识别订单号并返回订单、物流与售后状态。",
        type="官方技能",
        tools=3,
    ),
    AgentSkill(
        id="product-recommendation",
        title="商品推荐",
        text="根据客户诉求检索商品知识并给出可解释建议。",
        type="官方技能",
        tools=2,
    ),
    AgentSkill(
        id="after-sales-intake",
        title="售后预审",
        text="收集图片、订单与问题描述，生成售后处理摘要。",
        type="自定义技能",
        tools=4,
    ),
    AgentSkill(
        id="coupon-guidance",
        title="优惠券说明",
        text="解释领取、使用门槛及有效期，不自动发放权益。",
        type="自定义技能",
        tools=1,
    ),
)

_state_lock = threading.RLock()


def _default_configuration() -> AgentConfiguration:
    return AgentConfiguration(skills=[skill.model_copy(deep=True) for skill in DEFAULT_SKILLS])


def _state_path() -> Path | None:
    configured = settings.mailbox_state_file.strip()
    if not configured:
        return None
    return Path(configured).expanduser().with_name("agent-settings.json")


def get_agent_configuration() -> AgentConfiguration:
    path = _state_path()
    if path is None:
        return _default_configuration()
    with _state_lock:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AgentConfiguration.model_validate(payload)
        except (FileNotFoundError, OSError, ValueError, TypeError):
            return _default_configuration()


def _persist(configuration: AgentConfiguration) -> None:
    path = _state_path()
    if path is None:
        return
    with _state_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                configuration.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        temporary.chmod(0o600)
        temporary.replace(path)


def resolve_skill(message: str, configuration: AgentConfiguration) -> AgentSkill | None:
    normalized = message.lower()
    rules = (
        ("coupon-guidance", ("优惠券", "优惠码", "折扣码", "coupon", "promo code")),
        (
            "after-sales-intake",
            ("退货", "退款", "换货", "售后", "破损", "return", "refund", "exchange"),
        ),
        ("order-query", ("订单", "物流", "快递", "发货", "到货", "order", "shipping", "delivery")),
        (
            "product-recommendation",
            (
                "商品",
                "产品",
                "推荐",
                "型号",
                "规格",
                "价格",
                "product",
                "recommend",
                "model",
                "price",
            ),
        ),
    )
    skill_id = next(
        (skill_id for skill_id, terms in rules if any(term in normalized for term in terms)),
        None,
    )
    return next((skill for skill in configuration.skills if skill.id == skill_id), None)


def _is_english(text: str) -> bool:
    return bool(re.search(r"[a-z]", text, re.IGNORECASE)) and not re.search(
        r"[\u4e00-\u9fff]", text
    )


def _apply_generation_policy(answer: str, configuration: AgentConfiguration) -> str:
    normalized = re.sub(r"[ \t]+", " ", answer).strip()
    if configuration.tone == "简洁专业":
        normalized = re.sub(
            r"^(?:好的|明白了|您好|你好)[，,。.!！\s]+",
            "",
            normalized,
        )
    limit = {"economy": 160, "balanced": 360, "quality": 800}[configuration.cost_mode]
    if len(normalized) <= limit:
        return normalized
    candidate = normalized[:limit]
    boundary = max(candidate.rfind(mark) for mark in ("。", "！", "？", ".", "!", "?"))
    if boundary >= limit // 2:
        return candidate[: boundary + 1]
    return candidate.rstrip("，,；; ") + "…"


async def _answer_with_integration(payload: AgentDraftRequest) -> SupportReply:
    """Reuse the production BUZUD answer path without loading a second retriever/model stack."""

    from ai_service.api.integrations import chat as integration_chat

    secret = settings.buzud_integration_secret
    if not secret:
        raise HTTPException(status_code=503, detail="BUZUD 客服回答服务尚未配置")
    raw = json.dumps(
        {
            "message": payload.message,
            "subject": None,
            "conversation_id": None,
            "evidence": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    timestamp = str(int(time.time()))
    canonical = b"buzud\n" + timestamp.encode() + b"\n" + raw
    signature = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
    delivered = False

    async def receive() -> dict[str, object]:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": raw, "more_body": False}

    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/v1/integrations/buzud/chat",
            "raw_path": b"/v1/integrations/buzud/chat",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 0),
            "server": ("127.0.0.1", 8000),
        },
        receive,
    )
    result = await integration_chat(
        "buzud",
        request,
        Response(),
        timestamp=timestamp,
        signature=signature,
    )
    citations = result.get("citations", [])
    citation_items = citations if isinstance(citations, list) else []
    return SupportReply(
        str(result["answer"]),
        Intent(str(result["intent"])),
        tuple(
            Citation(str(item["title"]), str(item["reference"]))
            for item in citation_items
            if isinstance(item, dict) and "title" in item and "reference" in item
        ),
        bool(result.get("requires_human", False)),
        bool(result.get("requires_confirmation", False)),
    )


@router.get("/settings", response_model=AgentConfiguration)
async def get_settings(request: Request) -> AgentConfiguration:
    _require_local_connector(request)
    return get_agent_configuration()


@router.put("/settings", response_model=AgentConfiguration)
async def update_settings(
    payload: AgentSettingsUpdate,
    request: Request,
) -> AgentConfiguration:
    _require_local_connector(request)
    configuration = get_agent_configuration().model_copy(
        update=payload.model_dump(exclude_none=True)
    )
    _persist(configuration)
    return configuration


@router.patch("/skills/{skill_id}", response_model=AgentSkill)
async def update_skill(
    skill_id: str,
    payload: AgentSkillUpdate,
    request: Request,
) -> AgentSkill:
    _require_local_connector(request)
    configuration = get_agent_configuration()
    index = next(
        (index for index, skill in enumerate(configuration.skills) if skill.id == skill_id),
        None,
    )
    if index is None:
        raise HTTPException(status_code=404, detail="Agent 技能不存在")
    updated = configuration.skills[index].model_copy(
        update=payload.model_dump(exclude_none=True)
    )
    skills = list(configuration.skills)
    skills[index] = updated
    _persist(configuration.model_copy(update={"skills": skills}))
    return updated


@router.post("/skills", response_model=AgentSkill, status_code=201)
async def create_skill(
    payload: AgentSkillCreate,
    request: Request,
) -> AgentSkill:
    _require_local_connector(request)
    configuration = get_agent_configuration()
    created = AgentSkill(
        id=f"custom-{uuid4().hex}",
        title=payload.title,
        text=payload.text,
        type="自定义技能",
        tools=payload.tools,
        enabled=False,
    )
    _persist(configuration.model_copy(update={"skills": [created, *configuration.skills]}))
    return created


@router.post("/draft", response_model=AgentDraftResponse)
async def generate_draft(
    payload: AgentDraftRequest,
    request: Request,
) -> AgentDraftResponse:
    _require_local_connector(request)
    configuration = get_agent_configuration()
    if not configuration.draft:
        raise HTTPException(status_code=409, detail="回复建议已在 Agent 设置中停用")
    skill = resolve_skill(payload.message, configuration)
    if skill is not None and not skill.enabled:
        raise HTTPException(status_code=409, detail=f"{skill.title}技能当前已停用")
    reply = await _answer_with_integration(payload)
    language_assist = configuration.translate and _is_english(payload.message)
    return AgentDraftResponse(
        answer=_apply_generation_policy(reply.answer, configuration),
        intent=reply.intent.value,
        requires_human=reply.requires_human,
        handoff_recommended=configuration.handoff and reply.requires_human,
        language_assist_applied=language_assist,
        skill_id=skill.id if skill else None,
        tone=configuration.tone,
        cost_mode=configuration.cost_mode,
    )


def persist_default_configuration() -> AgentConfiguration:
    configuration = get_agent_configuration()
    with contextlib.suppress(OSError):
        _persist(configuration)
    return configuration
