"""Independent JSON model turns used by the support supervisor and specialists."""

import asyncio
import json
import logging
from typing import Any, Protocol

import httpx

from ai_service.config import Settings


class AgentModelError(RuntimeError):
    pass


class AgentModel(Protocol):
    async def complete(
        self, *, role: str, system: str, messages: list[dict[str, str]]
    ) -> dict[str, Any]: ...


class JsonAgentModel:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport
        self._slots = asyncio.Semaphore(4)

    async def complete(
        self, *, role: str, system: str, messages: list[dict[str, str]]
    ) -> dict[str, Any]:
        if self.settings.provider not in {"deepseek", "mlx"} or (
            self.settings.provider == "deepseek" and not self.settings.api_key
        ):
            raise AgentModelError("agent_model_unconfigured")
        try:
            async with asyncio.timeout(self.settings.agent_call_timeout_seconds):
                async with (
                    self._slots,
                    httpx.AsyncClient(
                        base_url=self.settings.model_base_url,
                        timeout=self.settings.agent_call_timeout_seconds,
                        transport=self.transport,
                    ) as client,
                ):
                    body: dict[str, Any] = {
                        "model": self.settings.model,
                        "messages": [{"role": "system", "content": system}, *messages],
                        "response_format": {"type": "json_object"},
                        "temperature": 0,
                        "max_tokens": 700,
                        "stream": False,
                    }
                    if self.settings.provider == "deepseek":
                        body["thinking"] = {"type": "disabled"}
                    response = await client.post(
                        "/chat/completions",
                        headers={"Authorization": f"Bearer {self.settings.api_key or 'local-mlx'}"},
                        json=body,
                    )
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    if not isinstance(content, str) or len(content) > 12000:
                        raise ValueError("invalid content")
                    result = json.loads(content)
                    if not isinstance(result, dict):
                        raise ValueError("invalid JSON object")
                    return result
        except (TimeoutError, httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            # Never include provider response bodies, messages, or credentials in logs.
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
            logging.getLogger("uvicorn.error").warning(
                "support_agent_model_failure role=%s category=%s http_status=%s",
                role,
                type(exc).__name__,
                status,
            )
            raise AgentModelError("agent_model_unavailable") from exc
