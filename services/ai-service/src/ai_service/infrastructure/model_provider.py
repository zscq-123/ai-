class GroundedLocalModel:
    async def answer(self, *, question: str, context: list[str]) -> str:
        if not context:
            return "当前知识库没有足够信息，我可以为你转接人工客服。"
        return f"根据平台规则：{context[0]} 如需查询个人订单，请先登录后提供订单号。"
