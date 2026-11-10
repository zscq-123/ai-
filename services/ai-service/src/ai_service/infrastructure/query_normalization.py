"""客服检索查询的轻量规范化。"""

import unicodedata

_COMMON_CORRECTIONS: tuple[tuple[str, str], ...] = (
    ("时侯", "时候"),
    ("到那", "到哪"),
    ("退歀", "退款"),
    ("无里由", "无理由"),
    ("成担", "承担"),
    ("抬投", "抬头"),
    ("活东", "活动"),
    ("才质", "材质"),
    ("还又", "还有"),
    ("支护宝", "支付宝"),
    ("企页", "企业"),
    ("进渡", "进度"),
    ("自莹", "自营"),
    ("寄粗", "寄出"),
    ("信西", "信息"),
    ("到帐", "到账"),
    ("退道", "退到"),
    ("恵", "惠"),
    ("沒", "没"),
    ("换贷", "换货"),
    ("多仲", "多重"),
    ("信拥卡", "信用卡"),
)


def normalize_query_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold().strip()
    for wrong, correct in _COMMON_CORRECTIONS:
        normalized = normalized.replace(wrong, correct)
    return normalized
