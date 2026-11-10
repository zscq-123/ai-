import json
import logging
import re
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel

from ai_service.config import Settings
from ai_service.domain.models import Intent, ReplyGuidance
from ai_service.domain.ports import ModelProvider
from ai_service.prompts import compose_prompt
from ai_service.prompts.library import S11_INSUFFICIENT, ScriptCard, select_card

GENERAL_SYSTEM_PROMPT = """You are a friendly general-purpose AI assistant embedded in the \
CHUNG YIP health products store's customer service.

Answer the user's question accurately and concisely in the user's language. You may use general
knowledge, but follow these boundaries:
- Never claim to have looked up the store's products, prices, stock, orders, payments, logistics,
  refunds or after-sales. For a specific store product or order, ask for details instead of
  inventing facts.
- Do not diagnose, prescribe, or give personalized medical treatment advice. General health
  information is fine; for personal symptoms, advise consulting a doctor or pharmacist.
- Never claim to execute refunds, cancellations, address changes, shipments or a human handoff.
- If the question needs live data (weather, news, prices), say you cannot access it.
- Refuse illegal, harmful, or privacy-invasive requests.
- Keep the answer concise (under about 180 words) and friendly. You may briefly mention that you
  can also help with store products."""


def _general_fallback(english: bool) -> str:
    return (
        "I can't answer general questions right now, but I can help with product prices,"
        " availability, orders and after-sales."
        if english
        else "我暂时无法回答通用问题，但可以帮你查商品、价格、库存、订单和售后。"
    )


class DeepSeekMessage(BaseModel):
    content: str


class DeepSeekChoice(BaseModel):
    message: DeepSeekMessage


class DeepSeekResponse(BaseModel):
    choices: list[DeepSeekChoice]


def selected_card(guidance: ReplyGuidance | None, question: str) -> ScriptCard:
    intent = guidance.intent if guidance is not None else Intent.FAQ
    return select_card(intent, question)


def _extract_delta(payload: str) -> str:
    try:
        chunk: object = json.loads(payload)
    except ValueError:
        return ""
    if not isinstance(chunk, dict):
        return ""
    choices = chunk.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    delta = first.get("delta")
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    return content if isinstance(content, str) else ""


def _product_fallback_summary(question: str, context: list[str]) -> str | None:
    """Compact list for degraded mode when several product facts were supplied."""

    products = [item for item in context if item.lstrip().startswith("商品：")]
    if len(products) < 2:
        return None
    english = bool(re.search(r"[a-z]", question)) and not re.search(r"[\u4e00-\u9fff]", question)
    lines: list[str] = []
    for content in products[:3]:
        name = re.search(r"商品：([^\n]+)", content)
        price = re.search(r"售价：SGD ([0-9]+(?:\.[0-9]+)?)", content)
        slug = re.search(r"商品页：(/zh/p/[^\s]+)", content)
        if not (name and price):
            continue
        line = f"- {name.group(1).strip()} — SGD {price.group(1)}"
        if slug:
            line += f"：{slug.group(1)}"
        lines.append(line)
    if not lines:
        return None
    header = "Here are the matching products:" if english else "为您找到以下商品："
    footer = (
        " Tell me your budget or preferred feature and I can narrow it down."
        if english
        else "如需按预算或功能进一步筛选，请告诉我。"
    )
    return header + "\n" + "\n".join(lines) + "\n" + footer


class GroundedLocalModel:
    """模型不可用或未配置时的降级回答，仍然遵守话术的边界。"""

    async def answer(
        self,
        *,
        question: str,
        context: list[str],
        guidance: ReplyGuidance | None = None,
    ) -> str:
        card = selected_card(guidance, question)
        if context:
            summary = _product_fallback_summary(question, context)
            if summary:
                return summary
            content = context[0].strip()
            if content:
                content = re.sub(r"^可用知识：\s*(?:-\s*)?", "", content)
                positive_signed = bool(
                    re.search(r"已于[^。]*签收", content) or "签收成功" in content
                )
                negative_signed = any(
                    signal in content for signal in ("未签收", "尚未签收", "运输中")
                )
                if (
                    "签收" in question
                    and positive_signed
                    and not negative_signed
                    and "已签收" not in content
                ):
                    content = content.rstrip("。") + "，当前状态为已签收。"
                if content.endswith(("。", "！", "？", ".", "!", "?")):
                    return content
                return content + "。"
        if not card.needs_knowledge:
            return next(
                (answer for example, answer in card.examples if example == question.strip()),
                card.template,
            )
        if not context:
            return S11_INSUFFICIENT.template
        return S11_INSUFFICIENT.template

    async def answer_general(self, *, question: str, english: bool = False) -> str:
        del question
        return _general_fallback(english)

    async def stream_answer(
        self,
        *,
        question: str,
        context: list[str],
        guidance: ReplyGuidance | None = None,
    ) -> AsyncIterator[str]:
        yield await self.answer(question=question, context=context, guidance=guidance)


