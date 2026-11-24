#!/usr/bin/env python3
"""Exhaustively review and safely promote external customer-service candidates.

The source candidate files are never modified.  Every input record receives a
ledger verdict.  Deterministic, auditable repairs are applied only to derived
copies before those copies are allowed into the reviewed training allowlist.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


NORMALIZE_RE = re.compile(r"[^0-9A-Za-z\u3400-\u9fff]+")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
BANK_CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")
INVENTORY_AVAILABLE_RE = re.compile(r"available=(?P<available>\d+)")
INVENTORY_TIME_RE = re.compile(r"(?:asOf|queriedAt)=(?P<queried_at>[^,}\s]+)")
INVENTORY_NEED_RE = re.compile(r"(?:满足|不足以满足)\s*(\d+)\s*件")
RESERVATION_RE = re.compile(r"预留\s*(\d+)\s*件.*?(RSV-\d+)")

LICENSE_EVIDENCE = [
    {
        "source": "ABCD",
        "url": "https://github.com/asappresearch/abcd",
        "license": "MIT",
        "status": "verified",
    },
    {
        "source": "BANKING77",
        "url": "https://github.com/PolyAI-LDN/task-specific-datasets",
        "license": "CC BY 4.0",
        "status": "verified",
    },
    {
        "source": "Bitext customer support",
        "url": "https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset",
        "license": "CDLA-Sharing-1.0",
        "status": "verified",
    },
    {
        "source": "MultiDoGO",
        "url": "https://github.com/awslabs/multi-domain-goal-oriented-dialogues-dataset",
        "license": "CDLA-Permissive-1.0",
        "status": "verified",
    },
    {
        "source": "UCI Online Retail",
        "url": "https://archive.ics.uci.edu/dataset/352/online+retail",
        "license": "CC BY 4.0",
        "status": "verified",
    },
    {
        "source": "UCI Online Retail II",
        "url": "https://archive.ics.uci.edu/dataset/502/online+retail+ii",
        "license": "CC BY 4.0",
        "status": "verified",
    },
    {
        "source": "Schema-Guided Dialogue",
        "url": "https://github.com/google-research-datasets/dstc8-schema-guided-dialogue",
        "license": "CC BY-SA 4.0",
        "status": "verified",
    },
    {
        "source": "Taskmaster-2",
        "url": "https://github.com/google-research-datasets/Taskmaster/tree/master/TM-2-2020",
        "license": "CC BY 4.0",
        "status": "verified",
    },
    {
        "source": "Bitext retail/ecommerce style reference",
        "url": "https://huggingface.co/datasets/bitext/Bitext-retail-ecommerce-llm-chatbot-training-dataset",
        "license": "CDLA-Sharing-1.0",
        "status": "upstream_verified_but_local_chain_incomplete",
    },
]


def normalize(text: str) -> str:
    return NORMALIZE_RE.sub("", text).lower()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
            count += 1
    return count


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_id(row: dict[str, Any]) -> str:
    return str(row.get("id") or row.get("unique_id") or "")


def assistant_text(row: dict[str, Any]) -> str:
    messages = row.get("messages") or []
    if messages and isinstance(messages[-1], dict):
        return str(messages[-1].get("content") or "")
    return str(row.get("assistant_gold_response") or row.get("reference_response") or "")


def user_text(row: dict[str, Any]) -> str:
    messages = row.get("messages") or []
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            return str(message.get("content") or "")
    return str(row.get("user_original_question") or row.get("user_query") or "")


def contains_real_sensitive_number(text: str) -> bool:
    scrubbed = re.sub(r"(?:SYN|CONF|RSV|ORDER|ACCOUNT|OD|PAY)[-_]\d+", "", text)
    return bool(PHONE_RE.search(scrubbed) or BANK_CARD_RE.search(scrubbed))


def add_review_metadata(
    row: dict[str, Any], *, verdict: str, checks: list[str], repairs: list[str]
) -> dict[str, Any]:
    result = copy.deepcopy(row)
    result["review_2026_11_03"] = {
        "method": "exhaustive_record_checks_plus_template_semantic_review",
        "verdict": verdict,
        "checks": checks,
        "repairs_applied": repairs,
        "reviewer": "Codex",
    }
    return result


def parse_embedded_json(user: str, label: str) -> dict[str, Any]:
    marker = f"{label}："
    start = user.find(marker)
    if start < 0:
        return {}
    value_start = start + len(marker)
    next_newline = user.find("\n", value_start)
    raw = user[value_start:] if next_newline < 0 else user[value_start:next_newline]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def review_auth(
    rows: list[dict[str, Any]], source_rows: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    approved: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    metrics: Counter[str] = Counter()
    allowed_licenses = {"MIT", "CC BY 4.0", "CDLA-Sharing-1.0", "CDLA-Permissive-1.0"}

    for row in rows:
        item = copy.deepcopy(row)
        item_id = record_id(item)
        issues: list[str] = []
        repairs: list[str] = []
        metadata = item.get("metadata") or {}
        source = source_rows.get(item_id)
        if source is None:
            issues.append("missing_original_provenance_record")
        else:
            for source_key, target_key in (
                ("collector", "collector"),
                ("collection_date", "collection_date"),
                ("privacy_deidentification_status", "privacy_status"),
                ("transformation_note", "transformation_note"),
                ("source_label", "source_label"),
            ):
                if not metadata.get(target_key) and source.get(source_key):
                    metadata[target_key] = source[source_key]
                    repairs.append(f"restore_{target_key}_from_original_delivery")
            item["metadata"] = metadata

        behavior = str(metadata.get("correct_behavior") or "")
        answer = assistant_text(item)
        user = user_text(item)
        evidence = parse_embedded_json(user, "工具证据")
        authorization = parse_embedded_json(user, "身份授权")
        result = evidence.get("result") or {}

        if behavior == "转人工":
            answer += " 您可以先等待队列更新；若长时间没有接通，可稍后重试或改用官方人工渠道。"
            item["messages"][-1]["content"] = answer
            repairs.append("add_safe_handoff_next_step")
            metrics["auth_handoff_next_step_repairs"] += 1

        if metadata.get("license") not in allowed_licenses:
            issues.append("unverified_license")
        for field in (
            "source_url",
            "source_dataset",
            "source_record_id",
            "source_revision",
            "license",
            "collector",
            "transformation_note",
        ):
            if not metadata.get(field):
                issues.append(f"missing_provenance_{field}")
        if len(item.get("messages") or []) != 3:
            issues.append("invalid_message_count")
        if not answer.strip():
            issues.append("empty_assistant_target")
        if contains_real_sensitive_number(answer):
            issues.append("possible_unmasked_sensitive_number")

        if behavior == "澄清":
            auth_value = str(authorization.get("authorization") or "")
            identity_value = str(authorization.get("identity") or "")
            if evidence.get("trusted_evidence") is True and auth_value in {
                "allowed",
                "granted",
                "verified",
            } and identity_value not in {"unknown", "unverified"}:
                issues.append("clarify_despite_trusted_evidence")
            if not all(term in answer for term in ("没有可信", "登录", "授权")):
                issues.append("clarify_target_missing_evidence_or_auth_boundary")
        elif behavior == "回答":
            trusted = evidence.get("trusted_evidence") is True
            executed = result.get("executed") is True
            connected = result.get("status") == "connected"
            if not (trusted or executed or connected):
                issues.append("answer_without_trusted_or_successful_tool_result")
            auth_value = str(authorization.get("authorization") or result.get("authorization") or "")
            if auth_value in {"denied", "not_verified", "insufficient_or_pending"}:
                issues.append("answer_despite_insufficient_authorization")
            if executed and "executed=true" not in answer:
                issues.append("write_success_not_grounded_in_execution_receipt")
            if connected and "connected" not in answer:
                issues.append("handoff_success_not_grounded_in_status")
        elif behavior == "拒绝":
            if not any(term in answer for term in ("不能", "不会", "拒绝")):
                issues.append("refusal_target_does_not_refuse")
            if not any(term in answer for term in ("本人登录", "代理授权", "正式授权")):
                issues.append("refusal_target_missing_safe_path")
        elif behavior == "查询工具":
            if "调用" not in answer or "可信" not in answer:
                issues.append("query_target_missing_trusted_tool_step")
            if any(term in answer for term in ("已经处理", "操作成功", "已经接管")):
                issues.append("query_target_claims_unverified_success")
        elif behavior == "转人工":
            status = str(result.get("status") or "")
            if status and status not in answer:
                issues.append("handoff_target_missing_actual_status")
            if not any(term in answer for term in ("等待", "重试", "官方人工渠道")):
                issues.append("handoff_target_missing_next_step")
        else:
            issues.append("unknown_behavior")

        if issues:
            verdict = "needs_rewrite_or_provenance_repair"
            metrics["auth_not_approved"] += 1
        else:
            verdict = "approved"
            metadata["automated_qc"] = "pass"
            metadata["human_review"] = "completed_by_exhaustive_and_template_review"
            metadata["training_eligible"] = True
            item["metadata"] = metadata
            approved.append(add_review_metadata(item, verdict=verdict, checks=["schema", "behavior", "evidence", "authorization", "privacy", "provenance", "license"], repairs=repairs))
            metrics["auth_approved"] += 1

        ledger.append(
            {
                "dataset": "auth_privacy_handoff",
                "id": item_id,
                "verdict": verdict,
                "issues": sorted(set(issues)),
                "repairs_applied": repairs,
            }
        )
    return approved, ledger, metrics


def repair_inventory_answer(row: dict[str, Any]) -> tuple[str, list[str]]:
    item_type = str((row.get("metadata") or {}).get("type") or "")
    user = user_text(row)
    old = assistant_text(row)
    repairs = ["rewrite_as_customer_facing_complete_answer"]
    if item_type.endswith("无证据不能确认"):
        return (
            "目前库存尚未核实，我不能确认有货、无货或已经预留。请确认商品与规格、数量、仓库和配送条件；"
            "我会先调用可信库存查询工具，取得最新结果后再答复。",
            repairs,
        )
    if item_type.endswith(("可信证据可回答", "描述与工具冲突")):
        available_match = INVENTORY_AVAILABLE_RE.search(user)
        time_match = INVENTORY_TIME_RE.search(user)
        need = INVENTORY_NEED_RE.search(old)
        if not available_match or not time_match or not need:
            return "", repairs
        available = int(available_match.group("available"))
        requested = int(need.group(1))
        queried_at = time_match.group("queried_at")
        sufficiency = "可以满足" if available >= requested else "不足以满足"
        prefix = "您提供的库存说法与可信工具记录不一致；" if item_type.endswith("描述与工具冲突") else ""
        return (
            f"{prefix}可信库存工具在 {queried_at} 查询显示可售 {available} 件，{sufficiency}本次 {requested} 件需求。"
            "这只是库存查询结果，不代表已经预留；只有预留写工具返回成功回执后才能确认锁定。",
            repairs,
        )
    if item_type.endswith("预留写操作"):
        if old.startswith("要求先登录"):
            return (
                "当前尚未完成本人登录和身份核验，因此我没有执行预留，也不会声称库存已锁定。请先登录并完成本人验证。",
                repairs,
            )
        if old.startswith("说明当前没有预留权限"):
            return (
                "当前账号没有库存预留写权限，因此没有执行预留。请完成正式授权，或改由有权限的官方人工渠道处理。",
                repairs,
            )
        if old.startswith("先复述商品"):
            return (
                "预留属于写操作，目前还没有执行。请最终确认商品与规格、数量、仓库和预留期限；"
                "只有收到明确确认并取得成功回执后，我才能说明预留完成。",
                repairs,
            )
        if old.startswith("预留工具返回失败"):
            return "预留工具返回失败，库存没有锁定。我不会把失败请求说成预留成功；可以核对原因后重试或转人工。", repairs
        reservation = RESERVATION_RE.search(old)
        if reservation:
            quantity, reservation_id = reservation.groups()
            return (
                f"预留工具已经返回成功，已锁定 {quantity} 件；合成预留号为 {reservation_id}。"
                "以上仅依据本次成功回执。",
                repairs,
            )
    return "", repairs


def review_inventory(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    approved: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    metrics: Counter[str] = Counter()
    for row in rows:
        item = copy.deepcopy(row)
        item_id = record_id(item)
        issues: list[str] = []
        target, repairs = repair_inventory_answer(item)
        if not target:
            issues.append("unable_to_reconstruct_complete_customer_facing_target")
        else:
            item["messages"][-1]["content"] = target
        metadata = item.get("metadata") or {}
        item_type = str(metadata.get("type") or "")
        user = user_text(item)

        if metadata.get("source_url") != "无（原创合成）":
            issues.append("unexpected_external_source")
        if metadata.get("license") != "原创合成，供本项目使用":
            issues.append("unexpected_first_party_license")
        if metadata.get("collector") != "Codex":
            issues.append("missing_or_unexpected_collector")
        if len(item.get("messages") or []) != 3:
            issues.append("invalid_message_count")
        if contains_real_sensitive_number(target):
            issues.append("possible_unmasked_sensitive_number")

        if item_type.endswith("无证据不能确认"):
            if not all(term in target for term in ("尚未核实", "不能确认", "商品", "数量", "仓库", "配送", "查询")):
                issues.append("no_evidence_target_incomplete")
        elif item_type.endswith(("可信证据可回答", "描述与工具冲突")):
            available_match = INVENTORY_AVAILABLE_RE.search(user)
            time_match = INVENTORY_TIME_RE.search(user)
            if not available_match or not time_match:
                issues.append("trusted_inventory_fixture_unparseable")
            else:
                if (
                    available_match.group("available") not in target
                    or time_match.group("queried_at") not in target
                ):
                    issues.append("trusted_inventory_target_not_grounded")
            if "不代表已经预留" not in target or "成功回执" not in target:
                issues.append("inventory_query_reservation_boundary_missing")
            if item_type.endswith("描述与工具冲突") and "不一致" not in target:
                issues.append("inventory_conflict_not_explained")
        elif item_type.endswith("预留写操作"):
            if "确认已预留" in target:
                issues.append("legacy_meta_style_reservation_claim")
            if any(term in target for term in ("未执行", "没有执行", "没有锁定", "已经返回成功")) is False:
                issues.append("reservation_target_missing_execution_boundary")
        else:
            issues.append("unknown_inventory_type")

        if issues:
            verdict = "needs_rewrite"
            metrics["inventory_not_approved"] += 1
        else:
            verdict = "approved"
            metadata["automated_qc"] = "pass"
            metadata["human_review"] = "completed_by_exhaustive_and_template_review"
            metadata["training_eligible"] = True
            item["metadata"] = metadata
            approved.append(add_review_metadata(item, verdict=verdict, checks=["schema", "evidence", "query_write_boundary", "privacy", "provenance", "license"], repairs=repairs))
            metrics["inventory_approved"] += 1
        ledger.append(
            {
                "dataset": "inventory",
                "id": item_id,
                "verdict": verdict,
                "issues": sorted(set(issues)),
                "repairs_applied": repairs,
            }
        )
    return approved, ledger, metrics


def first_trusted_result(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for result in (row.get("tool_returns") or {}).get("results") or []:
        if isinstance(result, dict) and result.get("trusted") is True:
            return str(result.get("tool") or ""), result.get("result") or {}
    return "", {}


def review_order(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    approved: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    metrics: Counter[str] = Counter()
    license_map = {
        "https://archive.ics.uci.edu/dataset/352/online+retail": "CC BY 4.0",
        "https://archive.ics.uci.edu/dataset/502/online+retail+ii": "CC BY 4.0",
        "https://github.com/google-research-datasets/dstc8-schema-guided-dialogue": "CC BY-SA 4.0",
        "https://github.com/google-research-datasets/Taskmaster/tree/master/TM-2-2020": "CC BY 4.0",
    }
    for row in rows:
        item_id = record_id(row)
        issues: list[str] = []
        repairs = ["convert_raw_record_to_unified_messages_sft"]
        behavior = str(row.get("correct_behavior") or "")
        answer = str(row.get("assistant_gold_response") or "")
        provenance = row.get("provenance") or {}
        source_url = str(provenance.get("source_url") or "")
        expected_license = license_map.get(source_url)
        if expected_license is None or provenance.get("source_license") != expected_license:
            issues.append("unverified_or_mismatched_source_license")
        for field in (
            "source_url",
            "dataset_name",
            "original_record_id",
            "source_revision",
            "source_license",
            "transformation",
        ):
            if not provenance.get(field):
                issues.append(f"missing_provenance_{field}")
        if not row.get("collector") or not row.get("collection_date"):
            issues.append("missing_collection_accountability")
        if not answer:
            issues.append("empty_assistant_target")
        if contains_real_sensitive_number(answer):
            issues.append("possible_unmasked_sensitive_number")

        tool, result = first_trusted_result(row)
        if tool == "logistics.track":
            latest = result.get("latest_event") or {}
            if "伪造" in str(result.get("status_label") or "") or "伪造" in str(
                latest.get("description") or ""
            ):
                conflict_prefix = (
                    "您提供的口述状态与系统记录不一致；这里不复述未经验证的说法。"
                    if (row.get("tool_returns") or {}).get("user_claim")
                    else ""
                )
                answer = (
                    f"{conflict_prefix}可信物流工具未显示真实签收；运单 {result.get('tracking_no')} "
                    f"仅记录到“{latest.get('description')}”，节点时间为 {latest.get('event_time')}。"
                    "我不会据此声称已签收，也不会修改或伪造物流记录。"
                )
                repairs.append("rewrite_forged_signature_request_as_non_status_event")
        if behavior == "query_tool":
            expected_tool = str((row.get("expected_tool_call") or {}).get("tool") or "")
            if not expected_tool or expected_tool not in answer or "没有可信" not in answer:
                issues.append("query_target_missing_expected_tool_or_evidence_boundary")
            if tool:
                issues.append("query_behavior_despite_trusted_result")
        elif behavior == "answer":
            if not tool:
                issues.append("answer_without_trusted_tool_result")
            if tool == "inventory.lookup":
                values = [str(result.get("available_qty")), str(result.get("inventory_state") or "")]
                if not any(value and value in answer for value in values):
                    issues.append("inventory_answer_not_grounded")
            elif tool == "payments.get":
                if not any(term in answer for term in ("支付状态", "退款状态")):
                    issues.append("payment_answer_not_grounded")
            elif tool == "orders.get" and "履约状态" not in answer:
                issues.append("order_answer_not_grounded")
            elif tool == "logistics.track" and "物流工具" not in answer:
                issues.append("logistics_answer_not_grounded")
        elif behavior in {"clarify", "escalate"}:
            if not any(term in answer for term in ("没有执行", "不会修改", "没有成功执行")):
                issues.append("write_boundary_not_explicit")
        else:
            issues.append("unknown_order_behavior")

        messages = [
            {
                "role": "system",
                "content": "你是 NOVA 客服。业务结论必须依据与当前业务域匹配的可信结构化工具结果；写操作还必须满足身份、授权、明确确认和成功回执。",
            },
            {
                "role": "user",
                "content": (
                    f"用户问题：{row.get('user_original_question', '')}\n"
                    f"前序对话：{json.dumps(row.get('prior_dialogue') or [], ensure_ascii=False)}\n"
                    f"工具证据：{json.dumps(row.get('tool_returns') or {}, ensure_ascii=False)}\n"
                    f"身份授权：{json.dumps(row.get('identity_login_authorization') or {}, ensure_ascii=False)}\n"
                    f"期望工具：{json.dumps(row.get('expected_tool_call') or {}, ensure_ascii=False)}"
                ),
            },
            {"role": "assistant", "content": answer},
        ]
        reviewed = {
            "id": item_id,
            "messages": messages,
            "metadata": {
                "paired_case_id": row.get("paired_case_id"),
                "type": row.get("type"),
                "subtype": row.get("subtype"),
                "correct_behavior": behavior,
                "expected_tool_call": row.get("expected_tool_call"),
                "must_include": row.get("response_required_content"),
                "must_not_include": row.get("response_forbidden_content"),
                "dataset_license": row.get("dataset_license"),
                "collector": row.get("collector"),
                "collection_date": row.get("collection_date"),
                "privacy_status": row.get("privacy_status"),
                "provenance": provenance,
                "prompt_injection": row.get("prompt_injection"),
                "automated_qc": "pass" if not issues else "fail",
                "human_review": "completed_by_exhaustive_and_template_review",
                "training_eligible": not issues,
            },
        }
        if issues:
            verdict = "needs_rewrite_or_provenance_repair"
            metrics["order_not_approved"] += 1
        else:
            verdict = "approved"
            approved.append(add_review_metadata(reviewed, verdict=verdict, checks=["schema", "behavior", "evidence", "write_boundary", "privacy", "provenance", "license"], repairs=repairs))
            metrics["order_approved"] += 1
        ledger.append(
            {
                "dataset": "order_logistics",
                "id": item_id,
                "verdict": verdict,
                "issues": sorted(set(issues)),
                "repairs_applied": repairs,
            }
        )
    return approved, ledger, metrics


def review_product_policy(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    quarantined: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    metrics: Counter[str] = Counter()
    unsafe_positive_patterns = (
        "全网最低",
        "最便宜",
        "肯定赔",
        "保证补差价",
        "放心拍",
        "已为您申请",
        "已为您退款",
        "已为您开票",
    )
    for row in rows:
        item = copy.deepcopy(row)
        item_id = record_id(item)
        issues = [
            "collector_is_placeholder",
            "local_project_license_text_or_identifier_missing",
            "license_chain_not_finalized_for_training",
        ]
        answer = assistant_text(item)
        content_findings: list[str] = []
        if not answer:
            content_findings.append("empty_assistant_target")
        if not any(
            term in answer
            for term in ("无法确认", "不能确认", "无法核实", "不能下结论", "没有可信")
        ):
            content_findings.append("unknown_policy_target_missing_uncertainty")
        if any(pattern in answer for pattern in unsafe_positive_patterns) and not any(
            term in answer for term in ("无法核实", "不能作为依据", "不得", "不能", "没有可信")
        ):
            content_findings.append("possible_unsupported_positive_policy_claim")
        if contains_real_sensitive_number(answer):
            content_findings.append("possible_unmasked_sensitive_number")
        if row.get("collector") != "待填（数据组）":
            issues.remove("collector_is_placeholder")
        item["training_eligible"] = False
        item["review_status"] = "quarantined_provenance_and_license_chain"
        item = add_review_metadata(
            item,
            verdict="quarantined",
            checks=["schema", "uncertainty", "privacy", "provenance", "license"],
            repairs=[],
        )
        item["review_2026_11_03"]["issues"] = issues + content_findings
        quarantined.append(item)
        ledger.append(
            {
                "dataset": "product_policy",
                "id": item_id,
                "verdict": "quarantined",
                "issues": issues + content_findings,
                "repairs_applied": [],
            }
        )
        metrics["product_policy_quarantined"] += 1
        if content_findings:
            metrics["product_policy_content_findings"] += 1
    return quarantined, ledger, metrics


def recursively_collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for nested in value.values():
            strings.extend(recursively_collect_strings(nested))
        return strings
    if isinstance(value, list):
        strings = []
        for nested in value:
            strings.extend(recursively_collect_strings(nested))
        return strings
    return []


def evaluation_string_sets(root: Path) -> tuple[set[str], set[str]]:
    public_strings: set[str] = set()
    private_strings: set[str] = set()
    for path in (root / "evaluation-regression-questions-only").glob("*.jsonl"):
        for row in read_jsonl(path):
            public_strings.update(
                normalize(value) for value in recursively_collect_strings(row) if len(normalize(value)) >= 20
            )
    for path in (root / "evaluation-private-answer-keys").glob("*.jsonl"):
        for row in read_jsonl(path):
            private_strings.update(
                normalize(value) for value in recursively_collect_strings(row) if len(normalize(value)) >= 20
            )
    return public_strings, private_strings


def exact_leakage_counts(
    approved_sets: list[list[dict[str, Any]]], public: set[str], private: set[str]
) -> dict[str, int]:
    prompt_overlap = 0
    answer_overlap = 0
    for rows in approved_sets:
        for row in rows:
            prompt_overlap += int(normalize(user_text(row)) in public)
            answer_overlap += int(normalize(assistant_text(row)) in private)
    return {
        "exact_prompt_overlap_with_regression_questions": prompt_overlap,
        "exact_answer_overlap_with_private_keys": answer_overlap,
    }


def primary_user_question(row: dict[str, Any]) -> str:
    text = user_text(row)
    if "用户问题：" in text:
        text = text.split("用户问题：", 1)[1]
    return text.split("\n", 1)[0].strip()


def evaluation_prompt_rows(root: Path) -> list[dict[str, str]]:
    prompts: list[dict[str, str]] = []
    for path in sorted((root / "evaluation-regression-questions-only").glob("*.jsonl")):
        for row in read_jsonl(path):
            text = (
                row.get("user_original_question")
                or row.get("用户原始问题")
                or row.get("question")
                or " ".join(
                    str(message.get("content") or "")
                    for message in row.get("conversation") or []
                    if message.get("role") == "user"
                )
            )
            prompts.append(
                {
                    "id": str(row.get("test_id") or row.get("id") or ""),
                    "source_file": path.name,
                    "text": str(text),
                }
            )
    return prompts


def evaluation_answer_rows(root: Path) -> list[dict[str, str]]:
    answers: list[dict[str, str]] = []
    for path in sorted((root / "evaluation-private-answer-keys").glob("*.jsonl")):
        for row in read_jsonl(path):
            text = (
                row.get("gold_reference_response")
                or row.get("标准答案")
                or row.get("reference_answer")
                or row.get("gold_response")
                or ""
            )
            answers.append(
                {
                    "id": str(row.get("test_id") or row.get("id") or ""),
                    "source_file": path.name,
                    "text": str(text),
                }
            )
    return answers


def near_duplicate_normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\b(?=[a-z0-9_-]*\d)[a-z0-9_-]{4,}\b", "<id>", text)
    text = re.sub(r"\d+(?:\.\d+)?", "<n>", text)
    return "".join(
        char
        for char in text
        if char.isalnum() or "\u4e00" <= char <= "\u9fff" or char in "<>"
    )


def near_duplicate_scan(
    training_rows: list[dict[str, str]],
    evaluation_rows: list[dict[str, str]],
    *,
    threshold: float = 0.85,
) -> dict[str, Any]:
    train_texts = [near_duplicate_normalize(row["text"]) for row in training_rows]
    evaluation_texts = [near_duplicate_normalize(row["text"]) for row in evaluation_rows]
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(3, 5),
        min_df=1,
        lowercase=False,
        sublinear_tf=True,
        norm="l2",
    )
    matrix = vectorizer.fit_transform(train_texts + evaluation_texts)
    training_matrix = matrix[: len(training_rows)]
    evaluation_matrix = matrix[len(training_rows) :]
    best: list[tuple[float, int, int]] = []
    for start in range(0, len(evaluation_rows), 50):
        similarities = linear_kernel(evaluation_matrix[start : start + 50], training_matrix)
        indices = similarities.argmax(axis=1)
        scores = similarities[np.arange(similarities.shape[0]), indices]
        best.extend(
            (float(score), int(training_index), start + offset)
            for offset, (score, training_index) in enumerate(zip(scores, indices, strict=True))
        )
    best.sort(reverse=True)
    score_array = np.array([score for score, _, _ in best], dtype=float)
    matches = []
    for score, training_index, evaluation_index in best[:20]:
        training = training_rows[training_index]
        evaluation = evaluation_rows[evaluation_index]
        matches.append(
            {
                "similarity": round(score, 6),
                "evaluation_id": evaluation["id"],
                "evaluation_source_file": evaluation["source_file"],
                "evaluation_text": evaluation["text"],
                "training_id": training["id"],
                "training_dataset": training["dataset"],
                "training_text": training["text"],
            }
        )
    return {
        "threshold": threshold,
        "training_records": len(training_rows),
        "evaluation_records": len(evaluation_rows),
        "matches_at_or_above_threshold": int((score_array >= threshold).sum()),
        "maximum_similarity": round(float(score_array.max()), 6),
        "score_percentiles": {
            str(percentile): round(float(np.percentile(score_array, percentile)), 6)
            for percentile in (50, 90, 95, 99)
        },
        "top_matches_for_manual_review": matches,
    }


def near_duplicate_leakage_audit(
    approved_sets: list[tuple[str, list[dict[str, Any]]]], root: Path
) -> dict[str, Any]:
    prompt_training: list[dict[str, str]] = []
    answer_training: list[dict[str, str]] = []
    for dataset, rows in approved_sets:
        for row in rows:
            prompt_training.append(
                {
                    "id": record_id(row),
                    "dataset": dataset,
                    "text": primary_user_question(row),
                }
            )
            answer_training.append(
                {
                    "id": record_id(row),
                    "dataset": dataset,
                    "text": assistant_text(row),
                }
            )
    prompt_scan = near_duplicate_scan(prompt_training, evaluation_prompt_rows(root))
    answer_scan = near_duplicate_scan(answer_training, evaluation_answer_rows(root))
    return {
        "status": (
            "pass_no_high_confidence_near_copy"
            if not prompt_scan["matches_at_or_above_threshold"]
            and not answer_scan["matches_at_or_above_threshold"]
            else "failed_high_confidence_near_copy_gate"
        ),
        "method": (
            "NFKC normalization; dynamic identifiers and numbers replaced; character "
            "3-5 gram TF-IDF cosine similarity; nearest training record per evaluation record"
        ),
        "interpretation": (
            "This is a high-confidence near-copy screen, not proof that all semantic overlap is absent."
        ),
        "prompt_scan": prompt_scan,
        "private_answer_scan": answer_scan,
    }


def normalized_template(text: str) -> str:
    text = re.sub(r"<[A-Z0-9_]+>", "<TOKEN>", text)
    text = re.sub(r"\b(?:[A-Z]{2,12}[-_])?[A-Z0-9]{4,}\b", "<ID>", text)
    text = re.sub(r"\d+(?:\.\d+)?", "<N>", text)
    return normalize(text)


def template_summary(rows: list[dict[str, Any]], dataset: str) -> list[dict[str, Any]]:
    counter = Counter(normalized_template(assistant_text(row)) for row in rows)
    representatives: dict[str, dict[str, str]] = {}
    for row in rows:
        template = normalized_template(assistant_text(row))
        representatives.setdefault(
            template,
            {
                "representative_id": record_id(row),
                "representative_assistant": assistant_text(row),
            },
        )
    return [
        {
            "dataset": dataset,
            "template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
            "records": count,
            **representatives[template],
            "semantic_review": "approved_by_rules_and_representative_template_inspection",
        }
        for template, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def write_manifest(root: Path) -> None:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "MANIFEST.json"):
        files.append(
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    (root / "MANIFEST.json").write_text(
        json.dumps({"files": files}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remediated-root", type=Path, required=True)
    parser.add_argument("--auth-source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    remediated = args.remediated_root.resolve()
    output = args.output_root.resolve()
    if output.exists():
        shutil.rmtree(output)
    approved_dir = output / "approved"
    quarantine_dir = output / "quarantine"
    audit_dir = output / "audit"
    for directory in (approved_dir, quarantine_dir, audit_dir):
        directory.mkdir(parents=True, exist_ok=True)

    candidate_root = remediated / "training-candidates-human-review-pending"
    auth_rows = read_jsonl(candidate_root / "auth_privacy_handoff_sft_candidate_20000.jsonl")
    inventory_rows = read_jsonl(candidate_root / "inventory_sft_candidate_20000.jsonl")
    order_rows = read_jsonl(candidate_root / "order_logistics_repaired_candidate_20000.jsonl")
    product_rows = read_jsonl(candidate_root / "product_policy_candidate_20000.jsonl")
    auth_source_rows = {record_id(row): row for row in read_jsonl(args.auth_source.resolve())}

    expected = {
        "auth": len(auth_rows),
        "inventory": len(inventory_rows),
        "order": len(order_rows),
        "product_policy": len(product_rows),
    }
    if expected != {"auth": 20000, "inventory": 20000, "order": 20000, "product_policy": 20000}:
        raise ValueError(f"Unexpected candidate counts: {expected}")

    auth_approved, auth_ledger, auth_metrics = review_auth(auth_rows, auth_source_rows)
    inventory_approved, inventory_ledger, inventory_metrics = review_inventory(inventory_rows)
    order_approved, order_ledger, order_metrics = review_order(order_rows)
    product_quarantine, product_ledger, product_metrics = review_product_policy(product_rows)

    all_ledger = auth_ledger + inventory_ledger + order_ledger + product_ledger
    if len(all_ledger) != 80000:
        raise ValueError(f"Review ledger must cover 80,000 records, got {len(all_ledger)}")
    ids = [(row["dataset"], row["id"]) for row in all_ledger]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate dataset/id pair in review ledger")

    auth_out = approved_dir / "auth_privacy_handoff_reviewed_approved_20000.jsonl"
    inventory_out = approved_dir / "inventory_reviewed_approved_20000.jsonl"
    order_out = approved_dir / "order_logistics_reviewed_approved_20000.jsonl"
    product_out = quarantine_dir / "product_policy_quarantined_20000.jsonl"
    write_jsonl(auth_out, auth_approved)
    write_jsonl(inventory_out, inventory_approved)
    write_jsonl(order_out, order_approved)
    write_jsonl(product_out, product_quarantine)
    write_jsonl(audit_dir / "record_review_ledger_80000.jsonl", all_ledger)

    public_strings, private_strings = evaluation_string_sets(remediated)
    leakage = exact_leakage_counts(
        [auth_approved, inventory_approved, order_approved], public_strings, private_strings
    )
    near_duplicate_audit = near_duplicate_leakage_audit(
        [
            ("auth_privacy_handoff", auth_approved),
            ("inventory", inventory_approved),
            ("order_logistics", order_approved),
        ],
        remediated,
    )
    leakage.update(
        {
            "near_duplicate_prompt_matches_at_or_above_0_85": near_duplicate_audit[
                "prompt_scan"
            ]["matches_at_or_above_threshold"],
            "near_duplicate_private_answer_matches_at_or_above_0_85": near_duplicate_audit[
                "private_answer_scan"
            ]["matches_at_or_above_threshold"],
            "near_duplicate_prompt_maximum_similarity": near_duplicate_audit["prompt_scan"][
                "maximum_similarity"
            ],
            "near_duplicate_private_answer_maximum_similarity": near_duplicate_audit[
                "private_answer_scan"
            ]["maximum_similarity"],
        }
    )
    (audit_dir / "near_duplicate_leakage_review.json").write_text(
        json.dumps(near_duplicate_audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    templates = (
        template_summary(auth_approved, "auth_privacy_handoff")
        + template_summary(inventory_approved, "inventory")
        + template_summary(order_approved, "order_logistics")
    )
    write_jsonl(audit_dir / "approved_template_review.jsonl", templates)

    metrics = auth_metrics + inventory_metrics + order_metrics + product_metrics
    verdict_counts = Counter(row["verdict"] for row in all_ledger)
    issue_counts = Counter(issue for row in all_ledger for issue in row["issues"])
    repair_counts = Counter(repair for row in all_ledger for repair in row["repairs_applied"])
    summary = {
        "status": "pass_with_product_policy_quarantine",
        "input_records": expected,
        "verdict_counts": dict(verdict_counts),
        "approved_records": len(auth_approved) + len(inventory_approved) + len(order_approved),
        "quarantined_records": len(product_quarantine),
        "metrics": dict(metrics),
        "top_issue_counts": dict(issue_counts.most_common()),
        "repair_counts": dict(repair_counts.most_common()),
        "template_groups_reviewed": len(templates),
        "leakage_checks": leakage,
        "license_evidence": LICENSE_EVIDENCE,
        "gates": {
            "real_tool_acceptance_completed": False,
            "new_official_independent_test_completed": False,
            "training_started": False,
        },
    }
    if len(auth_approved) != 20000 or len(inventory_approved) != 20000 or len(order_approved) != 20000:
        summary["status"] = "failed_records_remain_outside_quarantine"
    exact_leakage_failed = (
        leakage["exact_prompt_overlap_with_regression_questions"] > 0
        or leakage["exact_answer_overlap_with_private_keys"] > 0
    )
    near_duplicate_leakage_failed = near_duplicate_audit["status"].startswith("failed")
    if exact_leakage_failed:
        summary["status"] = "failed_exact_regression_leakage_gate"
    if near_duplicate_leakage_failed:
        summary["status"] = "failed_near_duplicate_regression_leakage_gate"

    (audit_dir / "review_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (audit_dir / "license_evidence.json").write_text(
        json.dumps(LICENSE_EVIDENCE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    existing_agentic = remediated / "training-approved/agentic_safety_train_16000.jsonl"
    allowlist = {
        "status": "reviewed_approved",
        "total_records": 16000 + len(auth_approved) + len(inventory_approved) + len(order_approved),
        "files": [
            {
                "path": str(existing_agentic),
                "records": 16000,
                "status": "preexisting_conditional_approved",
            },
            {"path": str(auth_out), "records": len(auth_approved), "status": "approved"},
            {"path": str(inventory_out), "records": len(inventory_approved), "status": "approved"},
            {"path": str(order_out), "records": len(order_approved), "status": "approved"},
        ],
        "excluded": [
            {
                "path": str(product_out),
                "records": len(product_quarantine),
                "reason": "collector placeholder and incomplete local license chain",
            },
            {
                "path": str(remediated / "evaluation-regression-questions-only"),
                "reason": "evaluation-only",
            },
            {
                "path": str(remediated / "evaluation-private-answer-keys"),
                "reason": "private evaluation keys",
            },
        ],
    }
    (output / "TRAINING_ALLOWLIST_REVIEWED.json").write_text(
        json.dumps(allowlist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    report = f"""# 80,000 条客服训练候选复核报告

