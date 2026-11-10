from collections.abc import Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from ai_service.domain.models import Citation
from ai_service.infrastructure.semantic_scope import SemanticScopeGuard


class FakeEmbedder:
    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping

    def embed_documents(self, texts: Sequence[str]) -> list[NDArray[np.float32]]:
        return [np.array(self._mapping[text], dtype=np.float32) for text in texts]

    def embed_query(self, text: str) -> NDArray[np.float32]:
        return np.array(self._mapping[text], dtype=np.float32)


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls = 0

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        del query, limit, merchant_id
        self.calls += 1
        return [("配送知识", Citation("配送", "kb://delivery"))]


async def test_supported_query_reaches_inner_retriever() -> None:
    inner = RecordingRetriever()
    embedder = FakeEmbedder(
        {
            "配送政策": [1.0, 0.0],
            "取消订单未覆盖": [0.0, 1.0],
            "什么时候发货": [0.9, 0.1],
        }
    )
    guard = SemanticScopeGuard(
        inner,
        embedder,
        supported_texts=("配送政策",),
        unsupported_texts=("取消订单未覆盖",),
    )

    results = await guard.search("什么时候发货")

    assert results[0][1].reference == "kb://delivery"
    assert inner.calls == 1


async def test_unsupported_query_is_rejected_before_retrieval() -> None:
    inner = RecordingRetriever()
    embedder = FakeEmbedder(
        {
            "配送政策": [1.0, 0.0],
            "取消订单未覆盖": [0.0, 1.0],
            "我要取消订单": [0.1, 0.9],
        }
    )
    guard = SemanticScopeGuard(
        inner,
        embedder,
        supported_texts=("配送政策",),
        unsupported_texts=("取消订单未覆盖",),
    )

    assert await guard.search("我要取消订单") == []
    assert inner.calls == 0


async def test_small_negative_advantage_does_not_reject_supported_query() -> None:
    inner = RecordingRetriever()
    embedder = FakeEmbedder(
        {
            "库存政策": [0.70, 0.30],
            "优惠券未覆盖": [0.68, 0.32],
            "这个版本还能买到吗": [0.69, 0.31],
        }
    )
    guard = SemanticScopeGuard(
        inner,
        embedder,
        supported_texts=("库存政策",),
        unsupported_texts=("优惠券未覆盖",),
    )

    assert await guard.search("这个版本还能买到吗")
    assert inner.calls == 1


async def test_guard_fails_open_when_embedding_is_unavailable() -> None:
    class BrokenEmbedder:
        def embed_documents(self, texts: Sequence[str]) -> list[NDArray[np.float32]]:
            del texts
            raise RuntimeError("model missing")

        def embed_query(self, text: str) -> NDArray[np.float32]:
            del text
            raise RuntimeError("model missing")

    inner = RecordingRetriever()
    guard = SemanticScopeGuard(
        inner,
        BrokenEmbedder(),
        supported_texts=("配送政策",),
        unsupported_texts=("取消订单未覆盖",),
    )

    results = await guard.search("什么时候发货")

    assert results
    assert inner.calls == 1