class DeepSeekModel:
    """OpenAI-compatible chat provider used by DeepSeek and local MLX servers."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        temperature: float = 0.2,
        thinking: bool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        fallback: ModelProvider | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._thinking = thinking
        self._transport = transport
        self._fallback = fallback or GroundedLocalModel()

    async def answer(
        self,
        *,
        question: str,
        context: list[str],
        guidance: ReplyGuidance | None = None,
    ) -> str:
        if not context and selected_card(guidance, question).needs_knowledge:
            return await self._fallback.answer(
                question=question, context=context, guidance=guidance
            )

        messages = self._messages(question=question, context=context, guidance=guidance)
        body: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "temperature": self._temperature,
            "max_tokens": 800,
        }
        if self._thinking is not None:
            body["thinking"] = {"type": "enabled" if self._thinking else "disabled"}

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=body,
                )
                response.raise_for_status()
                payload = DeepSeekResponse.model_validate(response.json())
                if payload.choices and payload.choices[0].message.content.strip():
                    return payload.choices[0].message.content.strip()
                logging.getLogger(__name__).warning("model_empty_content")
        except (httpx.HTTPError, ValueError) as exc:
            logging.getLogger(__name__).warning("model_call_failed %s", type(exc).__name__)
        return await self._fallback.answer(question=question, context=context, guidance=guidance)

    async def answer_general(self, *, question: str, english: bool = False) -> str:
        body: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            "stream": False,
            "temperature": 0.5,
            "max_tokens": 800,
        }
        if self._thinking is not None:
            body["thinking"] = {"type": "enabled" if self._thinking else "disabled"}
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=body,
                )
                response.raise_for_status()
                payload = DeepSeekResponse.model_validate(response.json())
                if payload.choices and payload.choices[0].message.content.strip():
                    return payload.choices[0].message.content.strip()
                logging.getLogger(__name__).warning("model_general_empty_content")
        except (httpx.HTTPError, ValueError) as exc:
            logging.getLogger(__name__).warning(
                "model_general_failed %s", type(exc).__name__
            )
        return _general_fallback(english)

    async def stream_answer(
        self,
        *,
        question: str,
        context: list[str],
        guidance: ReplyGuidance | None = None,
    ) -> AsyncIterator[str]:
        if not context and selected_card(guidance, question).needs_knowledge:
            yield await self._fallback.answer(question=question, context=context, guidance=guidance)
            return

        messages = self._messages(question=question, context=context, guidance=guidance)
        body: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "temperature": self._temperature,
            "max_tokens": 800,
        }
        if self._thinking is not None:
            body["thinking"] = {"type": "enabled" if self._thinking else "disabled"}

        emitted = False
        try:
            async with (
                httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout_seconds,
                    transport=self._transport,
                ) as client,
                client.stream(
                    "POST",
                    "/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Accept": "text/event-stream",
                    },
                    json=body,
                ) as response,
            ):
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[len("data:") :].strip()
                    if payload == "[DONE]":
                        break
                    delta = _extract_delta(payload)
                    if delta:
                        emitted = True
                        yield delta
        except (httpx.HTTPError, ValueError):
            pass

        if not emitted:
            yield await self._fallback.answer(question=question, context=context, guidance=guidance)

    def _messages(
        self,
        *,
        question: str,
        context: list[str],
        guidance: ReplyGuidance | None,
    ) -> list[dict[str, str]]:
        prompt = compose_prompt(
            intent=guidance.intent if guidance is not None else Intent.FAQ,
            question=question,
            knowledge=context,
            authenticated=guidance.authenticated if guidance is not None else False,
        )
        # 示例在 system 内明确标注为独立参考，不能伪装成当前用户的历史消息。
        return [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": question},
        ]


def build_model_provider(settings: Settings) -> ModelProvider:
    provider = settings.provider.strip().lower()
    if provider in {"deepseek", "mlx"} and (settings.api_key or provider == "mlx"):
        return DeepSeekModel(
            api_key=settings.api_key or "local-mlx",
            model=settings.model,
            base_url=settings.model_base_url,
            timeout_seconds=settings.model_timeout_seconds,
            temperature=0.0 if provider == "mlx" else 0.2,
            thinking=settings.thinking if provider == "deepseek" else None,
        )
    return GroundedLocalModel()
