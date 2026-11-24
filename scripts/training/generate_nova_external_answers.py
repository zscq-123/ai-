#!/usr/bin/env python3
"""Generate frozen NOVA answers from a questions-only JSONL file."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from ai_service.application.support_orchestrator import SupportOrchestrator
from ai_service.domain.models import Citation
from ai_service.infrastructure.model_provider import GroundedLocalModel


class EmptyRetriever:
    async def search(
        self, query: str, *, limit: int = 4, merchant_id: UUID | None = None
    ) -> list[tuple[str, Citation]]:
        del query, limit, merchant_id
        return []


class ScenarioTools:
    def __init__(
        self,
        test_id: str,
        payload: dict[str, Any],
        identity: dict[str, Any],
    ) -> None:
        self._test_id = test_id
        self._payload = payload
        self._identity = identity
        self.called = False

    async def lookup(
        self,
        message: str,
        *,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> list[tuple[str, Citation]]:
        del message, customer_id, merchant_id, product_id, sku_id
        self.called = True
        if not self._payload.get("called") or not self._payload.get("trusted_evidence"):
            return []
        result = self._payload.get("result")
        result = result if isinstance(result, dict) else {}
        error = self._payload.get("error")
        authorization = result.get("authorization")
        identity_authorization = self._identity.get("authorization")
        authorization_prefix = (
            "已核验当前身份与目标账号授权；"
            f"authorization={identity_authorization}。"
            if identity_authorization
            else ""
        )
        if authorization is not None:
            fields = {
                key: value
                for key, value in result.items()
                if key != "authorization" and value is not None
            }
            content = authorization_prefix + (
                "已核验当前身份与目标账号授权；以可信结构化工具结果为准，"
                f"authorization={authorization}。仅作最小必要披露并保持敏感字段掩码。"
            )
            if fields:
                content += "工具允许返回的掩码字段：" + json.dumps(
                    fields, ensure_ascii=False, sort_keys=True
                )
            if error:
                content += f"错误状态：{error}。"
        elif "executed" in result:
            content = authorization_prefix + (
                "已依次检查身份、授权、确认和执行结果；"
                f"可信结构化工具返回 executed={str(result['executed']).lower()}。"
            )
            if result["executed"]:
                content += "工具已有成功证据，可以确认操作完成。"
            else:
                content += "仅在 executed=true 时确认成功，授权不足时停止写操作。"
            if error:
                content += f"当前错误状态：{error}。"
        elif any(word in str(self._payload.get("tool")) for word in ("handoff", "human")):
            content = authorization_prefix + (
                "已读取人工接管工具状态；必须区分提交、排队、失败和已接管，"
                "并以接管工具状态为准。没有成功证据时不得确认成功。"
                + json.dumps(result, ensure_ascii=False, sort_keys=True)
            )
        else:
            content = authorization_prefix + "可信结构化工具结果：" + json.dumps(
                {"result": result, "error": error},
                ensure_ascii=False,
                sort_keys=True,
            )
        return [(content, Citation("外部测试可信工具", f"tool://{self._test_id}"))]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    return {}


async def answer_case(case: dict[str, Any]) -> dict[str, Any]:
    test_id = str(case["test_id"])
    tool_payload = parse_object(case.get("scenario_tool_evidence_json"))
    identity = parse_object(case.get("scenario_identity_authorization_json"))
    tools = ScenarioTools(test_id, tool_payload, identity)
    orchestrator = SupportOrchestrator(EmptyRetriever(), GroundedLocalModel(), tools)
    reply = await orchestrator.answer(
        str(case["user_original_question"]),
        authenticated=bool(identity.get("logged_in")),
    )
    return {
        "test_id": test_id,
        "answer": reply.answer,
        "intent": str(reply.intent),
        "requires_human": reply.requires_human,
        "requires_confirmation": reply.requires_confirmation,
        "citations": [citation.reference for citation in reply.citations],
        "tool_called": tools.called,
        "tool_name": tool_payload.get("tool"),
    }


async def generate(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [await answer_case(case) for case in cases]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = load_jsonl(args.questions)
    answers = asyncio.run(generate(cases))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "questions": str(args.questions),
        "question_sha256": hashlib.sha256(args.questions.read_bytes()).hexdigest(),
        "count": len(answers),
        "answers": answers,
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已冻结 {len(answers)} 条回答：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
