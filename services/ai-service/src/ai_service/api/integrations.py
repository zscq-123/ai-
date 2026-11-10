"""Signed, request-scoped integration for OMS and BUZUD backends.

Identity and evidence are supplied by the owning backend after authorization.
Foreign numeric identifiers never enter NOVA's UUID database or tool provider.
"""

import hashlib
import hmac
import json
import logging
import re
import time
from collections.abc import Iterable
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_service.application.chat_service import ChatService
from ai_service.application.integration_context import ConversationHint, IntegrationContextStore
from ai_service.application.support_agents import AgentScope, SupportAgentCoordinator
from ai_service.application.support_orchestrator import (
    IntentRoutingModule,
    SafetyBoundaryModule,
    SupportContext,
)
from ai_service.config import settings
from ai_service.domain.models import Citation, Intent, SupportReply
from ai_service.infrastructure.agent_model import JsonAgentModel
from ai_service.infrastructure.model_provider import build_model_provider

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])
model = build_model_provider(settings)
agent_model = JsonAgentModel(settings)
conversations = IntegrationContextStore()

TOPICS = {
    "contact": (
        "联系",
        "邮箱",
        "客服邮箱",
        "contact",
        "email",
        "e-mail",
        "customer support",
        "reach you",
    ),
    "stores": (
        "门店",
        "体验店",
        "地址",
        "营业",
        "store",
        "location",
        "opening hours",
        "address",
        "visit",
    ),
    "delivery": ("配送", "送货", "shipping", "delivery", "deliver", "ship overseas"),
    "warranty": ("保修", "质保", "warranty", "guarantee", "register my product"),
    "aftersales": ("维修", "换货", "退货", "售后", "repair", "broken", "return policy", "exchange"),
    "products": (
        "商品",
        "产品",
        "血压",
        "血糖",
        "手表",
        "价格",
        "售价",
        "多少钱",
        "库存",
        "有货",
        "现货",
        "型号",
        "规格",
        "推荐",
        "对比",
        "有没有",
        "有吗",
        "哪款",
        "仪器",
        "家用",
        "product",
        "products",
        "catalog",
        "price",
        "stock",
        "model",
        "spec",
        "recommend",
        "compare",
        "blood pressure",
        "watch",
    ),
}


