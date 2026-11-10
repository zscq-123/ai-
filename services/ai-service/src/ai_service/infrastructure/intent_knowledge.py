"""基于已标注意图样例的本地近邻检索。"""

import asyncio
import json
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass
from importlib.resources import files
from uuid import UUID

import numpy as np

from ai_service.domain.models import Citation
from ai_service.domain.ports import KnowledgeRetriever
from ai_service.infrastructure.embeddings import Embedder, normalize
from ai_service.infrastructure.local_knowledge import DEFAULT_ENTRIES, KnowledgeEntry
from ai_service.infrastructure.query_normalization import normalize_query_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntentExample:
    query: str
    reference: str


def load_default_intent_examples() -> tuple[IntentExample, ...]:
    resource = files("ai_service.resources").joinpath("retrieval_intent_examples.jsonl")
    examples: list[IntentExample] = []
    for line_number, raw in enumerate(resource.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        payload: object = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError(f"意图样例第 {line_number} 行必须是 JSON 对象")
        query = payload.get("query")
        reference = payload.get("reference")
        if not isinstance(query, str) or not isinstance(reference, str):
            raise ValueError(f"意图样例第 {line_number} 行字段不完整")
        examples.append(IntentExample(query, reference))
    return tuple(examples)


class IntentExampleKnowledgeRetriever:
    """以加权 k 近邻将查询路由到固定政策意图或拒绝类。"""

    def __init__(
        self,
        embedder: Embedder,
        *,
        entries: tuple[KnowledgeEntry, ...] = DEFAULT_ENTRIES,
        examples: tuple[IntentExample, ...] | None = None,
        neighbors: int = 3,
        fallback: KnowledgeRetriever | None = None,
        out_of_scope_fallback: KnowledgeRetriever | None = None,
    ) -> None:
        self._embedder = embedder
        self._entries = {entry.citation.reference: entry for entry in entries}
        self._examples = examples or load_default_intent_examples()
        if not self._examples:
            raise ValueError("意图样例不能为空")
        self._neighbors = min(neighbors, len(self._examples))
        self._fallback = fallback
        self._out_of_scope_fallback = out_of_scope_fallback
        self._matrix: np.ndarray | None = None
        self._lock = threading.Lock()
        self._disabled = False

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        if self._disabled:
            return await self._delegate(query, limit, merchant_id)
        try:
            matrix = await asyncio.to_thread(self._ensure_matrix)
            vector = normalize(
                await asyncio.to_thread(self._embedder.embed_query, normalize_query_text(query))
            )
        except Exception:
            logger.exception("意图样例路由不可用，已降级为基础检索")
            self._disabled = True
            return await self._delegate(query, limit, merchant_id)

        scores = matrix @ vector
        nearest = np.argsort(-scores)[: self._neighbors]
        votes: dict[str, float] = defaultdict(float)
        for index in nearest:
            score = max(float(scores[index]), 0.0)
            votes[self._examples[int(index)].reference] += score**4
        reference = max(votes.items(), key=lambda item: item[1])[0]
        if not reference:
            if self._out_of_scope_fallback is None:
                return []
            return await self._out_of_scope_fallback.search(
                query, limit=limit, merchant_id=merchant_id
            )
        entry = self._entries.get(reference)
        if entry is None:
            return await self._delegate(query, limit, merchant_id)
        return [(entry.content, entry.citation)]

    def _ensure_matrix(self) -> np.ndarray:
        with self._lock:
            if self._matrix is None:
                vectors = self._embedder.embed_documents(
                    [normalize_query_text(example.query) for example in self._examples]
                )
                self._matrix = normalize(np.vstack(vectors))
            return self._matrix

    async def _delegate(
        self, query: str, limit: int, merchant_id: UUID | None
    ) -> list[tuple[str, Citation]]:
        if self._fallback is None:
            return []
        return await self._fallback.search(query, limit=limit, merchant_id=merchant_id)
