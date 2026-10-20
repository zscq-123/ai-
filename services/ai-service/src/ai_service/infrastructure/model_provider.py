import httpx
from pydantic import BaseModel

from ai_service.config import Settings
from ai_service.domain.ports import ModelProvider


class DeepSeekMessage(BaseModel):
    content: str


class DeepSeekChoice(BaseModel):
    message: DeepSeekMessage


class DeepSeekResponse(BaseModel):
    choices: list[DeepSeekChoice]


class GroundedLocalModel:
    async def answer(self, *, question: str, context: list[str]) -> str:
        if not context:
            return "当前知识库没有足够信息，我可以为你转接人工客服。"
        return f"根据平台规则：{context[0]} 如需查询个人订单，请先登录后提供订单号。"


class DeepSeekModel:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
        fallback: ModelProvider | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._fallback = fallback or GroundedLocalModel()

    async def answer(self, *, question: str, context: list[str]) -> str:
        if not context:
            return await self._fallback.answer(question=question, context=context)
        system_prompt = (
            "你是企业商城的客服助手。只能依据提供的知识回答，不得编造商品、订单、库存、"
            "价格或售后状态。若知识不足，应明确说明并建议转人工。不要执行退款、改价、"
            "取消订单等操作。使用简洁、礼貌的中文回答。\n\n可用知识：\n- "
            + "\n- ".join(context)
        )
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": question},
                        ],
                        "stream": False,
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                payload = DeepSeekResponse.model_validate(response.json())
                if payload.choices and payload.choices[0].message.content.strip():
                    return payload.choices[0].message.content.strip()
        except (httpx.HTTPError, ValueError):
            pass
        return await self._fallback.answer(question=question, context=context)


def build_model_provider(settings: Settings) -> ModelProvider:
    if settings.provider == "deepseek" and settings.api_key:
        return DeepSeekModel(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.model_base_url,
            timeout_seconds=settings.model_timeout_seconds,
        )
    return GroundedLocalModel()