def matches(text: str, terms: Iterable[str]) -> bool:
    return any(
        (
            bool(re.search(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", text))
            if term.isascii()
            else term in text
        )
        for term in terms
        if term
    )


GREETING_PREFIXES = (
    "good morning",
    "good afternoon",
    "good evening",
    "greetings",
    "ciallo",
    "ciao",
    "salve",
    "hola",
    "aloha",
    "hello",
    "howdy",
    "hey",
    "hi",
    "yo",
    "你好",
    "您好",
    "嗨",
    "哈喽",
    "哈啰",
    "在吗",
    "早上好",
    "中午好",
    "下午好",
    "晚上好",
)
GREETING_FILLERS = {
    "there",
    "everyone",
    "all",
    "again",
    "friend",
    "呀",
    "啊",
    "哦",
    "喔",
    "哟",
    "啦",
    "呢",
    "吗",
    "～",
    "~",
}
GREETING_FOLLOWUPS = {
    "how are you",
    "how are you doing",
    "how is it going",
    "how's it going",
    "what's up",
    "你好吗",
    "最近怎么样",
    "在干嘛",
}
BUSINESS_TERMS = (
    "商品",
    "产品",
    "价格",
    "多少钱",
    "售价",
    "库存",
    "有货",
    "现货",
    "购买",
    "购买",
    "买",
    "订单",
    "物流",
    "快递",
    "发货",
    "退款",
    "退货",
    "换货",
    "售后",
    "支付",
    "付款",
    "客服",
    "联系",
    "邮箱",
    "门店",
    "配送",
    "保修",
    "维修",
    "product",
    "price",
    "stock",
    "order",
    "refund",
    "return",
    "shipping",
    "payment",
    "support",
    "contact",
    "email",
    "warranty",
    "delivery",
)
COMMERCE_INTENT_TERMS = (
    "多少钱",
    "价格",
    "售价",
    "库存",
    "有货",
    "现货",
    "购买",
    "买",
    "下单",
    "推荐",
    "哪款",
    "哪个好",
    "型号",
    "规格",
    "对比",
    "优惠",
    "券",
    "订单",
    "物流",
    "快递",
    "发货",
    "退款",
    "退货",
    "换货",
    "售后",
    "支付",
    "付款",
    "客服",
    "门店",
    "配送",
    "保修",
    "维修",
    "price",
    "cost",
    "stock",
    "buy",
    "purchase",
    "recommend",
    "model",
    "spec",
    "compare",
    "order",
    "refund",
    "return",
    "shipping",
    "payment",
    "support",
    "warranty",
    "repair",
)
GENERAL_KNOWLEDGE_TERMS = (
    "是什么",
    "什么是",
    "为什么",
    "怎么回事",
    "什么原因",
    "有什么危害",
    "有什么影响",
    "怎么预防",
    "如何预防",
    "怎么调理",
    "如何调理",
    "怎么办",
    "怎么治疗",
    "如何治疗",
    "吃什么药",
    "症状",
    "病因",
    "原理",
    "what is",
    "what are",
    "why",
    "how does",
    "how do",
    "explain",
    "meaning of",
    "tell me about",
    "what causes",
)
DEICTIC_TERMS = (
    "这个",
    "这款",
    "那款",
    "它",
    "该商品",
    "此商品",
    "this product",
    "this item",
    "this one",
)


def is_greeting_only(text: str) -> bool:
    value = text.strip().lower()
    if not value:
        return False
    if value in GREETING_FOLLOWUPS:
        return True
    for prefix in sorted(GREETING_PREFIXES, key=len, reverse=True):
        if not value.startswith(prefix):
            continue
        rest = value[len(prefix) :].strip(" \t\r\n，,！!。.~～-—:：、")
        if not rest:
            return True
        if rest in GREETING_FILLERS or rest in GREETING_FOLLOWUPS:
            return True
        # Ciallo～(∠・ω< )⌒★ and similar kaomoji contain no letters, digits or CJK.
        if not re.search(r"[a-z0-9\u4e00-\u9fff]", rest):
            return True
    return False


def social_kind(text: str) -> str | None:
    value = text.strip().lower()
    if is_greeting_only(value):
        return "greeting"
    if (
        value.startswith(("谢谢", "多谢"))
        or value
        in {
            "thanks",
            "thank you",
            "thx",
            "ty",
        }
        or value.startswith(("thanks ", "thank you "))
    ):
        return "thanks"
    if value.startswith(("再见", "拜拜", "bye", "goodbye", "see you")):
        return "goodbye"
    if value.startswith(("你是谁", "你是什么", "who are you", "what are you")):
        return "identity"
    if value in {
        "你能做什么",
        "你能帮我做什么",
        "你可以做什么",
        "what can you do",
        "what can you help with",
        "what do you do",
    }:
        return "capability"
    return None


def social_reply(source: str, text: str, english: bool, kind: str) -> SupportReply:
    ciallo = "ciallo" in text.lower() or "ciao" in text.lower()
    if kind == "thanks":
        message = (
            "You're welcome! Anything else I can help with?"
            if english
            else "不客气！还有其他想了解的吗？"
        )
    elif kind == "goodbye":
        message = "Goodbye! Have a great day." if english else "再见，祝你购物愉快！"
    elif kind == "identity":
        message = (
            "I'm the CHUNG YIP AI support assistant. I can look up product prices,"
            " specifications, availability, orders and after-sales, and I'm happy to chat briefly."
            if english and source == "buzud"
            else "I'm the support assistant. I can help with order status and amount,"
            " payment and after-sales, and I'm happy to chat briefly."
            if english
            else "我是 CHUNG YIP 的 AI 客服助手，可以帮你查商品价格、规格、库存、订单和售后；"
            "也可以简单聊两句。"
            if source == "buzud"
            else "我是客服助手，可以帮你查订单状态和金额、支付和售后；也可以简单聊两句。"
        )
    elif kind == "capability":
        message = (
            "I can help with product prices, specifications, availability, orders and"
            " after-sales. Tell me a product name, model or order number."
            if english and source == "buzud"
            else "I can help check order status and amount, payment and after-sales."
            " Tell me an order number."
            if english
            else "我可以帮你查商品价格、规格、库存、订单和售后。告诉我商品名、型号或订单号即可。"
            if source == "buzud"
            else "我可以帮你查订单状态和金额、支付和售后。告诉我订单号即可。"
        )
    else:
        opener = "Ciallo～ " if ciallo else ("Hello! " if english else "你好！")
        message = (
            opener + "I'm the CHUNG YIP support assistant. I can help with product prices,"
            " specifications, availability, orders and after-sales. What would you like to know?"
            if english and source == "buzud"
            else opener + "I'm the support assistant. I can help with order status and amount,"
            " payment and after-sales. What would you like to check?"
            if english
            else opener + "我是 CHUNG YIP 客服助手，可以帮你查商品价格、规格、库存、订单和售后。"
            "你想了解什么？"
            if source == "buzud"
            else opener + "我是客服助手，可以帮你查订单状态和金额、支付和售后。你想了解什么？"
        )
    return SupportReply(message, Intent.FAQ)


def social_scope_reply(source: str, english: bool) -> str:
    if english and source == "buzud":
        return (
            "I'm the CHUNG YIP AI support assistant. I can help with products, prices,"
            " availability, orders and after-sales, and I'm happy to chat briefly."
            " What would you like to know?"
        )
    if english:
        return (
            "I'm the support assistant. I can help with order status, payment and after-sales."
            " What would you like to check?"
        )
    if source == "buzud":
        return (
            "我是 CHUNG YIP 的 AI 客服助手，可以帮你查商品、价格、库存、订单和售后，"
            "也可以简单聊两句。你想了解什么？"
        )
    return "我是客服助手，可以帮你查订单状态、支付和售后。你想了解什么？"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=4000)
    title: str = Field(min_length=1, max_length=120)
    reference: str = Field(min_length=1, max_length=240)
    keywords: list[str] = Field(default_factory=list, max_length=32)


class IntegrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)
    subject: str | None = Field(default=None, min_length=1, max_length=120)
    conversation_id: UUID | None = None
    evidence: list[Evidence] = Field(default_factory=list, max_length=24)


