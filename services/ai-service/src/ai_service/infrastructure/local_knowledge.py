"""本地知识检索。

当前实现是「关键词 + 字符二元组」的轻量检索，不依赖向量模型：

- 每条知识带一组关键词，命中即得分；
- 没有关键词命中时，用字符二元组重叠做兜底；
- 低于阈值直接返回空，让上层按「知识不足」处理，避免把无关内容塞进提示词。

这只是过渡方案。知识规模超过百条或同义表达变多后，应换成 embedding + pgvector，
对外接口 ``search`` 不需要改动。

注意：以下条目是平台规则的占位版本，上线前必须替换为法务确认后的正式条款。
"""

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from ai_service.domain.models import Citation
from ai_service.infrastructure.query_normalization import normalize_query_text


@dataclass(frozen=True)
class KnowledgeEntry:
    content: str
    citation: Citation
    keywords: tuple[str, ...]
    examples: tuple[str, ...] = ()

    @property
    def search_text(self) -> str:
        """用于向量化的文本：关键词在前，正文在后。

        把运营维护的关键词一起嵌入，相当于在语义空间里保留一份词表信号，
        对短查询和行业术语更稳。
        """

        if not self.keywords:
            return self.content
        return " ".join(self.keywords) + " " + self.content

    @property
    def embedding_texts(self) -> tuple[str, ...]:
        """用于语义召回的政策文本与短查询原型。"""

        return (self.search_text, *self.examples)


