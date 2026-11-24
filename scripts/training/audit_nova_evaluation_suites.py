#!/usr/bin/env python3
"""Audit known answer-key and leakage defects in the external NOVA eval suites."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--independent-score", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    public = args.root / "evaluation-regression-questions-only"
    private = args.root / "evaluation-private-answer-keys"
    order_questions = load_jsonl(public / "order_logistics_repaired_questions_300.jsonl")
    order_keys = {
        item["id"]: item
        for item in load_jsonl(private / "order_logistics_repaired_key_300.jsonl")
    }
    independent_questions = load_jsonl(public / "independent_repaired_questions_300.jsonl")
    independent_keys = {
        item["test_id"]: item
        for item in load_jsonl(private / "independent_repaired_key_300.jsonl")
    }
    score = json.loads(args.independent_score.read_text(encoding="utf-8"))

    no_evidence = [
        item for item in order_questions if item.get("category") == "no_trusted_evidence"
    ]
    no_evidence_tools = Counter(
        str(order_keys[item["id"]].get("expected_tool_call", {}).get("tool"))
        for item in no_evidence
    )
    auth_tool_mismatch = [
        item["id"]
        for item in order_questions
        if item.get("category") == "authorization_boundary"
        and order_keys[item["id"]].get("expected_tool_call")
        and order_keys[item["id"]].get("tool_fixture", {}).get("tool")
        != order_keys[item["id"]].get("expected_tool_call", {}).get("tool")
    ]

    contradictory_handoff = []
    for item in independent_questions:
        key = independent_keys[item["test_id"]]
        latest = item.get("prior_turns", [])[-1] if item.get("prior_turns") else {}
        if (
            item.get("task_category") == "multi_turn"
            and key.get("expected_behavior", {}).get("action") == "handoff"
            and item.get("identity_and_auth", {}).get("permission_decision")
            == "allowed_read_only"
            and latest.get("content") == "我补一个条件：只查询，不要提交任何修改。"
            and all(
                evidence.get("ok") is True
                and evidence.get("trust_level") == "trusted"
                and evidence.get("freshness") == "current"
                for evidence in item.get("tool_evidence", [])
            )
        ):
            contradictory_handoff.append(item["test_id"])

    result_by_id = {item["test_id"]: item for item in score["results"]}
    valid_ids = [
        item["test_id"]
        for item in independent_questions
        if item["test_id"] not in contradictory_handoff
    ]
    valid_passed = sum(result_by_id[test_id]["passed"] for test_id in valid_ids)
    leaked_public_rows = sum(
        "expected_tool_calls" in item and "content_constraints" in item
        for item in independent_questions
    )
    officially_ineligible = sum(
        key.get("repair_metadata", {}).get("official_independent_test_eligible") is False
        for key in independent_keys.values()
    )

    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "order_logistics": {
            "underdetermined_no_evidence_count": len(no_evidence),
            "underdetermined_expected_tool_distribution": dict(no_evidence_tools),
            "authorization_fixture_expected_tool_mismatch_count": len(auth_tool_mismatch),
            "authorization_fixture_expected_tool_mismatch_ids": auth_tool_mismatch,
        },
        "independent_300": {
            "public_rows_exposing_expected_calls_and_constraints": leaked_public_rows,
            "official_independent_test_ineligible_rows": officially_ineligible,
            "contradictory_handoff_label_count": len(contradictory_handoff),
            "contradictory_handoff_label_ids": contradictory_handoff,
            "raw_regression_passed": score["summary"]["passed"],
            "raw_regression_total": score["summary"]["total"],
            "valid_subset_passed": valid_passed,
            "valid_subset_total": len(valid_ids),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = args.output.with_suffix(".md")
    report.write_text(
        "\n".join(
            [
                "# NOVA 外部评测套件质量审计",
                "",
                "## 结论",
                "",
                f"- 订单/物流套件有 {len(no_evidence)} 条题面无法确定唯一工具，但私钥在四种工具间轮换。",
                f"- 订单/物流授权题有 {len(auth_tool_mismatch)} 条预期认证工具与实际夹具工具不一致。",
                f"- Independent 300 有 {leaked_public_rows} 条公开题面直接包含 expected_tool_calls 和 content_constraints。",
                f"- 私钥明确标记 {officially_ineligible} 条均不具备正式独立测试资格。",
                f"- 其中 {len(contradictory_handoff)} 条把“只查询、不要修改”的只读场景错误标为转人工。",
                "",
                "## 可解释成绩",
                "",
                f"- 原始回归：{score['summary']['passed']}/{score['summary']['total']}。",
                f"- 剔除上述 {len(contradictory_handoff)} 条矛盾标签后：{valid_passed}/{len(valid_ids)}。",
                "- 该结果仍是内部回归，不是第三方盲测。",
                "",
                "## 矛盾标签 ID",
                "",
                ", ".join(f"`{test_id}`" for test_id in contradictory_handoff),
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"报告：{report}；有效子集：{valid_passed}/{len(valid_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