class RequestEvidence:
    def __init__(self, items: list[Evidence]) -> None:
        self.items = [(item.content, Citation(item.title, item.reference)) for item in items]

    async def search(self, query: str, **kwargs: object) -> list[tuple[str, Citation]]:
        return []  # Never use NOVA marketplace policies for another business.

    async def lookup(self, message: str, **kwargs: object) -> list[tuple[str, Citation]]:
        return self.items


def reply_json(reply: SupportReply) -> dict[str, object]:
    return {
        "answer": reply.answer,
        "intent": reply.intent.value,
        "citations": [{"title": c.title, "reference": c.reference} for c in reply.citations],
        "requires_human": reply.requires_human,
        "requires_confirmation": reply.requires_confirmation,
    }


def order_reply(
    source: str, message: str, items: list[Evidence], english: bool
) -> SupportReply | None:
    """Only render facts supplied by this request's authenticated owning backend."""
    for item in items:
        fact = re.fullmatch(
            r"订单 ([A-Za-z0-9_-]{1,80}) 当前状态："
            r"(待付款|待支付|已支付|已审核|待发货|已发货|待收货|已签收|已完成|已取消|售后处理中|退款中)"
            r"；订单金额 ([0-9]+(?:\.[0-9]+)?) ([A-Z]{3})。.*",
            item.content,
        )
        if not fact or item.reference != f"order://{source}/{fact.group(1)}":
            continue
        order_no, state, amount, currency = fact.groups()
        en_states = {
            "已取消": "cancelled",
            "待付款": "awaiting payment",
            "待支付": "awaiting payment",
            "已支付": "paid",
            "已审核": "reviewed",
            "待发货": "awaiting dispatch",
            "已发货": "shipped",
            "待收货": "awaiting delivery",
            "已签收": "delivered",
            "已完成": "completed",
            "售后处理中": "after-sales processing",
            "退款中": "refund processing",
        }
        summary = (
            f"Order {order_no} is {en_states[state]}; the amount is {amount} {currency}."
            if english
            else f"订单 {order_no} 当前为{state}，订单金额 {amount} {currency}。"
        )
        payment = matches(message, ("付款", "支付", "pay", "payment", "charged"))
        shipping = matches(
            message,
            (
                "物流",
                "快递",
                "到哪里",
                "送到",
                "送达",
                "运单",
                "tracking",
                "arrive",
                "delivery",
                "shipment",
            ),
        )
        refund = matches(message, ("退款", "到账", "refund"))
        basic = matches(message, ("状态", "金额", "多少钱", "status", "amount", "total"))
        if not any((payment, shipping, refund, basic)):
            return None
        if payment:
            if state == "已取消":
                summary += (
                    " You do not need to pay this cancelled order."
                    " Cancellation does not confirm a refund."
                    if english
                    else "这笔已取消订单不需要继续付款；取消状态不代表退款已经到账。"
                )
            elif state in ("待付款", "待支付"):
                summary += (
                    " Check the payment page before paying; do not pay twice if already charged."
                    if english
                    else "如需继续购买，请到订单支付页核对；如果已经扣款，请勿重复支付。"
                )
            else:
                summary += (
                    " No separate payment transaction record was supplied;"
                    " do not make a duplicate payment."
                    if english
                    else "本次没有独立的支付流水，不能确认具体扣款明细；请勿重复付款。"
                )
        if refund:
            summary += (
                " No refund receipt was supplied, so I cannot confirm the funds have arrived."
                if english
                else "本次没有退款到账记录，无法确认款项已经退回，请核对原支付渠道记录。"
            )
        if shipping:
            if state == "已取消":
                summary += (
                    " The order is cancelled, so I cannot promise a delivery."
                    if english
                    else "这笔订单已经取消，不能承诺继续配送或明天送达。"
                )
            summary += (
                " No tracking events were supplied. Check Orders / Logistics in OMS."
                if english and source == "oms"
                else " No tracking events were supplied."
                " Check the logistics section of your order details."
                if english
                else "本次没有运单轨迹，无法确认包裹位置或送达时间；"
                "可在 OMS「订单管理／物流轨迹」核对。"
                if source == "oms"
                else "本次没有运单轨迹，无法确认包裹位置或送达时间；可在订单详情的物流信息中核对。"
            )
        return SupportReply(summary, Intent.ORDER, (Citation(item.title, item.reference),))
    return None


