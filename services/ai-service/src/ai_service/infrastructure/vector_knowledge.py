"""向量知识检索：BGE 嵌入 + 余弦相似度。

知识条目只有十几条，直接在内存里做矩阵乘法即可，不引入向量数据库。
知识规模上千条后再换 pgvector，``search`` 接口保持不变。

任何一步失败（模型缺失、推理异常）都会自动降级为关键词检索，
并打印一次告警，避免拖垮整个客服链路。
"""

import asyncio
import logging
import threading
from uuid import UUID

import numpy as np

from ai_service.domain.models import Citation
from ai_service.domain.ports import KnowledgeRetriever
from ai_service.infrastructure.embeddings import Embedder, normalize
from ai_service.infrastructure.local_knowledge import DEFAULT_ENTRIES, KnowledgeEntry
from ai_service.infrastructure.query_normalization import normalize_query_text

logger = logging.getLogger(__name__)


class VectorKnowledgeRetriever:
    def __init__(
        self,
        embedder: Embedder,
        *,
        entries: tuple[KnowledgeEntry, ...] = DEFAULT_ENTRIES,
        min_score: float = 0.45,
        max_results: int = 1,
        fallback: KnowledgeRetriever | None = None,
    ) -> None:
        self._embedder = embedder
        self._entries = entries
        self._min_score = min_score
        self._max_results = max_results
        self._fallback = fallback
        self._matrix: np.ndarray | None = None
        self._owners: np.ndarray | None = None
        self._lock = threading.Lock()
        self._disabled = False

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        if self._disabled:
            return await self._delegate(query, limit, merchant_id)

        try:
            matrix, owners = await asyncio.to_thread(self._ensure_matrix)
            vector = await asyncio.to_thread(
                self._embedder.embed_query, normalize_query_text(query)
            )
        except Exception:
            logger.exception("向量检索不可用，已降级为关键词检索")
            self._disabled = True
            return await self._delegate(query, limit, merchant_id)

        prototype_scores = matrix @ normalize(vector)
        scores = np.full(len(self._entries), -np.inf, dtype=np.float32)
        np.maximum.at(scores, owners, prototype_scores)
        order = np.argsort(-scores)
        results: list[tuple[str, Citation]] = []
        for index in order[: min(limit, self._max_results)]:
            score = float(scores[index])
            if score < self._min_score:
                continue
            entry = self._entries[int(index)]
            results.append((entry.content, entry.citation))
        if not results:
            # 向量没把握时退回关键词，避免把本来能命中的精确词漏掉
            return await self._delegate(query, limit, merchant_id)
        return results

    def _ensure_matrix(self) -> tuple[np.ndarray, np.ndarray]:
        with self._lock:
            if self._matrix is None:
                texts: list[str] = []
                owners: list[int] = []
                for index, entry in enumerate(self._entries):
                    texts.extend(entry.embedding_texts)
                    owners.extend([index] * len(entry.embedding_texts))
                vectors = self._embedder.embed_documents(texts)
                self._matrix = normalize(np.vstack(vectors))
                self._owners = np.asarray(owners, dtype=np.intp)
            assert self._owners is not None
            return self._matrix, self._owners

    async def _delegate(
        self, query: str, limit: int, merchant_id: UUID | None
    ) -> list[tuple[str, Citation]]:
        if self._fallback is None:
            return []
        return await self._fallback.search(query, limit=limit, merchant_id=merchant_id)
