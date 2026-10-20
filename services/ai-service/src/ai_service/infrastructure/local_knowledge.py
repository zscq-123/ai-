from ai_service.domain.models import Citation


class LocalKnowledgeRetriever:
    _documents = (
        (
            "平台商品由自营店铺或审核通过的第三方商家提供，店铺信息会显示在商品详情页。",
            Citation("平台交易规则", "policy://marketplace"),
        ),
        (
            "现货商品通常在付款后 24 小时内出库，实际时效以订单物流节点为准。",
            Citation("配送说明", "policy://delivery"),
        ),
        (
            "企业采购订单支持开具合规发票，具体票种由店铺和商品类目决定。",
            Citation("企业采购指南", "policy://invoice"),
        ),
    )

    async def search(self, query: str, *, limit: int = 4) -> list[tuple[str, Citation]]:
        terms = set(query)
        ranked = sorted(
            self._documents, key=lambda item: len(terms.intersection(item[0])), reverse=True
        )
        return list(ranked[:limit])