DEFAULT_ENTRIES: tuple[KnowledgeEntry, ...] = (
    KnowledgeEntry(
        "平台商品由自营店铺或审核通过的第三方商家提供，店铺信息会显示在商品详情页。",
        Citation("平台交易规则", "policy://marketplace"),
        ("第三方", "商家", "自营", "直营", "官方", "正品", "店铺", "谁提供"),
        (
            "谁在卖这件商品",
            "平台自营还是第三方商家",
            "在哪里查看店铺主体",
            "确认卖家身份",
            "哪家店铺销售",
            "商品详情查看经营者",
            "订单由哪个店家履约",
            "下单对象是官方还是商户",
        ),
    ),
    KnowledgeEntry(
        "现货商品通常在付款后 24 小时内出库，实际时效以订单物流节点为准。",
        Citation("配送说明", "policy://delivery"),
        (
            "发货",
            "出库",
            "时效",
            "什么时候发",
            "什么时候到",
            "送过来",
            "拿到",
            "什么时候发出",
            "寄出",
            "发走",
            "多久能到",
            "多久到",
            "几天到",
            "几天能到",
            "到货",
            "几天",
        ),
        (
            "付款后什么时候发货",
            "订单多久出库",
            "现货多久交给快递",
            "付完钱迟迟没有寄出",
            "拍下后什么时候交给承运商",
            "下单后几天能收到",
            "什么时候寄出商品",
            "预计收货时间以订单物流为准",
        ),
    ),
    KnowledgeEntry(
        "物流节点可在「我的订单」中查看，登录后按订单号查询即可看到最新进度。",
        Citation("物流查询", "policy://logistics"),
        ("物流", "快递", "到哪", "在哪儿", "节点", "单号", "派送", "包裹", "没动"),
        (
            "物流到哪了",
            "运输轨迹没有更新",
            "快递好几天没有新记录",
            "货一直没动",
            "货从仓库出来后去哪里查",
            "查询运单进度",
            "包裹当前在哪里",
            "快递是否已经揽收",
            "订单页显示包裹位置",
        ),
    ),
    KnowledgeEntry(
        "签收后 7 天内、商品不影响二次销售可以申请退货，具体以店铺售后规则为准。",
        Citation("退货政策", "policy://return"),
        ("退货", "七天", "7天", "无理由", "签收", "还能退", "退不", "包装拆"),
        (
            "不想要了可以退吗",
            "签收七天内能退吗",
            "拆封后能否退货",
            "退货需要满足什么条件",
            "退货期限从哪天开始计算",
            "商品没使用想退掉",
            "保持全新可以申请退回",
            "保持原状办理退货",
        ),
    ),
    KnowledgeEntry(
        "退款原路退回，到账时间以支付渠道为准，平台不承诺具体到账天数。",
        Citation("退款说明", "policy://refund"),
        ("退款", "到账", "原路", "退回", "退钱", "退的钱", "打到哪里"),
        (
            "退款多久到账",
            "退的钱回到哪个账户",
            "退款会原路返回吗",
            "退款一直没有到账",
            "售后同意后钱何时回来",
            "平台能保证当天退钱吗",
            "原支付账户什么时候收到退款",
        ),
    ),
    KnowledgeEntry(
        "商品未使用、包装完整可以申请换货，可换规格以实际库存为准。",
        Citation("换货政策", "policy://exchange"),
        ("换货", "换尺码", "换颜色", "换一个", "换个", "不合适"),
        (
            "尺码不对想换货",
            "颜色选错了想换一件",
            "换成另一种规格",
            "未使用可以换吗",
            "型号不合适想调换",
            "调换商品时查看实时库存",
        ),
    ),
    KnowledgeEntry(
        "运费由谁承担以店铺规则为准，下单页与售后页会明确展示。",
        Citation("运费规则", "policy://shipping-fee"),
        ("运费", "包邮", "邮费", "快递费", "偏远", "另收费"),
        (
            "寄送费用由谁承担",
            "订单是否免邮",
            "退货邮资谁负责",
            "售后寄回商品的邮资谁付",
            "偏远地区怎么收配送费",
            "退换货快递费用怎么算",
            "购买多件能否免配送费",
        ),
    ),
    KnowledgeEntry(
        "企业采购订单支持开具合规发票，具体票种由店铺和商品类目决定。",
        Citation("企业采购指南", "policy://invoice"),
        ("发票", "开票", "税号", "抬头", "报销", "凭证", "专票", "普票"),
        (
            "公司报账需要发票",
            "企业订单提供合规票据",
            "能开企业抬头的票吗",
            "在哪里申请开票",
            "可以开专用发票吗",
            "填写发票税号和抬头",
        ),
    ),
    KnowledgeEntry(
        "价格以商品详情页为准，优惠以活动页展示为准，批量采购可转企业采购专员。",
        Citation("价格与优惠", "policy://pricing"),
        ("价格", "优惠", "折扣", "便宜", "满减", "活动", "议价", "多少钱", "报价"),
        (
            "现在购买有什么折扣",
            "商品目前卖多少钱",
            "有没有满减活动",
            "批量购买如何询价",
            "团体购买能便宜一些吗",
            "询问一百件商品的价格",
            "一次订很多件询问价格",
            "五十件商品如何报价",
            "促销价格以哪里为准",
        ),
    ),
    KnowledgeEntry(
        "商品参数以详情页标注为准，不同规格之间可能存在差异。",
        Citation("商品参数", "policy://product-spec"),
        (
            "参数",
            "规格",
            "型号",
            "尺寸",
            "材质",
            "颜色",
            "续航",
            "配置",
            "重量",
            "电池",
        ),
        (
            "商品具体有多重",
            "尺寸和材质参数",
            "不同型号配置差异",
            "一次充电续航多久",
            "查看详细技术规格",
            "可选颜色是否在详情展示",
            "商品规格从哪里查询",
            "外壳使用什么材料",
        ),
    ),
    KnowledgeEntry(
        "具体规格是否有货以商品页实时库存为准；没有库存查询结果时不能确认现货。",
        Citation("库存说明", "policy://inventory"),
        ("库存", "有货", "现货", "能拍", "能下单", "还有没有", "买到", "缺货"),
        (
            "这个型号还有货吗",
            "当前是否可以下单",
            "这个规格已经售罄了吗",
            "商品还有多少库存",
            "还有几件可以买",
            "蓝色版本现在可售吗",
            "页面查看实时余量",
            "库存数字是否实时更新",
            "剩余数量以详情页为准",
            "白色款已经缺货了吗",
        ),
    ),
    KnowledgeEntry(
        "支持的支付方式以结算页展示为准，下单前可以在结算页确认。",
        Citation("支付方式", "policy://payment"),
        (
            "支付",
            "微信",
            "支付宝",
            "银行卡",
            "信用卡",
            "花呗",
            "白条",
            "分期",
            "货到付款",
            "付款方式",
            "刷卡",
            "结账",
        ),
        (
            "结算支持哪些付款方式",
            "能不能用信用卡支付",
            "可以分期付款吗",
            "支持微信或支付宝吗",
            "花呗能用于订单吗",
            "下单前查看可用支付方式",
            "实际可用支付渠道以结算页为准",
            "这个订单支持白条吗",
            "订单支持分多少期",
            "结账页没有某个支付选项",
            "是否可以货到付款",
        ),
    ),
    KnowledgeEntry(
        "批量采购与对公结算可以转接企业采购专员处理。",
        Citation("企业采购", "policy://enterprise"),
        ("企业", "公司", "单位", "批量", "大宗", "采购", "对公", "开票信息"),
        (
            "单位批量采购怎么联系",
            "对公付款流程",
            "企业客户采购通道",
            "大宗订单安排采购专员",
            "公司一次购买很多件",
            "公司大额订单如何提交",
            "单位集中购买如何结算",
            "公司准备批量订货",
        ),
    ),
    KnowledgeEntry(
        "售后申请由店铺处理，进度可在「我的订单」的售后页查看。",
        Citation("售后处理", "policy://after-sales"),
        ("售后", "售后单", "处理", "进度", "多久回复", "没人理", "没回复"),
        (
            "售后申请处理到哪一步",
            "店铺多久处理售后单",
            "查看售后办理进度",
            "申请退换后没人回复",
            "售后状态一直没有更新",
        ),
    ),
)