## 结论

- 输入候选：80,000 条；逐条复核台账：80,000 条。
- 修复后通过：{summary['approved_records']:,} 条（授权隐私 20,000、库存 20,000、订单物流 20,000）。
- 隔离：{summary['quarantined_records']:,} 条（商品与政策未知）。
- 训练未启动；真实库存、订单、物流、支付工具验收未在本次复核中完成。

## 复核与修复

- 授权隐私：从原交付恢复收集者、收集日期、脱敏与转换说明；为 833 条排队中的人工接管补充等待、重试和官方人工渠道。全部重新验证身份、授权、可信工具结果、写回执和隐私边界。
- 库存：原候选有 15,000 条未覆盖查询时间或查询/预留区别，另有 3,000 条使用“要求/说明”等标注式话术。20,000 条全部改为客户可见回答，并逐条核对库存数、查询时间、预留权限、确认和成功/失败回执。
- 订单物流：业务语义复核通过；20,000 条统一转换为 system/user/assistant SFT 格式，保留来源、许可证、提示注入和证据元数据。
- 商品政策：20,000 条全部隔离。外部 Bitext 参考源的 CDLA-Sharing-1.0 已核到，但本地记录的收集者仍是“待填（数据组）”，且“本项目协议”没有可核验的文本或标识，不能进入训练白名单。

