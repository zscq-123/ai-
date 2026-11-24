#!/usr/bin/env python3
"""Build a license-aware Chinese customer-service training corpus.

The builder keeps source files immutable and writes a deterministic, unified
JSONL corpus.  It deliberately separates SFT data from preference data and
does not ingest restricted/non-commercial datasets into the commercial-ready
output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


SYSTEM_PROMPT = (
    "你是中文电商客服助手。只根据用户提供的信息和可用证据回答；"
    "不要虚构订单状态、库存、价格、时效、退款、补偿或已经执行的操作。"
    "需要查询系统或调用工具时，应明确说明并索取完成查询所必需的最少信息。"
)
DATASET_VERSION = "customer-service-zh-v3"

SOURCE_INFO = {
    "finrag-grpo": {"license": "MIT", "priority": 100},
    "chinese-ambiguous-reference": {"license": "MIT", "priority": 90},
    "cvalues-comparison": {"license": "Apache-2.0", "priority": 80},
    "infinity-instruct-7m-core": {"license": "CC-BY-SA-4.0", "priority": 70},
}

COMMERCE_STRONG_RE = re.compile(
    r"客服|订单|订单号|退款|退货|换货|退换|售后|发货|物流|快递|快递单号|配送|"
    r"包裹|收货|收件|运费|到货|店铺|商家|支付|付款|优惠券|发票|保修|质保|"
    r"投诉|补发|价保|预售|缺货|下单|购物车|商品"
)
DIRECT_SUPPORT_RE = re.compile(
    r"(?:^|[。！？\n]\s*)(?:你好|您好|请问|麻烦|帮我|请帮|怎么|为什么|能否|"
    r"可不可以|我(?:的|在|买|下单|想|需要|刚|已经|还|要|无法|没有|没))"
)
META_TASK_RE = re.compile(
    r"基于以下角色|角色信息|完成一段对话|生成.{0,12}(?:对话|客服|回答)|"
    r"写.{0,12}(?:对话|客服|回答)|创建.{0,12}(?:对话|客服|回答)|"
    r"模拟.{0,12}(?:对话|客服|回答)|以下是一段.{0,8}对话|"
    r"对话内容[:：]|请根据下面|根据输入内容|输出对应标题|判断事件类型|"
    r"改写下面|翻译|переведи|阅读下面的文章|完成各题|常见问题主题最相关|"
    r"数据分析师.*评估|研究摘要|RFP|写一篇|给出一句总结"
)
NON_SUPPORT_RE = re.compile(
    r"单选题|选择题|下列说法|正确的是|不正确的是|未知数|方程|证明|答案是|"
    r"题目[:：]|每.{0,20}(?:美元|元).{0,30}(?:总共|总金额)|"
    r"法院|诉讼|法律制裁|诊断|药物|律师|股票|证券|投资|贷款|保险|博彩|赌博|"
    r"编程|代码|SQL"
)
UNSUPPORTED_ACTION_RE = re.compile(
    r"(?:我|我们|这边)?(?:已经|已|马上|立即|这就|现在)"
    r"(?:为您|帮您|给您|替您)?(?:联系|提交|申请|登记|安排|处理|修改|取消|"
    r"退款|补发|催促|催件|核对|查看|查询|确认|预约|通知|备注|保留|标注|"
    r"升级|加急|开通|关闭|冻结|改寄)|"
    r"(?:已为您|已经为您|我这边已)|"
    r"(?:我|我们|这边).{0,10}(?:帮您|为您|给您).{0,8}"
    r"(?:看|查|联系|提交|申请|登记|安排|处理|修改|取消|退款|补发|催|核对|"
    r"确认|预约|跟进)|"
    r"经核实|系统显示|我刚刚查|"
    r"(?:可|可以)(?:直接)?(?:为您)?(?:预约|办理|申请|取消|退款|换新|补发|"
    r"改价|改址|提交|联系|处理)|"
    r"预计.{0,18}(?:到账|送达|完成|处理|派送)|"
    r"(?:通常|大约|约)?\d+(?:-|至|~)\d*(?:小时|天|工作日)|"
    r"(?:补偿|赠送|赔付|承担).{0,18}(?:元|券|积分|运费|费用)|"
    r"(?:一定|保证).{0,18}(?:到账|送达|完成|解决)|"
    r"我(?:会|来)(?:全程|持续|马上|立即).{0,18}(?:跟进|处理|联系)"
)
PRODUCT_FACT_QUERY_RE = re.compile(
    r"这款|材质|尺码|含绒量|防水|库存|价格|规格|保质期|成分|型号"
)
GROUNDED_ANSWER_RE = re.compile(
    r"以.{0,12}为准|需要.{0,12}查询|请提供|详情页|无法确认|不能确认|"
    r"建议查看|可查看|请核对|需要核实"
)
SAFE_PROCESS_RE = re.compile(
    r"请提供|需要提供|建议您|您可以|可尝试|请先|如果|若|以.{0,12}为准|"
    r"无法保证|不能保证|需要核实|需要查询|待查询|按照.{0,12}流程|请联系|"
    r"请核对|可在.{0,12}(?:页面|订单|平台)|详情页|规则"
)
POLICY_ASSERTION_RE = re.compile(
    r"支持.{0,8}(?:退换|退款|价保)|可以.{0,8}(?:退换|退款|改址|换新)|"
    r"运费.{0,10}(?:我们|商家|平台).{0,4}承担|可叠加|免费上门|有价保服务"
)
FINRAG_QUERY_EXCLUDE_RE = re.compile(
    r"敏感肌|皮肤过敏|容易泛红|面霜|护肤|药品|保健品|诊断|处方|"
    r"推荐.{0,12}(?:商品|产品|鞋|服装|品牌)|有什么推荐"
)
SAFETY_COMMERCE_RE = re.compile(
    r"订单|商品|商家|店铺|退款|退货|支付|付款|银行卡|信用卡|优惠券|发票|"
    r"物流|快递|刷单|套现|假货|盗刷|账户余额|购物"
)
SAFETY_RISK_RE = re.compile(
    r"骗|欺诈|诈骗|盗|偷|伪造|破解|绕过|攻击|恶意|洗钱|刷单|套现|操纵|"
    r"泄露|窃取|冒充|骚扰|威胁|违法|违规|灰产|黑产"
)
REFUSAL_RE = re.compile(r"不能|无法|不会|不应|不应该|违法|非法|不道德|反对|拒绝|不要")

EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ID_CARD_RE = re.compile(r"(?<![A-Za-z0-9])\d{17}[0-9Xx](?![A-Za-z0-9])")
ORDER_ID_RE = re.compile(
    r"(订单号|快递单号|运单号|退款申请号)\s*[：:#-]?\s*[A-Za-z0-9_-]{6,}", re.I
)


@dataclass(frozen=True)
class Candidate:
    messages: list[dict[str, str]]
    dataset: str
    source_id: str
    source_split: str
    task: str


class PromptDeduper:
    """Exact plus conservative SimHash near-deduplication on user messages."""

    def __init__(self, max_hamming: int = 3) -> None:
        self.max_hamming = max_hamming
        self.exact: set[str] = set()
        self.hashes: list[int] = []
        self.buckets: dict[tuple[int, int], list[int]] = defaultdict(list)

    def add(self, text: str) -> str | None:
        key = dedup_normalize(text)
        if key in self.exact:
            return "duplicate_exact_user"
        self.exact.add(key)
        if len(key) < 12:
            return None
        value = simhash64(key)
        candidates: set[int] = set()
        for band in range(4):
            part = (value >> (band * 16)) & 0xFFFF
            candidates.update(self.buckets[(band, part)])
        for index in candidates:
            if (value ^ self.hashes[index]).bit_count() <= self.max_hamming:
                return "duplicate_near_user"
        index = len(self.hashes)
        self.hashes.append(value)
        for band in range(4):
            part = (value >> (band * 16)) & 0xFFFF
            self.buckets[(band, part)].append(index)
        return None


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    return text.strip()


def strip_outer_quotes(text: str) -> str:
    text = normalize_text(text)
    pairs = [("“", "”"), ('"', '"'), ("‘", "’"), ("'", "'")]
    for left, right in pairs:
        if len(text) >= 2 and text.startswith(left) and text.endswith(right):
            return text[len(left) : -len(right)].strip()
    return text


def redact_pii(text: str) -> tuple[str, int]:
    text = normalize_text(text)
    total = 0
    for pattern, replacement in (
        (EMAIL_RE, "<EMAIL>"),
        (PHONE_RE, "<PHONE>"),
        (ID_CARD_RE, "<ID_CARD>"),
    ):
        text, count = pattern.subn(replacement, text)
        total += count

    def replace_order(match: re.Match[str]) -> str:
        return f"{match.group(1)}：<ORDER_ID>"

    text, count = ORDER_ID_RE.subn(replace_order, text)
    return text, total + count


def dedup_normalize(text: str) -> str:
    text = normalize_text(text).lower()
    text = EMAIL_RE.sub("<email>", text)
    text = PHONE_RE.sub("<phone>", text)
    text = ID_CARD_RE.sub("<id>", text)
    text = re.sub(r"[A-Za-z0-9_-]{6,}", "<token>", text)
    text = re.sub(r"\d+", "<num>", text)
    return re.sub(r"[^\w\u3400-\u9fff<>]+", "", text)


def simhash64(text: str) -> int:
    compact = dedup_normalize(text)
    if len(compact) <= 3:
        features = [compact]
    else:
        features = [compact[index : index + 3] for index in range(len(compact) - 2)]
    counts = Counter(features)
    vector = [0] * 64
    for feature, weight in counts.items():
        value = int.from_bytes(hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest(), "big")
        for bit in range(64):
            vector[bit] += weight if value & (1 << bit) else -weight
    result = 0
    for bit, score in enumerate(vector):
        if score >= 0:
            result |= 1 << bit
    return result


def chinese_ratio(text: str) -> float:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return 0.0
    return len(re.findall(r"[\u3400-\u9fff]", compact)) / len(compact)


def merge_messages(messages: Sequence[dict[str, Any]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    role_map = {"human": "user", "gpt": "assistant", "customer": "user"}
    for item in messages:
        role = role_map.get(str(item.get("role") or item.get("from") or "").lower())
        role = role or str(item.get("role") or item.get("from") or "").lower()
        if role not in {"system", "user", "assistant"}:
            continue
        content = normalize_text(item.get("content") if "content" in item else item.get("value"))
        if not content:
            continue
        if merged and merged[-1]["role"] == role:
            merged[-1]["content"] += "\n" + content
        else:
            merged.append({"role": role, "content": content})
    return merged


def normalize_messages(messages: Sequence[dict[str, Any]], system_context: str = "") -> tuple[list[dict[str, str]], int] | None:
    body = merge_messages(messages)
    while body and body[0]["role"] != "user":
        body.pop(0)
    while body and body[-1]["role"] != "assistant":
        body.pop()
    if not body or not any(item["role"] == "user" for item in body):
        return None
    if len(body) > 24:
        return None
    total_chars = sum(len(item["content"]) for item in body)
    if total_chars < 8 or total_chars > 10_000:
        return None
    system = SYSTEM_PROMPT
    if system_context:
        system += "\n场景信息：" + normalize_text(system_context)
    normalized = [{"role": "system", "content": system}, *body]
    redactions = 0
    for item in normalized:
        item["content"], count = redact_pii(item["content"])
        redactions += count
    if chinese_ratio("\n".join(item["content"] for item in body)) < 0.15:
        return None
    return normalized, redactions


def user_text(messages: Sequence[dict[str, str]]) -> str:
    return "\n".join(item["content"] for item in messages if item["role"] == "user")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(dataset: str, messages: Sequence[dict[str, str]]) -> str:
    payload = f"{dataset}\n{canonical_json(messages)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def grounding_penalty(question: str, answer: str) -> int:
    penalty = len(UNSUPPORTED_ACTION_RE.findall(answer))
    if PRODUCT_FACT_QUERY_RE.search(question) and not GROUNDED_ANSWER_RE.search(answer):
        if re.search(r"\d|偏大|偏小|防水|含绒|有货|现货|材质是|价格是", answer):
            penalty += 1
    return penalty


def grounding_score(question: str, answer: str) -> int:
    """Lower is safer: penalize unverifiable actions/facts, reward bounded process guidance."""
    score = 3 * len(UNSUPPORTED_ACTION_RE.findall(answer))
    if PRODUCT_FACT_QUERY_RE.search(question) and not GROUNDED_ANSWER_RE.search(answer):
        if re.search(r"\d|偏大|偏小|防水|含绒|有货|现货|库存|材质|型号|价格(?:是|为)", answer):
            score += 3
    if POLICY_ASSERTION_RE.search(answer) and not GROUNDED_ANSWER_RE.search(answer):
        score += 2
    if SAFE_PROCESS_RE.search(answer):
        score -= 2
    if re.search(r"如果|若|可能|视.{0,8}情况", answer):
        score -= 1
    return score


def parse_finrag_prompt(text: str) -> tuple[str, str, str] | None:
    pattern = re.compile(
        r"\[客户问题\]\s*(.*?)\s*"
        r"\[客服A的回答开始\]\s*(.*?)\s*\[客服A的回答结束\]\s*"
        r"\[客服B的回答开始\]\s*(.*?)\s*\[客服B的回答结束\]",
        re.S,
    )
    match = pattern.search(text)
    if not match:
        return None
    return tuple(normalize_text(part) for part in match.groups())  # type: ignore[return-value]


def iter_finrag(data_root: Path, stats: Counter[str], review: list[dict[str, Any]]) -> tuple[list[Candidate], list[dict[str, Any]]]:
    candidates: list[Candidate] = []
    preferences: list[dict[str, Any]] = []
    for split in ("train", "test"):
        path = data_root / "raw/finrag-grpo/datasets" / f"{split}_zh.jsonl"
        with path.open(encoding="utf-8") as handle:
            for row_number, line in enumerate(handle, 1):
                stats["finrag_seen"] += 1
                row = json.loads(line)
                contexts = row.get("context_messages") or []
                if not contexts:
                    stats["finrag_missing_context"] += 1
                    continue
                parsed = parse_finrag_prompt(str(contexts[0].get("content") or ""))
                if not parsed:
                    stats["finrag_parse_failed"] += 1
                    continue
                question, answer_a, answer_b = parsed
                if FINRAG_QUERY_EXCLUDE_RE.search(question):
                    stats["finrag_high_risk_or_catalog_recommendation"] += 1
                    continue
                winner = row.get("winner")
                if winner == "model_a":
                    original_chosen, original_rejected = answer_a, answer_b
                elif winner == "model_b":
                    original_chosen, original_rejected = answer_b, answer_a
                else:
                    stats["finrag_unknown_winner"] += 1
                    continue
                score_a = grounding_score(question, answer_a)
                score_b = grounding_score(question, answer_b)
                if score_a < score_b:
                    chosen, rejected = answer_a, answer_b
                elif score_b < score_a:
                    chosen, rejected = answer_b, answer_a
                else:
                    chosen, rejected = original_chosen, original_rejected
                chosen_score = min(score_a, score_b)
                rejected_score = max(score_a, score_b)
                if chosen != original_chosen:
                    stats["finrag_grounding_override"] += 1
                if chosen_score > 0 or not SAFE_PROCESS_RE.search(chosen):
                    stats["finrag_no_grounded_answer"] += 1
                    if len(review) < 500:
                        review.append(
                            {
                                "reason": "no_grounded_answer",
                                "dataset": "finrag-grpo",
                                "source_id": f"{split}:{row_number}",
                                "question": redact_pii(question)[0],
                                "answer": redact_pii(chosen)[0],
                                "grounding_score": chosen_score,
                            }
                        )
                    continue
                normalized = normalize_messages(
                    [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": chosen},
                    ]
                )
                if not normalized:
                    stats["finrag_invalid_messages"] += 1
                    continue
                messages, _ = normalized
                source_id = f"{split}:{row_number}"
                candidates.append(
                    Candidate(messages, "finrag-grpo", source_id, split, "customer_service")
                )
                redacted_question, _ = redact_pii(question)
                redacted_chosen, _ = redact_pii(chosen)
                redacted_rejected, _ = redact_pii(rejected)
                pref_id = hashlib.sha256(
                    f"finrag-grpo\n{redacted_question}\n{redacted_chosen}\n{redacted_rejected}".encode("utf-8")
                ).hexdigest()
                preferences.append(
                    {
                        "id": pref_id,
                        "prompt": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": redacted_question},
                        ],
                        "chosen": [{"role": "assistant", "content": redacted_chosen}],
                        "rejected": [{"role": "assistant", "content": redacted_rejected}],
                        "source": {
                            "dataset": "finrag-grpo",
                            "source_id": source_id,
                            "split": split,
                            "license": SOURCE_INFO["finrag-grpo"]["license"],
                        },
                        "curation": {
                            "selection": "grounding_score" if chosen != original_chosen else "source_preference",
                            "chosen_grounding_score": chosen_score,
                            "rejected_grounding_score": rejected_score,
                        },
                    }
                )
    return candidates, preferences


def speaker_role(speaker: str) -> str:
    if re.search(r"顾客|客户|消费者|客人|买家|用户", speaker):
        return "user"
    return "assistant"


def iter_ambiguous_reference(data_root: Path, stats: Counter[str]) -> list[Candidate]:
    path = data_root / "raw/chinese-ambiguous-reference/All Conversation.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    candidates: list[Candidate] = []
    for index, row in enumerate(rows):
        stats["ambiguous_seen"] += 1
        turns: list[dict[str, str]] = []
        for raw_turn in row.get("total_split") or []:
            match = re.match(r"\s*([^：:]{1,24})[：:]\s*(.*)", str(raw_turn), re.S)
            if not match:
                continue
            speaker, content = match.groups()
            turns.append({"role": speaker_role(speaker.strip()), "content": strip_outer_quotes(content)})
        normalized = normalize_messages(turns, str(row.get("shopBackground") or ""))
        if not normalized:
            stats["ambiguous_invalid_messages"] += 1
            continue
        messages, _ = normalized
        candidates.append(
            Candidate(messages, "chinese-ambiguous-reference", str(index), "all", "clarification")
        )
    return candidates


def infinity_filter_reason(question: str, answer: str) -> str | None:
    if not COMMERCE_STRONG_RE.search(question):
        return "infinity_not_commerce"
    if not DIRECT_SUPPORT_RE.search(question):
        return "infinity_not_direct_support"
    if META_TASK_RE.search(question):
        return "infinity_meta_task"
    if NON_SUPPORT_RE.search(question):
        return "infinity_non_support_task"
    if len(question) < 4 or len(question) > 2_000 or len(answer) < 4 or len(answer) > 5_000:
        return "infinity_length"
    if grounding_penalty(question, answer):
        return "infinity_unsupported_claim"
    return None


def iter_infinity(data_root: Path, stats: Counter[str], review: list[dict[str, Any]]) -> list[Candidate]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - environment check
        raise RuntimeError("pyarrow is required to read Infinity-Instruct Parquet files") from exc

    root = data_root / "raw/infinity-instruct/7M_core"
    candidates: list[Candidate] = []
    for path in sorted(root.glob("*.parquet")):
        parquet = pq.ParquetFile(path)
        columns = ["id", "conversations", "langdetect", "source"]
        for batch in parquet.iter_batches(batch_size=4_096, columns=columns):
            for row in batch.to_pylist():
                stats["infinity_seen"] += 1
                if not str(row.get("langdetect") or "").lower().startswith("zh"):
                    stats["infinity_non_chinese"] += 1
                    continue
                raw_messages = row.get("conversations") or []
                human_text = "\n".join(
                    normalize_text(item.get("value"))
                    for item in raw_messages
                    if item.get("from") == "human"
                )
                assistant_text = "\n".join(
                    normalize_text(item.get("value"))
                    for item in raw_messages
                    if item.get("from") == "gpt"
                )
                reason = infinity_filter_reason(human_text, assistant_text)
                if reason:
                    stats[reason] += 1
                    if reason == "infinity_unsupported_claim" and len(review) < 500:
                        review.append(
                            {
                                "reason": "unsupported_operational_claim",
                                "dataset": "infinity-instruct-7m-core",
                                "source_id": str(row.get("id")),
                                "question": redact_pii(human_text)[0],
                                "answer": redact_pii(assistant_text)[0],
                            }
                        )
                    continue
                normalized = normalize_messages(raw_messages)
                if not normalized:
                    stats["infinity_invalid_messages"] += 1
                    continue
                messages, _ = normalized
                candidates.append(
                    Candidate(
                        messages,
                        "infinity-instruct-7m-core",
                        str(row.get("id")),
                        "7M_core",
                        "customer_service",
                    )
                )
    return candidates


def iter_cvalues_safety(data_root: Path, stats: Counter[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    for split in ("train", "test"):
        path = data_root / "raw/cvalues-comparison" / f"{split}.jsonl"
        with path.open(encoding="utf-8") as handle:
            for row_number, line in enumerate(handle, 1):
                stats["cvalues_seen"] += 1
                row = json.loads(line)
                prompt = normalize_text(row.get("prompt"))
                answer = normalize_text(row.get("pos_resp"))
                if not (SAFETY_COMMERCE_RE.search(prompt) and SAFETY_RISK_RE.search(prompt)):
                    stats["cvalues_not_commerce_safety"] += 1
                    continue
                if not REFUSAL_RE.search(answer):
                    stats["cvalues_missing_refusal"] += 1
                    continue
                normalized = normalize_messages(
                    [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": answer},
                    ]
                )
                if not normalized:
                    stats["cvalues_invalid_messages"] += 1
                    continue
                messages, _ = normalized
                candidates.append(
                    Candidate(
                        messages,
                        "cvalues-comparison",
                        f"{split}:{row_number}",
                        split,
                        "commerce_safety",
                    )
                )
    return candidates


def build_sft_record(candidate: Candidate) -> dict[str, Any]:
    record_id = stable_id(candidate.dataset, candidate.messages)
    return {
        "id": record_id,
        "messages": candidate.messages,
        "language": "zh-CN",
        "task": candidate.task,
        "source": {
            "dataset": candidate.dataset,
            "source_id": candidate.source_id,
            "split": candidate.source_split,
            "license": SOURCE_INFO[candidate.dataset]["license"],
        },
    }


def split_name(record_id: str) -> str:
    bucket = int(record_id[:8], 16) % 100
    if bucket == 99:
        return "test"
    if bucket == 98:
        return "validation"
    return "train"


def dedupe_candidates(candidates: Iterable[Candidate], stats: Counter[str]) -> list[dict[str, Any]]:
    deduper = PromptDeduper(max_hamming=3)
    ordered = sorted(
        candidates,
        key=lambda item: (-int(SOURCE_INFO[item.dataset]["priority"]), item.dataset, item.source_id),
    )
    records: list[dict[str, Any]] = []
    for candidate in ordered:
        reason = deduper.add(user_text(candidate.messages))
        if reason:
            stats[reason] += 1
            continue
        record = build_sft_record(candidate)
        records.append(record)
        stats[f"included_{candidate.dataset}"] += 1
        stats[f"included_task_{candidate.task}"] += 1
    return sorted(records, key=lambda row: row["id"])


def dedupe_preferences(records: Iterable[dict[str, Any]], stats: Counter[str]) -> list[dict[str, Any]]:
    deduper = PromptDeduper(max_hamming=3)
    output: list[dict[str, Any]] = []
    for row in sorted(records, key=lambda item: item["id"]):
        prompt = "\n".join(item["content"] for item in row["prompt"] if item["role"] == "user")
        reason = deduper.add(prompt)
        if reason:
            stats[f"preference_{reason}"] += 1
            continue
        output.append(row)
    return output


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sft_file(path: Path) -> tuple[int, set[str]]:
    count = 0
    ids: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            record_id = row["id"]
            if record_id in ids:
                raise ValueError(f"duplicate id in {path}:{line_number}: {record_id}")
            ids.add(record_id)
            messages = row["messages"]
            if not messages or messages[0]["role"] != "system":
                raise ValueError(f"missing system message in {path}:{line_number}")
            if messages[-1]["role"] != "assistant":
                raise ValueError(f"record does not end with assistant in {path}:{line_number}")
            if not any(item["role"] == "user" for item in messages):
                raise ValueError(f"record has no user message in {path}:{line_number}")
            count += 1
    return count, ids


def dataset_card(report: dict[str, Any]) -> str:
    split_counts = report["sft_split_counts"]
    source_counts = report["sft_source_counts"]
    task_counts = report["sft_task_counts"]
    return f"""# Chinese Customer Service Training Corpus v3