PRODUCT_PRICE_TERMS = ("多少钱", "价格", "售价", "价钱", "price", "cost", "how much")
PRODUCT_STOCK_TERMS = ("库存", "有货", "现货", "能买", "能下单", "stock", "available", "in stock")
PRODUCT_COMPARE_TERMS = (
    "对比",
    "比较",
    "区别",
    "哪个",
    "compare",
    "difference",
    "versus",
    " vs ",
)


def product_reply(
    source: str, message: str, items: list[Evidence], english: bool
) -> SupportReply | None:
    """Render exact price/stock facts for a single signed catalogue item.

    The owning backend selects catalogue evidence from its complete product
    catalogue. When the question clearly targets one product, a deterministic
    answer avoids model paraphrasing of prices and availability.
    """

    catalogue = [
        item
        for item in items
        if item.reference.startswith(f"catalog://{source}/")
        and item.reference != f"catalog://{source}/overview"
    ]
    if len(catalogue) != 1:
        return None
    if not matches(message, (*PRODUCT_PRICE_TERMS, *PRODUCT_STOCK_TERMS)):
        return None
    if matches(message, PRODUCT_COMPARE_TERMS):
        return None
    item = catalogue[0]
    name = re.search(r"商品：([^\n]+)", item.content)
    price = re.search(r"售价：SGD ([0-9]+(?:\.[0-9]+)?)", item.content)
    stock = re.search(r"库存：[^\n]*?可售库存 ([0-9]+) 件", item.content)
    slug = re.search(r"商品页：(/zh/p/[^\s]+)", item.content)
    if not (name and price):
        return None
    product_name = name.group(1).strip()
    if english:
        answer = f"{product_name} is priced at SGD {price.group(1)}."
    else:
        answer = f"商品「{product_name}」当前售价 SGD {price.group(1)}。"
    if matches(message, PRODUCT_STOCK_TERMS):
        if stock:
            answer += (
                f" {stock.group(1)} units are currently available."
                " Availability can still change at checkout."
                if english
                else f" 当前可售库存 {stock.group(1)} 件，最终能否购买以下单结算结果为准。"
            )
        else:
            answer += (
                " Live stock is not available in this chat;"
                " please confirm on the product or checkout page."
                if english
                else " 实时库存未接入，能否购买请以商品页和结算结果为准。"
            )
    if slug:
        answer += f" Product page: {slug.group(1)}" if english else f" 商品页：{slug.group(1)}"
    return SupportReply(answer, Intent.PRODUCT, (Citation(item.title, item.reference),))