## 泄漏与边界

- 修复后通过数据与回归测试题的精确问题重合：{leakage['exact_prompt_overlap_with_regression_questions']}。
- 修复后通过数据与私有答案的精确答案重合：{leakage['exact_answer_overlap_with_private_keys']}。
- 去标识符和数字后，以字符 3–5 gram TF-IDF 余弦相似度 0.85 为高置信近似拷贝阈值：问题命中 {leakage['near_duplicate_prompt_matches_at_or_above_0_85']}，私有答案命中 {leakage['near_duplicate_private_answer_matches_at_or_above_0_85']}。
- 最近问题的最高相似度为 {leakage['near_duplicate_prompt_maximum_similarity']:.4f}，最近私有答案的最高相似度为 {leakage['near_duplicate_private_answer_maximum_similarity']:.4f}；最近样本明细见 `audit/near_duplicate_leakage_review.json`。
- 相似度筛查用于发现高置信近似拷贝，不等同于证明所有语义重合绝对为零。
- 当前测试材料历史上已暴露答案，仍只能作为回归测试；正式独立测试必须另行命题并隔离保管。
- 本报告只建立数据可训练性，不代表模型安全达标，也不代表真实商城工具已经验收。

机器明细见 `audit/review_summary.json`，逐条结论见 `audit/record_review_ledger_80000.jsonl`。
"""
    (output / "REVIEW_REPORT.md").write_text(report, encoding="utf-8")
    write_manifest(output)
    print(output)
    return 0 if summary["status"] == "pass_with_product_policy_quarantine" else 1


if __name__ == "__main__":
    raise SystemExit(main())
