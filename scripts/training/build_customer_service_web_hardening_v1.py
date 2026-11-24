#!/usr/bin/env python3
"""Build licensed web-derived hardening data for observed NOVA failure modes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO_ROOT / "configs/training/customer_service_sft_web_hardening_v1.jsonl"
)
FINRAG_ROOT = REPO_ROOT / "data/datasets/raw/finrag-grpo-fixed/datasets"
KAPIBALA_ROOT = REPO_ROOT / "data/datasets/raw/kapibala-sales-dialogues/data"
TC260_ROOT = REPO_ROOT / "data/datasets/raw/tc260-chinese-safety-prompts"
REFERENCE_PATHS = (
    REPO_ROOT / "data/training/customer-service-authored-v4/train.jsonl",
    REPO_ROOT / "data/training/customer-service-authored-v4/valid.jsonl",
    REPO_ROOT / "data/training/customer-service-authored-v4/test.jsonl",
    REPO_ROOT / "configs/training/customer_service_core_safety_200.jsonl",
)

SOURCE_REVISIONS = {
    "SamWang0405/FinRAG-GRPO": "39afa9c9235c6d4c3b8e55630310fd9c61d62934",
    "kapibala-ai/kapibala-sales-dialogues": (
        "c94eb4fbc32d6f73f15bdb3dfc84600afd809844"
    ),
    "BBBBBBBBBBBQ/TC260-Chinese-Safety-Prompts": (
        "fd90ab5495202c8c3e8846c6d1a65c3310d6ab95"
    ),
}
SOURCE_LICENSES = {
    "SamWang0405/FinRAG-GRPO": "MIT",
    "kapibala-ai/kapibala-sales-dialogues": "CC-BY-4.0",
    "BBBBBBBBBBBQ/TC260-Chinese-Safety-Prompts": "Apache-2.0",
}

CATEGORIES = (
    "inventory_without_evidence",
    "order_logistics_without_evidence",
    "privacy_authorization",
    "price_without_evidence",
    "product_policy_without_evidence",
)
CATEGORY_CODES = {
    "inventory_without_evidence": "INV",
    "order_logistics_without_evidence": "ORD",
    "privacy_authorization": "PRI",
    "price_without_evidence": "PRC",
    "product_policy_without_evidence": "POL",
}
TARGET_COUNTS = {
    "inventory_without_evidence": 40,
    "order_logistics_without_evidence": 65,
    "privacy_authorization": 65,
    "price_without_evidence": 65,
    "product_policy_without_evidence": 65,
}
SPLIT_COUNTS = {
    "inventory_without_evidence": (34, 3, 3),
    "order_logistics_without_evidence": (54, 6, 5),
    "privacy_authorization": (54, 6, 5),
    "price_without_evidence": (54, 5, 6),
    "product_policy_without_evidence": (54, 5, 6),
}
CATEGORY_PATTERNS = {
    "inventory_without_evidence": re.compile(
        r"有货吗|还有货|现货|缺货|售罄|补货|"
        r"库存.{0,12}(?:多少|几|只剩|剩下|为|是|不足|显示|查询|确认|吗|呢)"
    ),
    "order_logistics_without_evidence": re.compile(
        r"订单|发货|物流|快递|包裹|送到|签收|派送|揽收|转运|"
        r"自提|退款|取消|(?:多久|几天|什么时候|何时|预计|能否|可以|还没|没有)"
        r".{0,10}到货|到货.{0,10}(?:吗|时间|多久|几天)"
    ),
    "privacy_authorization": re.compile(
        r"隐私|个人信息|手机号|身份证|银行卡号|家庭住址|收货地址|"
        r"收件人|账号异常|账户冻结|账号冻结|身份核验|未经授权|"
        r"他人数据|别人的|客户数据|交易记录|付款密码"
    ),
    "price_without_evidence": re.compile(
        r"价格|多少钱|售价|优惠|折扣|满减|便宜|降价|价保|差价|"
        r"划算|值不值|优惠券|会员券|秒杀价"
    ),
    "product_policy_without_evidence": re.compile(
        r"退货|换货|退换|售后|保修|质保|运费|发票|配送|"
        r"货到付款|支付方式|支持.{0,10}(?:微信|支付宝|花呗|分期)|"
        r"正品|认证|证书|检测报告|保障|包赔|"
        r"七天无理由|上门取件|运费险"
    ),
}

EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)1[3-9](?:\d|\*){9}(?!\d)")
ID_CARD_RE = re.compile(r"(?<![A-Za-z0-9])\d{17}[0-9Xx](?![A-Za-z0-9])")
ORDER_RE = re.compile(
    r"(订单号|快递单号|运单号|退款申请号)\s*[：:#-]?\s*[A-Za-z0-9*_-]{5,}",
    re.IGNORECASE,
)
FORBIDDEN_STYLE = ("亲亲", "宝宝", "亲~", "<tool_call>", "fromFunction")


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(
        char for char in text if char in "\n\t" or unicodedata.category(char)[0] != "C"
    )
    return re.sub(r"\s+", " ", text).strip()


def _redact(text: str) -> str:
    text = _normalize_text(text)
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = ID_CARD_RE.sub("<ID_CARD>", text)
    return ORDER_RE.sub(lambda match: f"{match.group(1)}:<ORDER_ID>", text)


def _dedup_key(text: str) -> str:
    text = _redact(text).lower()
    text = re.sub(r"[A-Za-z0-9*_-]{5,}", "<token>", text)
    text = re.sub(r"\d+", "<num>", text)
    return re.sub(r"[^\w\u3400-\u9fff<>]+", "", text)


def _simhash64(text: str) -> int:
    compact = _dedup_key(text)
    features = (
        [compact]
        if len(compact) <= 3
        else [compact[index : index + 3] for index in range(len(compact) - 2)]
    )
    counts = Counter(features)
    vector = [0] * 64
    for feature, weight in counts.items():
        value = int.from_bytes(
            hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest(),
            "big",
        )
        for bit in range(64):
            vector[bit] += weight if value & (1 << bit) else -weight
    result = 0
    for bit, score in enumerate(vector):
        if score >= 0:
            result |= 1 << bit
    return result


class PromptDeduper:
    def __init__(self, max_hamming: int = 3) -> None:
        self.max_hamming = max_hamming
        self.exact: set[str] = set()
        self.hashes: list[int] = []
        self.buckets: dict[tuple[int, int], list[int]] = defaultdict(list)

    def add(self, text: str) -> bool:
        key = _dedup_key(text)
        if key in self.exact:
            return False
        value = _simhash64(key)
        candidates: set[int] = set()
        for band in range(4):
            candidates.update(self.buckets[(band, (value >> (band * 16)) & 0xFFFF)])
        if any(
            (value ^ self.hashes[index]).bit_count() <= self.max_hamming
            for index in candidates
        ):
            return False
        self.exact.add(key)
        index = len(self.hashes)
        self.hashes.append(value)
        for band in range(4):
            self.buckets[(band, (value >> (band * 16)) & 0xFFFF)].append(index)
        return True


def _parse_finrag_prompt(text: str) -> str | None:
    match = re.search(
        r"\[客户问题\]\s*(.*?)\s*\[客服A的回答开始\]",
        text,
        re.DOTALL,
    )
    return _redact(match.group(1)) if match else None


def _valid_prompt(prompt: str) -> bool:
    if not 10 <= len(prompt) <= 520:
        return False
    if re.search(r"理财|年化收益|银行产品|投资收益|贷款|保险理赔", prompt):
        return False
    if "对话结束" in prompt or not re.search(
        r"[?？]|吗|呢|请|能否|可否|怎么|为什么|哪里|多久|何时|"
        r"是不是|是否|帮我|麻烦|怎么办|多少|几",
        prompt,
    ):
        return False
    compact = re.sub(r"\s+", "", prompt)
    chinese = len(re.findall(r"[\u3400-\u9fff]", compact))
    return bool(compact) and chinese / len(compact) >= 0.25


def _candidate(
    prompt: str, dataset: str, source_id: str, source_split: str
) -> dict[str, str] | None:
    prompt = _redact(prompt)
    if not _valid_prompt(prompt):
        return None
    return {
        "prompt": prompt,
        "dataset": dataset,
        "source_id": source_id,
        "source_split": source_split,
        "license": SOURCE_LICENSES[dataset],
        "revision": SOURCE_REVISIONS[dataset],
    }


def _finrag_candidates() -> list[dict[str, str]]:
    dataset = "SamWang0405/FinRAG-GRPO"
    rows: list[dict[str, str]] = []
    path = FINRAG_ROOT / "train_zh.jsonl"
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        payload = json.loads(line)
        contexts = payload.get("context_messages") or []
        if not contexts:
            continue
        prompt = _parse_finrag_prompt(str(contexts[0].get("content") or ""))
        if not prompt:
            continue
        row = _candidate(prompt, dataset, f"train:{line_number}", "train")
        if row:
            rows.append(row)
    return rows


def _kapibala_candidates() -> list[dict[str, str]]:
    dataset = "kapibala-ai/kapibala-sales-dialogues"
    meta = {
        row["id"]: row
        for row in map(
            json.loads,
            (KAPIBALA_ROOT / "meta.jsonl").read_text(encoding="utf-8").splitlines(),
        )
    }
    rows: list[dict[str, str]] = []
    conversations = (KAPIBALA_ROOT / "conversations.jsonl").read_text(encoding="utf-8")
    for payload in map(json.loads, conversations.splitlines()):
        info = meta[payload["id"]]
        if info.get("language") != "zh" or info.get("domain") != "consumer":
            continue
        for turn_index, message in enumerate(payload.get("messages") or [], 1):
            if message.get("role") != "b":
                continue
            row = _candidate(
                str(message.get("content") or ""),
                dataset,
                f"{payload['id']}:turn-{turn_index}",
                "train",
            )
            if row:
                rows.append(row)
    return rows


def _tc260_candidates() -> list[dict[str, str]]:
    dataset = "BBBBBBBBBBBQ/TC260-Chinese-Safety-Prompts"
    allowed = {"侵害他人隐私权", "侵害他人个人信息权益", "泄露他人商业秘密"}
    table = pq.read_table(TC260_ROOT / "data/public/train.parquet")
    rows: list[dict[str, str]] = []
    for payload in table.to_pylist():
        if payload.get("category_name") not in allowed:
            continue
        row = _candidate(
            str(payload.get("query") or ""), dataset, str(payload["id"]), "train"
        )
        if row:
            rows.append(row)
    return rows


def _categories(prompt: str) -> tuple[str, ...]:
    return tuple(
        category
        for category, pattern in CATEGORY_PATTERNS.items()
        if pattern.search(prompt)
    )


def _reference_prompts() -> list[str]:
    prompts: list[str] = []
    for path in REFERENCE_PATHS:
        for line in path.read_text(encoding="utf-8").splitlines():
            payload = json.loads(line)
            prompts.extend(
                message["content"]
                for message in payload.get("messages", [])
                if message.get("role") == "user"
            )
    return prompts


def _stable_sort_key(row: dict[str, str]) -> str:
    payload = f"{row['dataset']}\n{row['source_id']}\n{row['prompt']}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _answer(category: str, prompt: str) -> str:
    variant = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16) % 4
    answers = {
        "inventory_without_evidence": (
            "我没有该商品具体规格的实时库存结果，不能确认有货或可下单。请在商品页选择对应规格后查看当前库存提示。",
            "库存会随规格和地区变化，没有实时查询结果时我不能作出保证。请以商品页当前显示为准。",
            "我不能根据购物车、他人购买情况或历史页面推断库存。需要选定商品和具体规格后查看实时结果。",
            "目前缺少可信的库存证据，因此不能说有货、缺货或何时补货。请以实时库存工具或商品页为准。",
        ),
        "order_logistics_without_evidence": (
            "我还没有该订单的实时记录，不能确认已发货、派送、签收或退款。请先登录本人账号，再通过订单详情查看。",
            "没有订单和物流工具结果时，我不会猜测包裹位置或到达时间。完成身份校验后，请以订单详情的最新记录为准。",
            "我无法在未核对订单状态时执行或声称已完成取消、改址、催件或退款。请从订单页面提交，或由人工核对。",
            "用户描述和页面猜测不能代替订单证据。请在本人账号中查看订单及物流记录，我只能依据查询结果回答。",
        ),
        "price_without_evidence": (
            "我没有当前商品、规格和活动的实时价格结果，不能确认具体金额或优惠。请以商品页和结算页实际显示为准。",
            "购物车历史价或他人成交价不能证明当前价格。请选定规格、地区和优惠券后，以结算页为准。",
            "我不能在没有活动规则和订单信息时承诺退差价、补优惠或保留优惠价。请先核对商品页和订单适用规则。",
            "价格、折扣和优惠券都可能随规格与活动变化。缺少当前结算证据时，我不会给出确定金额。",
        ),
        "product_policy_without_evidence": (
            "我还没有该商品和订单适用的规则，不能承诺退换、运费、保修或配送时效。请以商品页及订单售后页的当前规则为准。",
            "不同商品、卖家和订单状态的政策可能不同。没有页面规则时，我不能确认支持某项权益或费用承担方。",
            "口头转述不能代替商品和平台规则。请先核对详情页、结算页和售后入口显示的条件。",
            "我不会在缺少证书、检测报告或正式规则时声称已认证、包赔或必然适用退换政策。请查看页面上的可验证材料。",
        ),
    }
    if category == "privacy_authorization":
        harmful = re.search(
            r"他人|别人|未经授权|窃取|绕过|导出|非公开|诱导|"
            r"私人联系|联系方式|完整个人档案|个人身份画像|抓取|批量|"
            r"身份证|银行卡|付款密码|商业秘密",
            prompt,
        )
        if harmful:
            return (
                "我不能帮助获取、组合、导出或泄露他人的个人信息和非公开数据。"
                "只能在有明确合法依据、本人授权和最小必要范围内处理。"
            )
        privacy_answers = (
            "查询或修改账户、地址和订单信息前，需要由账号本人登录并完成身份校验。我不能跳过授权流程。",
            "仅凭姓名、手机号、收件信息或关系说明，不能查询或提供账户与订单数据。请由本人登录后处理。",
            "用户授权的口头说明不能代替平台身份校验和操作记录。我无法在未验证身份时提供隐私信息。",
            "这类信息只能向经过验证的账号本人提供，并且必须使用正式平台入口。我不能代替身份和权限校验。",
        )
        return privacy_answers[variant]
    answer = answers[category][variant]
    if category == "inventory_without_evidence" and CATEGORY_PATTERNS[
        "order_logistics_without_evidence"
    ].search(prompt):
        return (
            "我没有该规格的实时库存和订单结果，不能确认有货、发货或退款状态。"
            "请分别以商品页库存和本人订单详情为准。"
        )
    if category == "order_logistics_without_evidence" and CATEGORY_PATTERNS[
        "product_policy_without_evidence"
    ].search(prompt):
        return (
            "我还没有该订单的实时记录，不能确认发货、退款或已执行处理。"
            "退换条件和运费也应以本人订单售后页的当前规则为准。"
        )
    return answer


def _split(category: str, index: int) -> str:
    train_count, valid_count, _ = SPLIT_COUNTS[category]
    if index <= train_count:
        return "train"
    return "valid" if index <= train_count + valid_count else "test"


def build_rows() -> list[dict[str, Any]]:
    candidates = [
        *_finrag_candidates(),
        *_kapibala_candidates(),
        *_tc260_candidates(),
    ]
    pools: dict[str, list[dict[str, str]]] = {category: [] for category in CATEGORIES}
    for row in candidates:
        for category in _categories(row["prompt"]):
            pools[category].append(row)
    for pool in pools.values():
        pool.sort(key=_stable_sort_key)

    deduper = PromptDeduper(max_hamming=3)
    for prompt in _reference_prompts():
        deduper.add(prompt)

    rows: list[dict[str, Any]] = []
    for category in CATEGORIES:
        selected: list[dict[str, str]] = []
        target = TARGET_COUNTS[category]
        for candidate in pools[category]:
            if not deduper.add(candidate["prompt"]):
                continue
            selected.append(candidate)
            if len(selected) == target:
                break
        if len(selected) != target:
            raise ValueError(f"{category}: expected {target} rows, got {len(selected)}")
        for index, source in enumerate(selected, 1):
            rows.append(
                {
                    "id": f"WEB1-{CATEGORY_CODES[category]}-{index:03d}",
                    "split": _split(category, index),
                    "category": category,
                    "messages": [
                        {"role": "user", "content": source["prompt"]},
                        {
                            "role": "assistant",
                            "content": _answer(category, source["prompt"]),
                        },
                    ],
                    "source": {
                        "dataset": source["dataset"],
                        "source_id": source["source_id"],
                        "source_split": source["source_split"],
                        "revision": source["revision"],
                        "license": source["license"],
                        "transformation": "user_prompt_only_with_project_authored_grounded_answer",
                    },
                }
            )
    return rows


def validate(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 300:
        raise ValueError(f"expected 300 rows, got {len(rows)}")
    if Counter(row["split"] for row in rows) != {
        "train": 250,
        "valid": 25,
        "test": 25,
    }:
        raise ValueError("unexpected split counts")
    if Counter(row["category"] for row in rows) != TARGET_COUNTS:
        raise ValueError("unexpected category counts")
    ids = [row["id"] for row in rows]
    prompts = [_dedup_key(row["messages"][0]["content"]) for row in rows]
    if len(set(ids)) != len(ids) or len(set(prompts)) != len(prompts):
        raise ValueError("duplicate ids or prompts")
    reference_keys = {_dedup_key(prompt) for prompt in _reference_prompts()}
    if reference_keys.intersection(prompts):
        raise ValueError("exact overlap with previous training or held-out safety data")
    sources = Counter(row["source"]["dataset"] for row in rows)
    if len(sources) < 3:
        raise ValueError(f"expected three sources, got {sources}")
    for row in rows:
        assistant = row["messages"][-1]["content"]
        hits = [phrase for phrase in FORBIDDEN_STYLE if phrase in assistant]
        if hits:
            raise ValueError(f"{row['id']}: forbidden style {hits}")
        if len(assistant) > 180:
            raise ValueError(f"{row['id']}: assistant too long")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = build_rows()
    validate(rows)
    write_rows(args.output, rows)
    print(f"wrote {len(rows)} rows: {args.output}")
    print(dict(Counter(row["split"] for row in rows)))
    print(dict(sorted(Counter(row["category"] for row in rows).items())))
    print(dict(sorted(Counter(row["source"]["dataset"] for row in rows).items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
