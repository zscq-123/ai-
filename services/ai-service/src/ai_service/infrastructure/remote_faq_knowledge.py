"""读取企业审核发布的知识，失败时由组合检索器继续使用本地知识。"""

import hashlib
import hmac
import json
import logging
import time
from uuid import UUID

import httpx

from ai_service.domain.models import Citation

logger = logging.getLogger(__name__)


def _bigrams(text: str) -> set[str]:
    cleaned = "".join(char.lower() for char in text if char.isalnum())
    return {cleaned[index : index + 2] for index in range(len(cleaned) - 1)}


class RemoteFaqKnowledgeRetriever:
    def __init__(
        self,
        commerce_api_url: str,
        trusted_context_secret: str,
        *,
        timeout_seconds: float = 2.0,
        failure_cooldown_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = commerce_api_url.rstrip("/")
        self._secret = trusted_context_secret
        self._timeout_seconds = timeout_seconds
        self._failure_cooldown_seconds = failure_cooldown_seconds
        self._transport = transport
        self._retry_after = 0.0

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        # 企业知识必须绑定已由商城网关签名的商家范围，匿名请求不能跨店检索。
        if merchant_id is None:
            return []
        if time.monotonic() < self._retry_after:
            return []
        request_payload = {"query": query.strip(), "merchantId": str(merchant_id)}
        body = json.dumps(request_payload, ensure_ascii=False, separators=(",", ":"))
        timestamp = str(int(time.time()))
        path = "/api/internal/support/knowledge-search"
        signed = f"{timestamp}\nPOST\n{path}\n{body}".encode()
        signature = hmac.new(
            self._secret.encode(), signed, hashlib.sha256
        ).hexdigest()
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    path,
                    content=body.encode(),
                    headers={
                        "Content-Type": "application/json",
                        "X-Nova-Timestamp": timestamp,
                        "X-Nova-Signature": signature,
                    },
                )
                response.raise_for_status()
                payload: object = response.json()
        except (httpx.HTTPError, ValueError):
            self._retry_after = time.monotonic() + self._failure_cooldown_seconds
            logger.warning("企业知识库暂不可用，继续使用本地知识库")
            return []
        self._retry_after = 0.0
        if not isinstance(payload, list):
            return []

        query_text = query.strip().lower()
        query_bigrams = _bigrams(query_text)
        ranked: list[tuple[int, int, str, Citation]] = []
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                continue
            entry_id = raw.get("documentId", raw.get("id"))
            question = raw.get("title", raw.get("question"))
            answer = raw.get("content", raw.get("answer"))
            raw_keywords = raw.get("keywords")
            if (
                not isinstance(entry_id, str)
                or not isinstance(question, str)
                or not isinstance(answer, str)
            ):
                continue
            keywords = (
                [item.lower() for item in raw_keywords if isinstance(item, str)]
                if isinstance(raw_keywords, list)
                else []
            )
            normalized_question = question.strip().lower()
            exact = 100 if query_text == normalized_question else 0
            keyword_hits = sum(
                1 for keyword in keywords if keyword and keyword in query_text
            )
            overlap = len(query_bigrams & _bigrams(normalized_question + answer))
            # 内部接口已经完成发布状态、商家和产品范围过滤；没有显式 FAQ
            # 关键词时仍保留其结果顺序，避免中文无空格问题被本地二次过滤。
            score = exact + keyword_hits * 20 + overlap
            if "documentId" in raw:
                score = max(score, 1)
            if score <= 0:
                continue
            ranked.append(
                (
                    score,
                    index,
                    answer.strip(),
                    Citation(
                        "企业知识库",
                        str(raw.get("source") or f"knowledge://{entry_id}"),
                    ),
                )
            )
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [(answer, citation) for _, _, answer, citation in ranked[:limit] if answer]
