from collections.abc import Sequence
from uuid import UUID

import numpy as np
import pytest
from numpy.typing import NDArray

from ai_service.domain.models import Citation
from ai_service.infrastructure.local_knowledge import KnowledgeEntry
from ai_service.infrastructure.vector_knowledge import VectorKnowledgeRetriever

ENTRIES = (
    KnowledgeEntry("发货知识", Citation("配送", "kb://delivery"), ()),
    KnowledgeEntry("发票知识", Citation("发票", "kb://invoice"), ()),
)


class FakeEmbedder:
    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping
        self.embed_calls = 0

    def embed_documents(self, texts: Sequence[str]) -> list[NDArray[np.float32]]:
        return [np.array(self._mapping[text], dtype=np.float32) for text in texts]

    def embed_query(self, text: str) -> NDArray[np.float32]:
        self.embed_calls += 1
        return np.array(self._mapping[text], dtype=np.float32)


class StubRetriever:
    def __init__(self) -> None:
        self.calls = 0

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        del query, limit, merchant_id
        self.calls += 1
        return [("关键词兜底", Citation("兜底", "kb://fallback"))]


def _embedder() -> FakeEmbedder:
    return FakeEmbedder(
        {
            "发货知识": [1.0, 0.0, 0.0],
            "发票知识": [0.0, 1.0, 0.0],
            "多久发货": [0.98, 0.2, 0.0],
            "能开发票吗": [0.1, 0.99, 0.0],
            "你好": [0.0, 0.0, 1.0],
        }
    )


@pytest.mark.asyncio
async def test_ranks_by_cosine_similarity() -> None:
    retriever = VectorKnowledgeRetriever(_embedder(), entries=ENTRIES, min_score=0.5)

    delivery = await retriever.search("多久发货")
    invoice = await retriever.search("能开发票吗")

    assert [citation.reference for _, citation in delivery] == ["kb://delivery"]
    assert [citation.reference for _, citation in invoice] == ["kb://invoice"]


@pytest.mark.asyncio
async def test_returns_only_the_highest_confidence_vector_result_by_default() -> None:
    retriever = VectorKnowledgeRetriever(_embedder(), entries=ENTRIES, min_score=0.1)

    results = await retriever.search("多久发货", limit=4)

    assert [citation.reference for _, citation in results] == ["kb://delivery"]


@pytest.mark.asyncio
async def test_filters_below_threshold() -> None:
    retriever = VectorKnowledgeRetriever(_embedder(), entries=ENTRIES, min_score=0.5)

    assert await retriever.search("你好") == []


@pytest.mark.asyncio
async def test_falls_back_to_keyword_when_nothing_passes_threshold() -> None:
    fallback = StubRetriever()
    retriever = VectorKnowledgeRetriever(
        _embedder(), entries=ENTRIES, min_score=0.5, fallback=fallback
    )

    results = await retriever.search("你好")

    assert results == [("关键词兜底", Citation("兜底", "kb://fallback"))]
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_document_vectors_are_embedded_once() -> None:
    embedder = _embedder()
    retriever = VectorKnowledgeRetriever(embedder, entries=ENTRIES, min_score=0.5)

    await retriever.search("多久发货")
    await retriever.search("能开发票吗")

    assert embedder.embed_calls == 2


@pytest.mark.asyncio
async def test_document_embedding_includes_curated_keywords() -> None:
    class RecordingEmbedder:
        def __init__(self) -> None:
            self.documents: list[str] = []

        def embed_documents(self, texts: Sequence[str]) -> list[NDArray[np.float32]]:
            self.documents = list(texts)
            return [np.array([1.0, 0.0], dtype=np.float32) for _ in texts]

        def embed_query(self, text: str) -> NDArray[np.float32]:
            del text
            return np.array([1.0, 0.0], dtype=np.float32)

    entry = KnowledgeEntry(
        "退款原路返回。",
        Citation("退款", "kb://refund"),
        ("退钱", "到账"),
    )
    embedder = RecordingEmbedder()
    retriever = VectorKnowledgeRetriever(embedder, entries=(entry,), min_score=0.5)

    await retriever.search("钱退到哪")

    assert embedder.documents == ["退钱 到账 退款原路返回。"]


@pytest.mark.asyncio
async def test_falls_back_when_embedding_fails() -> None:
    class BrokenEmbedder:
        def embed_documents(self, texts: Sequence[str]) -> list[NDArray[np.float32]]:
            raise RuntimeError("model missing")

        def embed_query(self, text: str) -> NDArray[np.float32]:
            raise RuntimeError("model missing")

    fallback = StubRetriever()
    retriever = VectorKnowledgeRetriever(
        BrokenEmbedder(), entries=ENTRIES, min_score=0.5, fallback=fallback
    )

    results = await retriever.search("多久发货")

    assert results == [("关键词兜底", Citation("兜底", "kb://fallback"))]
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_stays_on_fallback_after_failure() -> None:
    class BrokenEmbedder:
        def __init__(self) -> None:
            self.calls = 0

        def embed_documents(self, texts: Sequence[str]) -> list[NDArray[np.float32]]:
            self.calls += 1
            raise RuntimeError("model missing")

        def embed_query(self, text: str) -> NDArray[np.float32]:
            raise RuntimeError("model missing")

    embedder = BrokenEmbedder()
    retriever = VectorKnowledgeRetriever(
        embedder, entries=ENTRIES, min_score=0.5, fallback=StubRetriever()
    )

    await retriever.search("多久发货")
    await retriever.search("能开发票吗")

    assert embedder.calls == 1
