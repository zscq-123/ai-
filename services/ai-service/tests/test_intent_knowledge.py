from collections.abc import Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from ai_service.domain.models import Citation
from ai_service.infrastructure.intent_knowledge import (
    IntentExample,
    IntentExampleKnowledgeRetriever,
    load_default_intent_examples,
)
from ai_service.infrastructure.local_knowledge import KnowledgeEntry


class FakeEmbedder:
    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping

    def embed_documents(self, texts: Sequence[str]) -> list[NDArray[np.float32]]:
        return [np.asarray(self._mapping[text], dtype=np.float32) for text in texts]

    def embed_query(self, text: str) -> NDArray[np.float32]:
        return np.asarray(self._mapping[text], dtype=np.float32)


class StubRetriever:
    def __init__(self) -> None:
        self.calls = 0

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        del query, limit, merchant_id
        self.calls += 1
        return [("外部知识", Citation("外部", "kb://external"))]


def _entries() -> tuple[KnowledgeEntry, ...]:
    return (
        KnowledgeEntry("配送政策", Citation("配送", "policy://delivery"), ()),
        KnowledgeEntry("退款政策", Citation("退款", "policy://refund"), ()),
    )


async def test_routes_to_nearest_intent() -> None:
    examples = (
        IntentExample("多久发货", "policy://delivery"),
        IntentExample("几时寄出", "policy://delivery"),
        IntentExample("钱多久退", "policy://refund"),
    )
    embedder = FakeEmbedder(
        {
            "多久发货": [1.0, 0.0],
            "几时寄出": [0.9, 0.1],
            "钱多久退": [0.0, 1.0],
            "什么时候出库": [0.95, 0.05],
        }
    )
    retriever = IntentExampleKnowledgeRetriever(
        embedder, entries=_entries(), examples=examples, neighbors=1
    )

    results = await retriever.search("什么时候出库")

    assert results[0][1].reference == "policy://delivery"


async def test_out_of_scope_class_returns_empty() -> None:
    examples = (
        IntentExample("多久发货", "policy://delivery"),
        IntentExample("修改密码", ""),
    )
    embedder = FakeEmbedder(
        {
            "多久发货": [1.0, 0.0],
            "修改密码": [0.0, 1.0],
            "忘记密码": [0.1, 0.9],
        }
    )
    retriever = IntentExampleKnowledgeRetriever(
        embedder, entries=_entries(), examples=examples, neighbors=1
    )

    assert await retriever.search("忘记密码") == []


async def test_out_of_scope_can_search_external_knowledge() -> None:
    external = StubRetriever()
    examples = (
        IntentExample("多久发货", "policy://delivery"),
        IntentExample("产品说明书", ""),
    )
    embedder = FakeEmbedder(
        {
            "多久发货": [1.0, 0.0],
            "产品说明书": [0.0, 1.0],
            "耳机说明书": [0.1, 0.9],
        }
    )
    retriever = IntentExampleKnowledgeRetriever(
        embedder,
        entries=_entries(),
        examples=examples,
        neighbors=1,
        out_of_scope_fallback=external,
    )

    results = await retriever.search("耳机说明书")

    assert results[0][1].reference == "kb://external"
    assert external.calls == 1


def test_packaged_examples_are_complete() -> None:
    examples = load_default_intent_examples()

    assert len(examples) == 624
    assert len({example.query for example in examples}) == 624
