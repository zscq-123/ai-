"""语义范围门控：知识库未覆盖的问题不强行匹配最近文档。"""

import asyncio
import logging
import threading
from collections.abc import Sequence
from uuid import UUID

import numpy as np

from ai_service.domain.models import Citation
from ai_service.domain.ports import KnowledgeRetriever
from ai_service.infrastructure.embeddings import Embedder, normalize
from ai_service.infrastructure.query_normalization import normalize_query_text

logger = logging.getLogger(__name__)


DEFAULT_UNSUPPORTED_EXAMPLES: tuple[str, ...] = (
    "忘记登录密码",
    "注册验证码收不到",
    "更换绑定手机号或注销账户",
    "账户被冻结或锁定",
    "修改订单收货地址或收件人",
    "临时更换送货地址",
    "取消或撤销订单",
    "撤回刚才的购买",
    "合并多个订单",
    "转接真人客服",
    "投诉电话或人工回电",
    "客服工作时间",
    "商品坏了需要维修",
    "商品质保期和延长保修",
    "购买额外质保",
    "屏幕破损维修",
    "商品安装教程或视频",
    "下载商品说明书",
    "查看产品使用手册",
    "教我如何使用或连接设备",
    "会员积分有效期",
    "会员等级和生日权益",
    "领取新人优惠券",
    "优惠券兑换码如何使用",
    "预约上门安装或取件",
    "退货预约上门取件",
    "门店自提、地址或营业时间",
    "线上下单后到门店自提",
    "门店什么时候营业",
    "附近实体店位置",
    "删除或修改商品评价",
    "商品安全、有毒或健康风险",
    "材料是否伤害身体",
    "根据人群推荐商品",
    "给老人或儿童推荐型号",
    "天气、笑话、翻译或写作",
    "讲故事或闲聊",
    "中英文互相翻译",
    "今天气温或天气情况",
    "编写商品标题或广告文案",
    "撰写商品卖点",
    "助手身份或自我介绍",
    "你是真人还是程序",
)


class SemanticScopeGuard:
    """以正负语义原型判断查询是否在当前知识库范围内。"""

    def __init__(
        self,
        inner: KnowledgeRetriever,
        embedder: Embedder,
        *,
        supported_texts: Sequence[str],
        unsupported_texts: Sequence[str] = DEFAULT_UNSUPPORTED_EXAMPLES,
        rejection_margin: float = 0.025,
    ) -> None:
        if not supported_texts:
            raise ValueError("supported_texts 不能为空")
        if not unsupported_texts:
            raise ValueError("unsupported_texts 不能为空")
        self._inner = inner
        self._embedder = embedder
        self._supported_texts = tuple(supported_texts)
        self._unsupported_texts = tuple(unsupported_texts)
        self._rejection_margin = rejection_margin
        self._supported_matrix: np.ndarray | None = None
        self._unsupported_matrix: np.ndarray | None = None
        self._lock = threading.Lock()
        self._disabled = False

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        if self._disabled:
            return await self._inner.search(query, limit=limit, merchant_id=merchant_id)

        try:
            supported, unsupported = await asyncio.to_thread(self._ensure_matrices)
            vector = normalize(
                await asyncio.to_thread(self._embedder.embed_query, normalize_query_text(query))
            )
        except Exception:
            logger.exception("语义范围门控不可用，继续使用基础检索")
            self._disabled = True
            return await self._inner.search(query, limit=limit, merchant_id=merchant_id)

        supported_score = float(np.max(supported @ vector))
        unsupported_score = float(np.max(unsupported @ vector))
        if unsupported_score >= supported_score + self._rejection_margin:
            return []
        return await self._inner.search(query, limit=limit, merchant_id=merchant_id)

    def _ensure_matrices(self) -> tuple[np.ndarray, np.ndarray]:
        with self._lock:
            if self._supported_matrix is None or self._unsupported_matrix is None:
                count = len(self._supported_texts)
                vectors = self._embedder.embed_documents(
                    [*self._supported_texts, *self._unsupported_texts]
                )
                matrix = normalize(np.vstack(vectors))
                self._supported_matrix = matrix[:count]
                self._unsupported_matrix = matrix[count:]
            return self._supported_matrix, self._unsupported_matrix
