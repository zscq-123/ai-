"""向量检索 + 关键词检索的融合。

单靠向量会漏掉精确词命中（例如“包邮吗”），单靠关键词又听不懂改写说法。
这里用 RRF（倒数排名融合）把两路结果合并，取长补短。
"""

from uuid import UUID

from ai_service.domain.models import Citation
from ai_service.domain.ports import KnowledgeRetriever

DEFAULT_RANK_CONSTANT = 60


class HybridKnowledgeRetriever:
    def __init__(
        self,
        primary: KnowledgeRetriever,
        secondary: KnowledgeRetriever,
        *,
        rank_constant: int = DEFAULT_RANK_CONSTANT,
        primary_weight: float = 1.0,
        secondary_weight: float = 1.0,
        prefer_secondary_when_available: bool = False,
        prefer_single_secondary: bool = False,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._rank_constant = rank_constant
        self._weights = (primary_weight, secondary_weight)
        self._prefer_secondary_when_available = prefer_secondary_when_available
        self._prefer_single_secondary = prefer_single_secondary

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        primary = await self._primary.search(query, limit=limit, merchant_id=merchant_id)
        secondary = await self._secondary.search(query, limit=limit, merchant_id=merchant_id)
        if self._prefer_secondary_when_available and secondary:
            return secondary[:limit]
        if self._prefer_single_secondary and len(secondary) == 1:
            return secondary[:limit]

        fused: dict[str, float] = {}
        payload: dict[str, tuple[str, Citation]] = {}
        for results, weight in zip((primary, secondary), self._weights, strict=True):
            for rank, (content, citation) in enumerate(results, start=1):
                reference = citation.reference
                fused[reference] = fused.get(reference, 0.0) + weight / (
                    self._rank_constant + rank
                )
                payload.setdefault(reference, (content, citation))

        ordered = sorted(fused.items(), key=lambda item: -item[1])[:limit]
        return [payload[reference] for reference, _ in ordered]
