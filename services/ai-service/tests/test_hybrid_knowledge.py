from uuid import UUID

import pytest

from ai_service.domain.models import Citation
from ai_service.infrastructure.hybrid_knowledge import HybridKnowledgeRetriever


class FixedRetriever:
    def __init__(self, results: list[tuple[str, Citation]]) -> None:
        self._results = results

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        del query, merchant_id
        return self._results[:limit]


def _item(name: str) -> tuple[str, Citation]:
    return (f"{name} 内容", Citation(name, f"kb://{name}"))


@pytest.mark.asyncio
async def test_document_present_in_both_ranks_first() -> None:
    primary = FixedRetriever([_item("vec-only"), _item("both")])
    secondary = FixedRetriever([_item("both"), _item("kw-only")])
    hybrid = HybridKnowledgeRetriever(primary, secondary)

    results = await hybrid.search("q", limit=3)

    assert [citation.reference for _, citation in results][0] == "kb://both"


@pytest.mark.asyncio
async def test_keyword_only_document_is_kept() -> None:
    primary = FixedRetriever([_item("vec-only")])
    secondary = FixedRetriever([_item("kw-only")])
    hybrid = HybridKnowledgeRetriever(primary, secondary)

    references = {citation.reference for _, citation in await hybrid.search("q", limit=4)}

    assert references == {"kb://vec-only", "kb://kw-only"}


@pytest.mark.asyncio
async def test_respects_limit() -> None:
    primary = FixedRetriever([_item("a"), _item("b"), _item("c")])
    secondary = FixedRetriever([_item("d"), _item("e")])
    hybrid = HybridKnowledgeRetriever(primary, secondary)

    assert len(await hybrid.search("q", limit=3)) == 3


@pytest.mark.asyncio
async def test_empty_inputs_return_empty() -> None:
    hybrid = HybridKnowledgeRetriever(FixedRetriever([]), FixedRetriever([]))

    assert await hybrid.search("q") == []


@pytest.mark.asyncio
async def test_configured_weight_breaks_conflicting_top_rank_tie() -> None:
    primary = FixedRetriever([_item("semantic-neighbor")])
    secondary = FixedRetriever([_item("exact-keyword")])
    hybrid = HybridKnowledgeRetriever(primary, secondary, secondary_weight=1.1)

    results = await hybrid.search("q", limit=2)

    assert results[0][1].reference == "kb://exact-keyword"


@pytest.mark.asyncio
async def test_authoritative_secondary_omits_noisy_semantic_neighbors() -> None:
    primary = FixedRetriever([_item("semantic-neighbor"), _item("another-neighbor")])
    secondary = FixedRetriever([_item("exact-keyword")])
    hybrid = HybridKnowledgeRetriever(
        primary,
        secondary,
        prefer_secondary_when_available=True,
    )

    results = await hybrid.search("q", limit=4)

    assert [citation.reference for _, citation in results] == ["kb://exact-keyword"]


@pytest.mark.asyncio
async def test_single_exact_secondary_can_override_semantic_neighbor() -> None:
    hybrid = HybridKnowledgeRetriever(
        FixedRetriever([_item("semantic-neighbor")]),
        FixedRetriever([_item("single-exact")]),
        primary_weight=1.2,
        prefer_single_secondary=True,
    )

    results = await hybrid.search("q", limit=4)

    assert [citation.reference for _, citation in results] == ["kb://single-exact"]