Generated: {report['generated_at']}

Format: UTF-8 JSONL, one record per line

## Purpose

High-confidence Chinese ecommerce customer-service SFT data for local
LoRA/QLoRA experiments. Every SFT record uses a `messages` array with `system`,
`user`, and `assistant` roles. Preference candidates are quarantined and are not
approved for training.

## Selected versions

- Infinity-Instruct: `7M_core` was the only candidate version audited, avoiding
  overlap with `0625`, `3M`, `7M`, domain views, and `Gen`. Its surviving
  keyword matches failed the stricter task-fit review, so no Infinity rows are
  present in the final SFT files.
- FinRAG-GRPO: excluded from training after second-pass sampling found that even
  the safer A/B answer can assert merchant-specific policy or backend state
  without evidence. Parsed and redacted candidates are retained under
  `quarantine/` for human rewriting only.
- Chinese-Ambiguous-Reference: grounded multi-turn clarification dialogues.
- CValues-Comparison: commerce/security refusal subset only.

## Counts

- SFT train: {split_counts['train']}
- SFT validation: {split_counts['validation']}
- SFT test: {split_counts['test']}
- Preference total: {report['preference_total']}
- By source: `{json.dumps(source_counts, ensure_ascii=False, sort_keys=True)}`
- By task: `{json.dumps(task_counts, ensure_ascii=False, sort_keys=True)}`