_MIN_KEYWORD_HITS = 1
_MIN_BIGRAM_OVERLAP = 3


def load_entries(path: Path) -> tuple[KnowledgeEntry, ...]:
    """从 JSONL 读取知识条目，每行一个 {content, reference, title, keywords}。"""

    entries: list[KnowledgeEntry] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        payload: object = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name} 第 {line_number} 行必须是 JSON 对象")
        content = payload.get("content")
        reference = payload.get("reference")
        if not isinstance(content, str) or not isinstance(reference, str):
            raise ValueError(f"{path.name} 第 {line_number} 行缺少 content 或 reference")
        title = payload.get("title")
        raw_keywords = payload.get("keywords")
        raw_examples = payload.get("examples")
        keywords = (
            tuple(item for item in raw_keywords if isinstance(item, str))
            if isinstance(raw_keywords, list)
            else ()
        )
        examples = (
            tuple(item for item in raw_examples if isinstance(item, str))
            if isinstance(raw_examples, list)
            else ()
        )
        entries.append(
            KnowledgeEntry(
                content=content,
                citation=Citation(title if isinstance(title, str) else "知识库", reference),
                keywords=keywords,
                examples=examples,
            )
        )
    return tuple(entries)


def _bigrams(text: str) -> set[str]:
    cleaned = "".join(char for char in text.casefold() if char.isalnum())
    return {cleaned[index : index + 2] for index in range(len(cleaned) - 1)}


def _score(entry: KnowledgeEntry, query: str) -> int:
    keyword_hits = _keyword_hits(entry, query)
    normalized_query = query.casefold()
    overlap = len(_bigrams(normalized_query) & _bigrams(entry.search_text))
    if keyword_hits < _MIN_KEYWORD_HITS and overlap < _MIN_BIGRAM_OVERLAP:
        return 0
    return keyword_hits * 10 + overlap


def _keyword_hits(entry: KnowledgeEntry, query: str) -> int:
    normalized_query = query.casefold()
    return sum(
        1
        for keyword in entry.keywords
        if _contains_keyword(normalized_query, keyword.casefold())
    )


def _contains_keyword(query: str, keyword: str) -> bool:
    """匹配中文关键词，同时避开“多久到”误吃“多久到账”这类词界冲突。"""

    start = query.find(keyword)
    while start >= 0:
        end = start + len(keyword)
        if not (keyword.endswith("到") and query[end : end + 1] == "账"):
            return True
        start = query.find(keyword, start + 1)
    return False


class LocalKnowledgeRetriever:
    def __init__(
        self,
        entries: tuple[KnowledgeEntry, ...] = DEFAULT_ENTRIES,
        *,
        allow_bigram_fallback: bool = True,
    ) -> None:
        self._entries = entries
        self._allow_bigram_fallback = allow_bigram_fallback

    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        del merchant_id
        query = normalize_query_text(query)
        scored = [
            (_score(entry, query), _keyword_hits(entry, query), index, entry)
            for index, entry in enumerate(self._entries)
        ]
        # 一旦存在明确关键词，只保留明确命中的意图，避免字符二元组把相邻但无关的
        # 政策一并塞进上下文。没有关键词时仍保留一个二元组兜底，供纯关键词模式使用。
        has_explicit_match = any(keyword_hits > 0 for _, keyword_hits, _, _ in scored)
        if not has_explicit_match and not self._allow_bigram_fallback:
            return []
        candidates = (
            (item for item in scored if item[1] > 0)
            if has_explicit_match
            else (item for item in scored if item[0] > 0)
        )
        ranked = sorted(
            candidates,
            key=lambda item: (-item[0], item[2]),
        )
        if not has_explicit_match:
            ranked = ranked[:1]
        return [(entry.content, entry.citation) for _, _, _, entry in ranked[:limit]]
