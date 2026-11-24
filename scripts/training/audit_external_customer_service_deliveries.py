#!/usr/bin/env python3
"""Audit external customer-service training and evaluation deliveries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from docx import Document

SPACE_PUNCT_RE = re.compile(r"[^0-9A-Za-z\u3400-\u9fff]+")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ID_CARD_RE = re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)")
BANK_CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TEST_HEADER_RE = re.compile(r"^(TEST-\d{3})\b")


@dataclass(frozen=True)
class Record:
    dataset: str
    record_id: str
    pair_id: str
    prompt: str
    answer: str
    split: str
    license: str
    source_dataset: str
    source_record_id: str
    review_status: str
    collector: str
    raw: dict[str, Any] | None = None


def normalize(text: str) -> str:
    return SPACE_PUNCT_RE.sub("", text).lower()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"{path}:{line_number}: JSONL row is not an object")
            rows.append(value)
    return rows


def stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def last_message(messages: Any, role: str) -> str:
    if not isinstance(messages, list):
        return ""
    for item in reversed(messages):
        if isinstance(item, dict) and item.get("role") == role:
            return str(item.get("content") or "")
    return ""


def parse_pipe_record(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    parts = [part.strip() for part in text.split("｜")]
    fields["record_id"] = parts[0]
    for part in parts[1:]:
        if part.startswith("配对 "):
            fields["pair_id"] = part.removeprefix("配对 ").strip()
        elif "：" in part:
            key, value = part.split("：", 1)
            fields[key.strip()] = value.strip()
    return fields


def parse_inventory_docx(path: Path) -> list[Record]:
    doc = Document(path)
    records: list[Record] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text.startswith("INV-"):
            continue
        row = parse_pipe_record(text)
        records.append(
            Record(
                dataset="inventory_docx_20000",
                record_id=row.get("record_id", ""),
                pair_id=row.get("pair_id", ""),
                prompt=row.get("用户", ""),
                answer=row.get("正确行为", ""),
                split="candidate",
                license=row.get("许可", ""),
                source_dataset=row.get("数据集", ""),
                source_record_id=row.get("原始记录", ""),
                review_status="待人工审核",
                collector=row.get("收集者", ""),
            )
        )
    return records


def parse_test_docx(path: Path) -> dict[str, dict[str, str]]:
    doc = Document(path)
    results: dict[str, dict[str, str]] = {}
    current_id = ""
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        match = TEST_HEADER_RE.match(text)
        if match:
            current_id = match.group(1)
            results[current_id] = {"header": text}
            continue
        if current_id and "：" in text:
            key, value = text.split("：", 1)
            results[current_id][key.strip()] = value.strip()
    return results


def load_training_records(root: Path, inventory_docx: Path, project_root: Path) -> list[Record]:
    records: list[Record] = []

    agentic_path = root / "agentic_safety_eval_20000/agentic_safety_eval_20000/data/agentic_safety_20000.jsonl"
    for row in read_jsonl(agentic_path):
        provenance = row.get("provenance") or {}
        behavior = row.get("correct_behavior") or {}
        records.append(
            Record(
                dataset="agentic_safety_20000",
                record_id=str(row.get("record_id") or ""),
                pair_id=str(row.get("paired_case_id") or ""),
                prompt=str(row.get("user_query") or ""),
                answer=str(behavior.get("reference_response") or ""),
                split=str(row.get("split") or ""),
                license=str(provenance.get("license") or ""),
                source_dataset=str(provenance.get("source_dataset_name") or ""),
                source_record_id=str(provenance.get("original_record_id") or ""),
                review_status="package_validator_pass",
                collector=str(provenance.get("collector") or ""),
                raw=row,
            )
        )

    auth_path = root / "授权隐私人工接管_20000条交付包/授权隐私人工接管_20000条.jsonl"
    for row in read_jsonl(auth_path):
        records.append(
            Record(
                dataset="auth_privacy_handoff_20000",
                record_id=str(row.get("unique_id") or ""),
                pair_id=str(row.get("paired_case_id") or ""),
                prompt=str(row.get("user_original_question") or ""),
                answer="",
                split=str(row.get("split") or ""),
                license=str(row.get("license") or ""),
                source_dataset=str(row.get("dataset_name") or ""),
                source_record_id=str(row.get("source_original_record_id") or ""),
                review_status="package_validator_pass_no_sft_answer",
                collector=str(row.get("collector") or ""),
                raw=row,
            )
        )

    category_path = root / "第5类_商品与政策未知/第5类_商品与政策未知/data/C5/C5_category5_20000.jsonl"
    for row in read_jsonl(category_path):
        records.append(
            Record(
                dataset="product_policy_unknown_20000",
                record_id=str(row.get("id") or ""),
                pair_id=str(row.get("paired_case_id") or ""),
                prompt=str(row.get("user_query") or ""),
                answer=str(row.get("reference_response") or ""),
                split=str(row.get("split") or ""),
                license=str(row.get("license") or ""),
                source_dataset=str(row.get("dataset_name") or ""),
                source_record_id=str(row.get("source_record_id") or ""),
                review_status=str(row.get("review_status") or ""),
                collector=str(row.get("collector") or ""),
                raw=row,
            )
        )

    order_path = root / "数据收集交付包/数据收集交付包/train/order_logistics_pairs.jsonl"
    for row in read_jsonl(order_path):
        provenance = row.get("provenance") or {}
        records.append(
            Record(
                dataset="order_logistics_pairs_20000",
                record_id=str(row.get("id") or ""),
                pair_id=str(row.get("paired_case_id") or ""),
                prompt=str(row.get("user_original_question") or ""),
                answer=str(row.get("assistant_gold_response") or ""),
                split="train",
                license=str(row.get("dataset_license") or ""),
                source_dataset=str(provenance.get("dataset_name") or ""),
                source_record_id=str(provenance.get("original_record_id") or ""),
                review_status="package_validator_pass",
                collector=str(row.get("collector") or ""),
                raw=row,
            )
        )

    records.extend(parse_inventory_docx(inventory_docx))

    v5_root = project_root / "data/training/customer-service-authored-v5"
    for split in ("train", "valid", "test"):
        path = v5_root / f"{split}.jsonl"
        if not path.exists():
            continue
        for index, row in enumerate(read_jsonl(path), 1):
            messages = row.get("messages") or []
            records.append(
                Record(
                    dataset="existing_customer_service_v5",
                    record_id=str(row.get("id") or f"{split}:{index}"),
                    pair_id="",
                    prompt=last_message(messages, "user"),
                    answer=last_message(messages, "assistant"),
                    split=split,
                    license="project_dataset",
                    source_dataset="existing_customer_service_v5",
                    source_record_id="",
                    review_status="existing",
                    collector="project",
                    raw=row,
                )
            )
    return records


def load_test_records(
    root: Path, question_docx: Path, answer_docx: Path, project_root: Path
) -> list[Record]:
    records: list[Record] = []

    auth_root = root / "授权隐私人工接管_300条测试题交付包"
    auth_keys = {
        row["test_id"]: row
        for row in read_jsonl(auth_root / "授权隐私人工接管_评分密钥_300条.jsonl")
    }
    for row in read_jsonl(auth_root / "授权隐私人工接管_盲测题_300条.jsonl"):
        key = auth_keys.get(row.get("test_id"), {})
        records.append(
            Record(
                dataset="auth_privacy_handoff_test_300",
                record_id=str(row.get("test_id") or ""),
                pair_id="",
                prompt=str(row.get("user_original_question") or ""),
                answer=str(key.get("gold_reference_response") or ""),
                split="independent_test",
                license=str(row.get("license") or ""),
                source_dataset=str(row.get("dataset_name") or ""),
                source_record_id=str(row.get("source_original_record_id") or ""),
                review_status="package_validator_pass",
                collector=str(row.get("collector") or ""),
                raw={"question": row, "key": key},
            )
        )

    independent_root = root / "独立测试集_300_完整整合包_含私有答案/independent_test_300"
    independent_keys = {
        row["test_id"]: row
        for row in read_jsonl(independent_root / "private/reference_answers_300.jsonl")
    }
    for row in read_jsonl(independent_root / "test/independent_test_300.jsonl"):
        key = independent_keys.get(row.get("test_id"), {})
        provenance = row.get("provenance") or {}
        records.append(
            Record(
                dataset="independent_full_test_300",
                record_id=str(row.get("test_id") or ""),
                pair_id="",
                prompt=str(row.get("question") or ""),
                answer=str(key.get("reference_answer") or ""),
                split="independent_test",
                license=str(provenance.get("license") or "synthetic_project_test"),
                source_dataset=str(provenance.get("scenario_source_family") or ""),
                source_record_id=str(provenance.get("scenario_source_id") or ""),
                review_status="single_author_cross_person_pending",
                collector=str(row.get("contributor_id") or ""),
                raw={"question": row, "key": key},
            )
        )

    order_root = root / "数据收集交付包/数据收集交付包/test"
    order_keys = {row["id"]: row for row in read_jsonl(order_root / "hidden_rubric.jsonl")}
    for row in read_jsonl(order_root / "questions.jsonl"):
        key = order_keys.get(row.get("id"), {})
        provenance = row.get("provenance") or {}
        conversation = row.get("conversation") or []
        prompt = "\n".join(
            str(item.get("content") or "")
            for item in conversation
            if isinstance(item, dict) and item.get("role") == "user"
        )
        records.append(
            Record(
                dataset="order_logistics_test_300",
                record_id=str(row.get("id") or ""),
                pair_id=str(row.get("fixture_id") or ""),
                prompt=prompt,
                answer=str(key.get("gold_response") or ""),
                split="independent_test",
                license=str(provenance.get("source_license") or ""),
                source_dataset=str(provenance.get("dataset_name") or ""),
                source_record_id=str(provenance.get("original_record_id") or ""),
                review_status="package_validator_pass_but_reaudit_required",
                collector="package",
                raw={"question": row, "key": key},
            )
        )

    docx_questions = parse_test_docx(question_docx)
    docx_answers = parse_test_docx(answer_docx)
    for test_id, question in sorted(docx_questions.items()):
        answer = docx_answers.get(test_id, {})
        records.append(
            Record(
                dataset="docx_independent_test_300",
                record_id=test_id,
                pair_id=question.get("配对编号", ""),
                prompt=question.get("用户原始问题", ""),
                answer=answer.get("标准答案", ""),
                split="independent_test",
                license="project_test_only",
                source_dataset="original_synthetic",
                source_record_id=test_id,
                review_status="provided",
                collector="Codex",
                raw={"question": question, "key": answer},
            )
        )

    core_path = project_root / "configs/training/customer_service_core_safety_200.jsonl"
    if core_path.exists():
        for row in read_jsonl(core_path):
            records.append(
                Record(
                    dataset="existing_core_safety_200",
                    record_id=str(row.get("id") or ""),
                    pair_id="",
                    prompt=last_message(row.get("messages"), "user"),
                    answer="",
                    split="held_out_test",
                    license="project_test",
                    source_dataset="project",
                    source_record_id="",
                    review_status="existing",
                    collector="project",
                    raw=row,
                )
            )
    return records


def profile_records(records: list[Record]) -> dict[str, Any]:
    ids = [record.record_id for record in records]
    prompts = [normalize(record.prompt) for record in records if record.prompt]
    answers = [normalize(record.answer) for record in records if record.answer]
    pair_counts = Counter(record.pair_id for record in records if record.pair_id)
    prompt_pairs: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.prompt:
            prompt_pairs[normalize(record.prompt)].add(record.pair_id or record.record_id)
    cross_pair_duplicates = sum(
        len(pair_ids) - 1 for pair_ids in prompt_pairs.values() if len(pair_ids) > 1
    )
    pii = Counter()
    pii_records = 0
    for record in records:
        text = f"{record.prompt}\n{record.answer}"
        hits = {
            "phone": len(PHONE_RE.findall(text)),
            "cn_id": len(ID_CARD_RE.findall(text)),
            "bank_card": len(BANK_CARD_RE.findall(text)),
            "email": len(EMAIL_RE.findall(text)),
        }
        if any(hits.values()):
            pii_records += 1
        pii.update(hits)
    return {
        "records": len(records),
        "unique_ids": len(set(ids)),
        "blank_ids": sum(not value for value in ids),
        "unique_normalized_prompts": len(set(prompts)),
        "blank_prompts": sum(not record.prompt.strip() for record in records),
        "records_with_answers": sum(bool(record.answer.strip()) for record in records),
        "unique_normalized_answers": len(set(answers)),
        "pair_groups": len(pair_counts),
        "pair_size_distribution": dict(sorted(Counter(pair_counts.values()).items())),
        "cross_pair_exact_prompt_duplicate_excess": cross_pair_duplicates,
        "split_distribution": dict(Counter(record.split for record in records)),
        "license_distribution": dict(Counter(record.license for record in records)),
        "source_distribution": dict(Counter(record.source_dataset for record in records)),
        "review_status_distribution": dict(Counter(record.review_status for record in records)),
        "collector_distribution": dict(Counter(record.collector for record in records)),
        "pii_pattern_hits": dict(pii),
        "records_with_pii_pattern_hits": pii_records,
    }


def source_key(record: Record) -> str:
    if not record.source_record_id:
        return ""
    return f"{normalize(record.source_dataset)}::{normalize(record.source_record_id)}"


def exact_overlap(train: list[Record], tests: list[Record]) -> dict[str, Any]:
    train_prompts: dict[str, list[Record]] = defaultdict(list)
    train_answers: dict[str, list[Record]] = defaultdict(list)
    train_sources: dict[str, list[Record]] = defaultdict(list)
    for record in train:
        if record.prompt:
            train_prompts[normalize(record.prompt)].append(record)
        if record.answer:
            train_answers[normalize(record.answer)].append(record)
        key = source_key(record)
        if key:
            train_sources[key].append(record)

    prompt_matches = []
    answer_matches = []
    source_matches = []
    for record in tests:
        prompt_key = normalize(record.prompt)
        if prompt_key in train_prompts:
            prompt_matches.append(
                {
                    "test_dataset": record.dataset,
                    "test_id": record.record_id,
                    "train_matches": [
                        {"dataset": item.dataset, "id": item.record_id}
                        for item in train_prompts[prompt_key][:20]
                    ],
                }
            )
        answer_key = normalize(record.answer)
        if answer_key and answer_key in train_answers:
            answer_matches.append(
                {
                    "test_dataset": record.dataset,
                    "test_id": record.record_id,
                    "train_matches": [
                        {"dataset": item.dataset, "id": item.record_id}
                        for item in train_answers[answer_key][:20]
                    ],
                }
            )
        key = source_key(record)
        if key and key in train_sources:
            source_matches.append(
                {
                    "test_dataset": record.dataset,
                    "test_id": record.record_id,
                    "source_key": key,
                    "train_matches": [
                        {"dataset": item.dataset, "id": item.record_id}
                        for item in train_sources[key][:20]
                    ],
                }
            )
    return {
        "exact_prompt_match_tests": len(prompt_matches),
        "exact_answer_match_tests": len(answer_matches),
        "source_record_match_tests": len(source_matches),
        "prompt_matches": prompt_matches[:200],
        "answer_matches": answer_matches[:200],
        "source_matches": source_matches[:200],
    }


def test_to_test_exact_overlap(tests: list[Record]) -> dict[str, Any]:
    prompts: dict[str, list[Record]] = defaultdict(list)
    answers: dict[str, list[Record]] = defaultdict(list)
    for record in tests:
        if record.prompt:
            prompts[normalize(record.prompt)].append(record)
        if record.answer:
            answers[normalize(record.answer)].append(record)
    prompt_groups = [
        items
        for items in prompts.values()
        if len({item.dataset for item in items}) > 1
    ]
    answer_groups = [
        items
        for items in answers.values()
        if len({item.dataset for item in items}) > 1
    ]
    return {
        "cross_dataset_exact_prompt_groups": len(prompt_groups),
        "cross_dataset_exact_answer_groups": len(answer_groups),
        "prompt_groups": [
            [{"dataset": item.dataset, "id": item.record_id} for item in group]
            for group in prompt_groups[:100]
        ],
        "answer_groups": [
            [{"dataset": item.dataset, "id": item.record_id} for item in group]
            for group in answer_groups[:100]
        ],
    }


def char_shingles(text: str, size: int = 4) -> frozenset[str]:
    value = normalize(text)
    if len(value) <= size:
        return frozenset({value}) if value else frozenset()
    return frozenset(value[index : index + size] for index in range(len(value) - size + 1))


MINHASH_SEEDS = (17, 104729, 130363, 155921, 196613, 262147, 314573, 393241)


@lru_cache(maxsize=200_000)
def shingles_cached(text: str) -> frozenset[str]:
    return char_shingles(text)


def minhash_signature(text: str) -> tuple[int, ...]:
    grams = shingles_cached(text)
    if not grams:
        return tuple(0 for _ in MINHASH_SEEDS)
    encoded = [gram.encode("utf-8") for gram in grams]
    return tuple(min(zlib.crc32(value, seed) for value in encoded) for seed in MINHASH_SEEDS)


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def near_overlap(train: list[Record], tests: list[Record], field: str) -> dict[str, Any]:
    usable_train = [record for record in train if getattr(record, field).strip()]
    usable_tests = [record for record in tests if getattr(record, field).strip()]
    index: dict[tuple[int, int], list[int]] = defaultdict(list)
    train_texts = [normalize(getattr(record, field)) for record in usable_train]
    for position, text in enumerate(train_texts):
        for band, value in enumerate(minhash_signature(text)):
            index[(band, value)].append(position)

    matches = []
    maxima: list[float] = []
    for test in usable_tests:
        text = normalize(getattr(test, field))
        candidates: set[int] = set()
        for band, value in enumerate(minhash_signature(text)):
            candidates.update(index.get((band, value), []))
        test_grams = shingles_cached(text)
        best_score = 0.0
        best_train: Record | None = None
        for position in candidates:
            score = jaccard(test_grams, shingles_cached(train_texts[position]))
            if score > best_score:
                best_score = score
                best_train = usable_train[position]
        maxima.append(best_score)
        if best_score >= 0.8 and best_train is not None:
            matches.append(
                {
                    "score": round(best_score, 6),
                    "test_dataset": test.dataset,
                    "test_id": test.record_id,
                    "train_dataset": best_train.dataset,
                    "train_id": best_train.record_id,
                }
            )
    maxima_sorted = sorted(maxima)
    p95 = 0.0
    if maxima_sorted:
        p95 = maxima_sorted[min(len(maxima_sorted) - 1, int(len(maxima_sorted) * 0.95))]
    return {
        "field": field,
        "train_records": len(usable_train),
        "test_records": len(usable_tests),
        "tests_at_or_above_0_80": sum(value >= 0.8 for value in maxima),
        "tests_at_or_above_0_85": sum(value >= 0.85 for value in maxima),
        "tests_at_or_above_0_90": sum(value >= 0.9 for value in maxima),
        "maximum": round(max(maxima, default=0.0), 6),
        "p95": round(p95, 6),
        "matches": sorted(matches, key=lambda item: item["score"], reverse=True)[:200],
        "method": "8-seed MinHash candidate retrieval plus exact normalized 4-character Jaccard",
    }


def cross_training_exact(records: list[Record]) -> dict[str, Any]:
    prompts: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        if record.prompt:
            prompts[normalize(record.prompt)].append(record)
    groups = [
        items
        for items in prompts.values()
        if len({item.dataset for item in items}) > 1
    ]
    return {
        "cross_dataset_exact_prompt_groups": len(groups),
        "records_in_groups": sum(len(group) for group in groups),
        "examples": [
            [{"dataset": item.dataset, "id": item.record_id} for item in group[:20]]
            for group in groups[:100]
        ],
    }


STATUS_LABELS = {
    "unshipped": "未发货",
    "in_transit": "运输中",
    "out_for_delivery": "派送中",
    "delivered": "已签收",
    "exception": "异常",
    "not_delivered": "伪造签收请求",
    "paid": "已支付",
    "captured": "已支付",
    "failed": "失败",
    "pending": "处理中",
    "none": "未退款",
    "available": "可售",
    "quarantined": "隔离",
}


def meaningful_tool_values(tool: str, result: dict[str, Any]) -> list[str]:
    if tool == "logistics.track":
        return [str(result.get("status_label") or "")]
    if tool == "orders.get":
        value = str(result.get("fulfillment_status") or "")
        return [STATUS_LABELS.get(value, value)]
    if tool == "inventory.lookup":
        return [str(result.get("available_qty")), STATUS_LABELS.get(str(result.get("inventory_state")), "")]
    if tool == "payments.get":
        values = [
            STATUS_LABELS.get(str(result.get("status")), str(result.get("status") or "")),
            STATUS_LABELS.get(
                str(result.get("refund_status")), str(result.get("refund_status") or "")
            ),
        ]
        return [value for value in values if value]
    return []


def audit_order_training(records: list[Record]) -> dict[str, Any]:
    selected = [record for record in records if record.dataset == "order_logistics_pairs_20000"]
    problems = Counter()
    by_domain_variant = Counter()
    examples: list[dict[str, Any]] = []
    shipping_terms = ("未发货", "运输中", "派送中", "已签收", "异常件", "伪造签收请求")
    for record in selected:
        row = record.raw or {}
        subtype = str(row.get("subtype") or "")
        domain = subtype.split("__", 1)[0]
        variant = subtype.rsplit("__", 1)[-1]
        gold = record.answer
        tool_returns = row.get("tool_returns") or {}
        results = tool_returns.get("results") or []
        if (
            variant == "no_evidence"
            and domain in {"inventory", "payment"}
            and any(term in gold for term in shipping_terms)
        ):
            problems["unrelated_shipping_state_in_no_evidence_gold"] += 1
            by_domain_variant[f"{domain}/{variant}"] += 1
            if len(examples) < 30:
                examples.append(
                    {
                        "id": record.record_id,
                        "problem": "unrelated_shipping_state",
                        "gold": gold,
                    }
                )
        if results and variant in {"trusted_evidence", "evidence_conflict"}:
            first = results[0]
            tool = str(first.get("tool") or "")
            result = first.get("result") or {}
            if tool and not tool.startswith(domain):
                problems["tool_domain_mismatch"] += 1
                by_domain_variant[f"{domain}/{variant}"] += 1
            expected = meaningful_tool_values(tool, result)
            if expected and not any(value and value in gold for value in expected):
                problems["gold_not_grounded_in_structured_result"] += 1
                by_domain_variant[f"{domain}/{variant}"] += 1
                if len(examples) < 30:
                    examples.append(
                        {
                            "id": record.record_id,
                            "problem": "gold_not_grounded",
                            "tool": tool,
                            "expected_values": expected,
                            "gold": gold,
                        }
                    )
            if domain in {"inventory", "payment"} and any(term in gold for term in shipping_terms):
                problems["cross_domain_shipping_gold"] += 1
                by_domain_variant[f"{domain}/{variant}"] += 1
    return {
        "records_checked": len(selected),
        "problem_counts": dict(problems),
        "problem_counts_by_domain_variant": dict(by_domain_variant),
        "examples": examples,
    }


def audit_order_test(records: list[Record]) -> dict[str, Any]:
    selected = [record for record in records if record.dataset == "order_logistics_test_300"]
    problems = Counter()
    by_tool = Counter()
    examples: list[dict[str, Any]] = []
    for record in selected:
        key = (record.raw or {}).get("key") or {}
        expected_call = key.get("expected_tool_call") or {}
        fixture = key.get("tool_fixture") or {}
        expected_tool = str(expected_call.get("tool") or "")
        fixture_tool = str(fixture.get("tool") or "")
        # Some cases deliberately provide the prerequisite authorization result
        # while the key asks the model to call the next business tool.  That is
        # a workflow sequence, not a fixture/key contradiction.
        if (
            expected_tool
            and fixture_tool
            and fixture_tool != "authorization.policy_check"
            and expected_tool != fixture_tool
        ):
            problems["expected_tool_fixture_tool_mismatch"] += 1
            by_tool[fixture_tool] += 1
        result = fixture.get("result") or {}
        expected_values = meaningful_tool_values(fixture_tool, result)
        if expected_values and not any(value and value in record.answer for value in expected_values):
            problems["gold_not_grounded_in_tool_fixture"] += 1
            by_tool[fixture_tool] += 1
            if len(examples) < 40:
                examples.append(
                    {
                        "id": record.record_id,
                        "tool": fixture_tool,
                        "expected_values": expected_values,
                        "gold": record.answer,
                    }
                )
    return {
        "records_checked": len(selected),
        "problem_counts": dict(problems),
        "problem_counts_by_tool": dict(by_tool),
        "examples": examples,
    }


def audit_independent_test(records: list[Record]) -> dict[str, Any]:
    selected = [record for record in records if record.dataset == "independent_full_test_300"]
    problems = Counter()
    examples: list[dict[str, Any]] = []
    for record in selected:
        payload = record.raw or {}
        question = payload.get("question") or {}
        key = payload.get("key") or {}
        behavior = key.get("expected_behavior") or {}
        action = str(behavior.get("action") or "")
        evidence = question.get("tool_evidence") or []
        current_trusted = [
            item
            for item in evidence
            if isinstance(item, dict)
            and item.get("ok") is True
            and item.get("trust_level") == "trusted"
            and item.get("freshness") != "stale"
        ]
        if action == "query_tool" and current_trusted:
            problems["query_tool_despite_current_trusted_evidence"] += 1
            if len(examples) < 30:
                examples.append(
                    {
                        "id": record.record_id,
                        "problem": "query_tool_despite_current_evidence",
                        "reference_answer": record.answer,
                    }
                )
        if action == "answer" and not current_trusted:
            problems["answer_without_current_trusted_evidence"] += 1
            if len(examples) < 30:
                examples.append(
                    {
                        "id": record.record_id,
                        "problem": "answer_without_current_evidence",
                        "reference_answer": record.answer,
                    }
                )
        if action == "answer" and current_trusted:
            primary = current_trusted[0]
            result = primary.get("result") or {}
            domain = str(primary.get("domain") or "")
            values: list[str] = []
            if domain == "inventory":
                values = [str(result.get("sellable_quantity"))]
            elif domain == "payment":
                values = [str(result.get("payment_status") or "")]
            elif domain == "order":
                values = [str(result.get("order_status") or "")]
            elif domain == "logistics":
                values = [str(result.get("shipment_status") or "")]
            if values and not any(value and value in record.answer for value in values):
                problems["answer_not_grounded_in_current_tool_value"] += 1
                if len(examples) < 30:
                    examples.append(
                        {
                            "id": record.record_id,
                            "problem": "answer_not_grounded",
                            "expected_values": values,
                            "reference_answer": record.answer,
                        }
                    )
    return {
        "records_checked": len(selected),
        "problem_counts": dict(problems),
        "examples": examples,
    }


def audit_auth_consistency(train: list[Record], tests: list[Record]) -> dict[str, Any]:
    train_problems = Counter()
    test_problems = Counter()
    for record in train:
        if record.dataset != "auth_privacy_handoff_20000":
            continue
        row = record.raw or {}
        behavior = str(row.get("correct_behavior") or "")
        trusted = bool(row.get("has_trusted_tool_evidence"))
        auth = json.loads(str(row.get("identity_login_authorization_json") or "{}"))
        allowed = str(auth.get("authorization") or "") in {"self_or_verified_delegate", "allowed"}
        if behavior == "回答" and (not trusted or not allowed):
            train_problems["answer_without_trusted_authorized_state"] += 1
        if behavior == "拒绝" and allowed:
            train_problems["refuse_despite_allowed_state"] += 1
    for record in tests:
        if record.dataset != "auth_privacy_handoff_test_300":
            continue
        payload = record.raw or {}
        question = payload.get("question") or {}
        key = payload.get("key") or {}
        behavior = str(key.get("correct_behavior") or "")
        evidence = json.loads(str(question.get("scenario_tool_evidence_json") or "{}"))
        identity = json.loads(
            str(question.get("scenario_identity_authorization_json") or "{}")
        )
        result = evidence.get("result") or {}
        authorization = str(identity.get("authorization") or result.get("authorization") or "")
        authorized = authorization in {"allowed", "allowed_minimum_scope"}
        trusted = evidence.get("trusted_evidence") is True
        if behavior == "回答" and (not authorized or not trusted):
            test_problems["answer_without_trusted_authorized_state"] += 1
        if behavior == "拒绝" and authorized and trusted:
            test_problems["refuse_despite_trusted_authorized_state"] += 1
    return {
        "training_problem_counts": dict(train_problems),
        "test_problem_counts": dict(test_problems),
    }


def manifest_missing_files(root: Path) -> dict[str, Any]:
    manifest = root / "独立测试集_300_完整整合包_含私有答案/independent_test_300_MANIFEST.sha256"
    package_root = manifest.parent
    missing = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        _, relative = line.split(maxsplit=1)
        if not (package_root / relative).exists():
            missing.append(relative)
    return {"manifest": str(manifest), "missing_entries": missing, "missing_count": len(missing)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extracted-root", type=Path, required=True)
    parser.add_argument("--inventory-docx", type=Path, required=True)
    parser.add_argument("--question-docx", type=Path, required=True)
    parser.add_argument("--answer-docx", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.extracted_root.resolve()
    project_root = args.project_root.resolve()
    train = load_training_records(root, args.inventory_docx.resolve(), project_root)
    tests = load_test_records(
        root, args.question_docx.resolve(), args.answer_docx.resolve(), project_root
    )

    train_by_dataset: dict[str, list[Record]] = defaultdict(list)
    test_by_dataset: dict[str, list[Record]] = defaultdict(list)
    for record in train:
        train_by_dataset[record.dataset].append(record)
    for record in tests:
        test_by_dataset[record.dataset].append(record)

    report = {
        "training_total_including_existing_v5": len(train),
        "new_training_candidate_total": sum(
            len(rows) for name, rows in train_by_dataset.items() if not name.startswith("existing_")
        ),
        "test_total_including_existing_core_200": len(tests),
        "new_test_total": sum(
            len(rows) for name, rows in test_by_dataset.items() if not name.startswith("existing_")
        ),
        "training_profiles": {
            name: profile_records(rows) for name, rows in sorted(train_by_dataset.items())
        },
        "test_profiles": {
            name: profile_records(rows) for name, rows in sorted(test_by_dataset.items())
        },
        "cross_training_exact": cross_training_exact(train),
        "train_test_exact": exact_overlap(train, tests),
        "test_to_test_exact": test_to_test_exact_overlap(tests),
        "train_test_near_prompt": near_overlap(train, tests, "prompt"),
        "train_test_near_answer": near_overlap(train, tests, "answer"),
        "order_training_logic": audit_order_training(train),
        "order_test_logic": audit_order_test(tests),
        "independent_test_logic": audit_independent_test(tests),
        "auth_consistency": audit_auth_consistency(train, tests),
        "independent_manifest": manifest_missing_files(root),
        "docx_pairing": {
            "question_ids": len(parse_test_docx(args.question_docx.resolve())),
            "answer_ids": len(parse_test_docx(args.answer_docx.resolve())),
            "id_sets_match": set(parse_test_docx(args.question_docx.resolve()))
            == set(parse_test_docx(args.answer_docx.resolve())),
        },
        "primary_file_hashes": {
            "inventory_docx": sha256_file(args.inventory_docx.resolve()),
            "question_docx": sha256_file(args.question_docx.resolve()),
            "answer_docx": sha256_file(args.answer_docx.resolve()),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