@router.post("/{source}/chat")
async def chat(
    source: Literal["oms", "buzud"],
    request: Request,
    response: Response,
    timestamp: Annotated[str, Header(alias="X-Support-Timestamp")] = "",
    signature: Annotated[str, Header(alias="X-Support-Signature")] = "",
) -> dict[str, object]:
    secret = (
        settings.oms_integration_secret if source == "oms" else settings.buzud_integration_secret
    )
    if not secret:
        raise HTTPException(503, "Support integration is not configured")
    try:
        if abs(time.time() - int(timestamp)) > 120:
            raise ValueError("expired")
    except ValueError as exc:
        raise HTTPException(401, "Invalid support timestamp") from exc
    raw = await request.body()
    if len(raw) > 64000:
        raise HTTPException(413, "Support payload too large")
    canonical = source.encode() + b"\n" + timestamp.encode() + b"\n" + raw
    expected = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid support signature")
    try:
        body = IntegrationRequest.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(422, "Invalid support request") from exc
    if not body.message.strip():
        raise HTTPException(422, "Message is required")
    conversation = str(body.conversation_id) if body.conversation_id else None
    previous = conversations.get(source, body.subject, conversation)
    question = body.message.strip()
    repeat = re.fullmatch(
        r"(?:(?:请|麻烦)?(?:把)?(?:刚才|上面|上一条|刚刚)(?:那条|的回答|那句|的内容|那个答案)?"
        r"(?:再)?(?:发|说|重复)(?:一遍|一次|一下)?[。？！!?]*|(?:请)?再说(?:一遍|一次)[。？！!?]*|"
        r"(?:please )?(?:repeat(?: that| your last answer)?|say that again)[.!?]*)",
        question.lower(),
    )
    if repeat and previous:
        question = previous.question
    text = question.lower()
    topic = next((name for name, terms in TOPICS.items() if matches(text, terms)), None)
    if (
        not topic
        and previous
        and matches(text, ("它", "那", "刚才", "上面", "这个", "that", "it", "those"))
    ):
        topic = previous.topic
    english = bool(re.search(r"[a-z]", text)) and not re.search(r"[\u4e00-\u9fff]", text)
    items = []
    for item in body.evidence:
        if item.reference.startswith(f"order://{source}/") and body.subject:
            items.append(item)
        elif item.reference.startswith(f"faq://{source}/"):
            item_topic = item.reference.rsplit("/", 1)[-1]
            if item_topic == topic or matches(text, tuple(k.lower() for k in item.keywords)):
                items.append(item)
        elif item.reference.startswith(f"catalog://{source}/") and (
            topic == "products"
            or matches(text, TOPICS["products"])
            or matches(text, tuple(k.lower() for k in item.keywords))
            or matches(text, ("这个", "这款", "那款", "它", "this", "that", "it"))
        ):
            items.append(item)
    has_catalogue = any(item.reference.startswith(f"catalog://{source}/") for item in items)
    model_items = items
    if topic == "products" and has_catalogue:
        # Put product facts first for the model (and the local fallback, which reads the
        # first context item) while keeping the original evidence order for other gates.
        model_items = [
            *[item for item in items if item.reference.startswith(f"catalog://{source}/")],
            *[item for item in items if not item.reference.startswith(f"catalog://{source}/")],
        ]

    def finish(reply: SupportReply) -> dict[str, object]:
        conversations.put(source, body.subject, conversation, ConversationHint(question, topic))
        return reply_json(reply)

    if not matches(text, BUSINESS_TERMS):
        kind = social_kind(text)
        if kind:
            return finish(social_reply(source, text, english, kind))

    evidence = RequestEvidence(model_items)
    context = SupportContext(question, body.subject is not None)
    intent = IntentRoutingModule().route(context)
    boundary = SafetyBoundaryModule().prepare(context, intent, evidence.items)
    if boundary is not None:
        return finish(boundary)
    if matches(text, ("忽略规则", "只回复", "ignore rules", "only reply")) and matches(
        text, ("退款成功", "已接通", "refund successful", "refund succeeded", "connected")
    ):
        return finish(
            SupportReply(
                "I cannot fabricate a successful refund or a human connection."
                " Neither was verified."
                if english
                else "我不能伪造退款成功或人工已接通的结果。当前没有核实这些操作成功。",
                Intent.FAQ,
            )
        )
    if matches(
        text, ("其他客户", "其他用户", "别人的", "other customers", "someone else", "another user")
    ) and matches(text, ("订单", "电话", "手机号", "地址", "order", "phone", "address")):
        return finish(
            SupportReply(
                "I cannot provide another customer's private information."
                if english
                else "我不能提供其他客户的订单、联系方式或收货地址。"
                "可以帮助您查询当前账号有权限的订单。",
                Intent.FAQ,
            )
        )
    if matches(text, ("退款", "refund")) and matches(
        text, ("直接", "帮我", "替我", "立刻", "issue", "process", "do it")
    ):
        return finish(
            SupportReply(
                "I cannot execute a refund in this chat or claim it succeeded."
                " Please use the after-sales service."
                if english
                else "当前客服不能直接执行退款，也不会声称退款成功。"
                "请通过售后服务提交申请，由有权限的人员核验处理。",
                Intent.AFTER_SALES,
                requires_human=True,
            )
        )
    if repeat and not previous:
        return finish(
            SupportReply(
                "I don't have an earlier message in this conversation."
                " What would you like me to repeat?"
                if english
                else "当前会话里还没有可重复的上轮问题，请告诉我需要查询什么。",
                Intent.FAQ,
            )
        )
    greeting = re.fullmatch(
        r"(?:你好|您好|嗨|在吗|hello|hi|hey)[，,！!。 .]*"
        r"(?:(?:你能|可以|能)(?:帮我)?(?:做什么|查什么|提供什么帮助)[？?。!]*)?"
        r"|(?:what can you (?:do|help with)|你能帮我做什么)[？?。!]*",
        text,
    )
    if greeting:
        answer = (
            "Hello! I can check the status and amount of an order you can access in OMS."
            " Select an order to get started."
            if english and source == "oms"
            else "Hello! I can help with product price, specifications, usage and availability,"
            " plus contact details, delivery and warranty questions."
            " Select an order after signing in to check its status and amount."
            if english
            else "您好！我可以帮您查询已关联订单的状态和金额，"
            "并说明退款、物流信息是否已核实。填写订单号后即可提问。"
            if source == "oms"
            else "您好！我可以回答商品价格、规格、用法和库存，"
            "以及联系方式、门店、配送、维修和保修问题。"
            "登录并填写订单号后，还能查询订单状态和金额。"
        )
        return finish(SupportReply(answer, Intent.FAQ))
    if matches(
        text, ("转人工", "找真人", "人工客服", "live agent", "human agent", "speak to a human")
    ):
        return finish(
            SupportReply(
                "Use the customer service ticket link below to contact our team."
                " No human agent has joined this chat yet."
                if english and source == "buzud"
                else "请点击下方「联系人工客服」提交客服工单，说明需要处理的问题。"
                "当前对话尚未接通真人。"
                if source == "buzud"
                else "请在 OMS「售后服务」中处理售后申请，或联系负责该订单的客服人员。"
                "当前对话尚未接通真人。",
                Intent.HUMAN_HANDOFF,
                requires_human=True,
            )
        )
    # General knowledge / small talk with no commerce signal: answer like a general assistant,
    # while the system prompt forbids inventing store facts or giving medical diagnoses.
    order_evidence = any(item.reference.startswith(f"order://{source}/") for item in items)
    contact_evidence = any(
        item.reference.startswith(f"faq://{source}/")
        and item.reference.rsplit("/", 1)[-1]
        in {"contact", "stores", "delivery", "warranty", "aftersales"}
        for item in items
    )
    general_definition = (
        matches(text, GENERAL_KNOWLEDGE_TERMS)
        and not matches(text, COMMERCE_INTENT_TERMS)
        and not matches(text, DEICTIC_TERMS)
        and not order_evidence
        and not contact_evidence
    )
    general_chat = not order_evidence and (
        (not matches(text, BUSINESS_TERMS) and not has_catalogue and not items and topic is None)
        or general_definition
    )
    if general_chat:
        answer_general = getattr(model, "answer_general", None)
        if answer_general is not None:
            try:
                general_answer = (await answer_general(question=question, english=english)).strip()
            except Exception:
                general_answer = ""
            if general_answer:
                return finish(SupportReply(general_answer, Intent.FAQ))
    # Existing permission/safety and unsupported-action gates remain outside model control.
    # Specialists get only this request's signed sources, including multiple FAQ topics
    # for compound questions; the legacy single-topic filter remains for the old path.
    unsupported_catalog = source == "buzud" and (
        matches(text, ("优惠", "优惠券", "折扣", "coupon", "discount", "promo code"))
        or (
            topic == "products"
            and not has_catalogue
            and matches(text, ("多少钱", "价格", "库存", "有货", "price", "stock", "cost"))
        )
    )
    if (
        source == "buzud"
        and topic == "products"
        and not matches(text, ("订单", "这单", "这笔", "order"))
        and not unsupported_catalog
        and (product := product_reply(source, text, items, english))
    ):
        return finish(product)
    # Product catalogue answers are evidence-grounded and already handled by the normal model
    # path. The multi-agent planner adds latency and, on a JSON/tool failure, falls back to a
    # raw product record instead of a recommendation. Keep agents for order/after-sales/FAQ.
    product_catalogue_query = source == "buzud" and topic == "products" and has_catalogue
    if (
        settings.integration_agents_enabled
        and not unsupported_catalog
        and not product_catalogue_query
    ):
        scope = AgentScope.from_items(
            source=source,
            authenticated=body.subject is not None,
            question=question,
            english=english,
            topic=topic,
            items=items,
        )
        coordinator = SupportAgentCoordinator(agent_model, settings)
        reply, trace = await coordinator.run(
            scope, canonical_order=lambda query: order_reply(source, query, items, english)
        )
        response.headers["X-Support-Agent-Run"] = trace.run_id
        response.headers["X-Support-Agent-Roles"] = ",".join(t.agent for t in trace.tasks)
        response.headers["X-Support-Agent-Degraded"] = str(trace.fallback_used).lower()
        logging.getLogger("uvicorn.error").info(
            "support_agent_run %s", json.dumps(trace.public_record(), ensure_ascii=False)
        )
        return finish(reply)
    order_query = topic is None or matches(text, ("订单", "这笔", "这单", "order"))
    if body.subject and order_query and (order := order_reply(source, text, items, english)):
        return finish(order)
    if source == "buzud" and matches(
        text, ("优惠", "优惠券", "折扣", "coupon", "discount", "promo code")
    ):
        return finish(
            SupportReply(
                "See the coupon centre at /zh/coupon/ or your coupons at /zh/profile/coupons/."
                " Availability and eligibility are shown there;"
                " I cannot issue a code or promise a 50% discount here."
                if english
                else "可前往「领券中心」/zh/coupon/ 查看当前活动，"
                "登录后在「我的优惠券」/zh/profile/coupons/ 查看已领取的券。"
                "可用优惠和门槛以页面及结算结果为准；我不能直接发放优惠码或承诺五折。",
                Intent.FAQ,
            )
        )
    if (
        source == "buzud"
        and topic == "products"
        and not has_catalogue
        and matches(text, ("多少钱", "价格", "库存", "有货", "price", "stock", "cost"))
    ):
        return finish(
            SupportReply(
                "Please open the product catalogue at /zh/all-products/ and choose the exact model"
                " to view its current price. Stock availability must be confirmed on the product"
                " or checkout page; this chat cannot verify live inventory."
                if english
                else "请在「所有商品」/zh/all-products/ 选择具体型号查看当前售价。"
                "不同型号价格不同，库存和能否购买需以商品页及结算结果为准；"
                "当前客服尚不能核验实时库存。",
                Intent.PRODUCT,
            )
        )
    # Read the email from current signed knowledge, never embed merchant facts in code.
    if english and topic == "contact" and not matches(text, ("phone", "telephone", "hours")):
        for item in items:
            email = re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", item.content)
            if email:
                return finish(
                    SupportReply(
                        f"You can contact customer support by email at {email.group()}.",
                        Intent.FAQ,
                        (Citation(item.title, item.reference),),
                    )
                )
    # Preserve all policy conditions rather than allowing paraphrasing to drop eligibility.
    if not english and topic == "aftersales":
        for item in items:
            if item.reference == f"faq://{source}/aftersales":
                return finish(
                    SupportReply(
                        "当前售后政策：" + item.content,
                        Intent.AFTER_SALES,
                        (Citation(item.title, item.reference),),
                    )
                )
    service = ChatService(evidence, model, evidence)
    model_question = question
    if topic and previous and previous.topic == topic:
        model_question += f"\n（当前咨询话题：{topic}；仅使用本次提供的最新证据。）"
    if has_catalogue:
        model_question += (
            "\nAnswer product price, specification, usage and stock only from the catalogue"
            " evidence in this request. Do not invent missing fields. Use the exact available"
            " quantity when supplied; otherwise state that live stock must be confirmed on the"
            " product or checkout page. Keep product-page links and compare only fields present"
            " in the evidence. For each recommended product, include its /zh/p/ product-page link."
            if english
            else "\n仅使用本次提供的商品资料回答价格、规格、用法和可售数量；"
            "资料中没有的字段不要补全。"
            "可售数量只使用资料中明确写出的数字，未提供时说明以商品页和结算结果为准。"
            "每推荐一个商品，在回答中附上该商品的商品页链接（/zh/p/.../）；"
            "多商品对比时只比较资料中列出的字段。"
        )
    if english:
        model_question += "\nPlease answer in English."
    reply = await service.answer(
        model_question,
        authenticated=body.subject is not None,
        customer_id=uuid5(NAMESPACE_URL, f"{source}:{body.subject}") if body.subject else None,
    )
    answer = reply.answer
    if reply.intent == Intent.HUMAN_HANDOFF:
        answer = (
            "请点击下方「联系人工客服」提交工单，当前对话尚未接通真人。"
            if source == "buzud"
            else "请在 OMS「售后服务」中联系负责该订单的客服人员，当前对话尚未接通真人。"
        )
    elif "需要按本轮有效意图重新查询最新工具证据" in answer:
        if not matches(text, BUSINESS_TERMS):
            answer = social_scope_reply(source, english)
        else:
            answer = (
                "Please sign in and select an order before asking about your order."
                if english and "登录" in answer
                else "I cannot confirm that from the available information."
                " Please provide the specific product or select an order."
                if english
                else "请先登录，再填写需要查询的订单号。"
                if "登录" in answer
                else "目前没有查到可核实的信息。请补充具体商品、问题或关联订单号。"
            )
    return finish(
        SupportReply(
            answer, reply.intent, reply.citations, reply.requires_human, reply.requires_confirmation
        )
    )