## Licensing

Records retain per-example source and license metadata. The approved SFT corpus
contains MIT and Apache-2.0 material. Infinity-Instruct data is not present in
the approved SFT files.

Restricted/non-commercial/unclear-license sources are not included. English
ABCD, tau-bench, ToolACE, and xLAM remain evaluation/tool references rather
than Chinese SFT data. Safety-Prompts is excluded because its own documentation
warns that some responses may be unsafe and it requires separate review.

## Quality boundaries

The filters are deterministic heuristics, not human certification. Review the
validation/test sets and `review_candidates.jsonl` before training. Production
behavior still requires tool-grounded evaluation for order, logistics, catalog,
refund, compensation, privacy, and human-handoff scenarios.
"""


def build(data_root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=output_dir.name + ".tmp-", dir=output_dir.parent))
    stats: Counter[str] = Counter()
    review: list[dict[str, Any]] = []

    try:
        finrag, preferences = iter_finrag(data_root, stats, review)
        candidates: list[Candidate] = []
        stats["finrag_quality_gate_excluded"] += len(finrag)
        candidates.extend(iter_ambiguous_reference(data_root, stats))
        candidates.extend(iter_cvalues_safety(data_root, stats))
        infinity_candidates = iter_infinity(data_root, stats, review)
        stats["infinity_quality_gate_excluded"] += len(infinity_candidates)

        sft_records = dedupe_candidates(candidates, stats)
        quarantine_preferences = dedupe_preferences(preferences, stats)
        preference_records: list[dict[str, Any]] = []

        split_rows: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
        for row in sft_records:
            split_rows[split_name(row["id"])].append(row)

        pref_split_rows: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
        for row in preference_records:
            pref_split_rows[split_name(row["id"])].append(row)

        sft_dir = temp_dir / "sft"
        preference_dir = temp_dir / "preference"
        quarantine_dir = temp_dir / "quarantine"
        sft_dir.mkdir()
        preference_dir.mkdir()
        quarantine_dir.mkdir()
        for split, rows in split_rows.items():
            write_jsonl(sft_dir / f"{split}.jsonl", rows)
        for split, rows in pref_split_rows.items():
            write_jsonl(preference_dir / f"{split}.jsonl", rows)
        for row in quarantine_preferences:
            row["training_approved"] = False
            row["quarantine_reason"] = "merchant_policy_or_backend_state_requires_human_rewrite"
        write_jsonl(quarantine_dir / "finrag_grounding_review.jsonl", quarantine_preferences)
        write_jsonl(temp_dir / "review_candidates.jsonl", review)

        all_ids: set[str] = set()
        validated_counts: dict[str, int] = {}
        for split in ("train", "validation", "test"):
            count, ids = validate_sft_file(sft_dir / f"{split}.jsonl")
            if all_ids.intersection(ids):
                raise ValueError(f"SFT ids overlap across splits: {split}")
            all_ids.update(ids)
            validated_counts[split] = count

        source_counts = Counter(row["source"]["dataset"] for row in sft_records)
        task_counts = Counter(row["task"] for row in sft_records)
        report: dict[str, Any] = {
            "version": DATASET_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "audited_infinity_variant": "7M_core",
            "infinity_included_in_sft": False,
            "sft_total": len(sft_records),
            "sft_split_counts": validated_counts,
            "sft_source_counts": dict(sorted(source_counts.items())),
            "sft_task_counts": dict(sorted(task_counts.items())),
            "preference_total": len(preference_records),
            "preference_split_counts": {key: len(value) for key, value in pref_split_rows.items()},
            "quarantine_finrag_preferences": len(quarantine_preferences),
            "review_candidates": len(review),
            "filter_and_dedup_stats": dict(sorted(stats.items())),
            "excluded_source_groups": {
                "overlapping_infinity_versions": ["0625", "3M", "7M", "7M_domains", "Gen"],
                "non_chinese_references": ["ABCD", "tau-bench", "ToolACE", "xLAM"],
                "requires_manual_safety_review": ["Safety-Prompts"],
                "restricted_or_unclear_license": [
                    "E-commerce Dialogue Corpus",
                    "APIGen-MT-5k",
                    "PKU-SafeRLHF",
                    "MHCH-DAMI",
                    "JDDC 2.1",
                ],
            },
        }
        (temp_dir / "processing-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (temp_dir / "README.md").write_text(dataset_card(report), encoding="utf-8")

        output_files = sorted(
            path for path in temp_dir.rglob("*") if path.is_file() and path.name != "checksums.sha256"
        )
        checksum_lines = [f"{file_sha256(path)}  {path.relative_to(temp_dir)}" for path in output_files]
        (temp_dir / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

        temp_dir.rename(output_dir)
        return report
    except Exception:
        # The temporary directory is intentionally retained for diagnostics;
        # it never replaces or mutates source data.
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/datasets"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/datasets/processed/customer-service-zh-v3"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build(args.data_root.resolve(), args.output_dir.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
