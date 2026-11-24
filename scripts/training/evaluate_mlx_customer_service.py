#!/usr/bin/env python3
"""Run deterministic, text-level regression checks against an MLX chat model."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = REPO_ROOT / "configs/training/customer_service_regression_v1.jsonl"
DEFAULT_SEED = REPO_ROOT / "services/ai-service/datasets/scripts_sft_seed.jsonl"

GLOBAL_FORBIDDEN = (
    "<tool_call>",
    "</tool_call>",
    "fromFunction",
    "<|im_start|>",
    "<|im_end|>",
    "亲亲",
    "亲~",
    "宝宝",
    "嗷",
    "已为您查询",
    "已经为您查询",
    "已为您催件",
    "已经为您催件",
    "已为您退款",
    "已经为您退款",
    "已为您转接",
    "已经为您转接",
)

REQUIRED_PHRASE_ALIASES: dict[str, tuple[str, ...]] = {
    "运输中": ("运输中", "运输途中"),
    "尚未发货": ("尚未发货", "还未发货", "还没有发货"),
    "没有发货": ("没有发货", "还未发货", "尚未发货"),
    "还没有发货": ("还没有发货", "还未发货", "尚未发货"),
    "无法查询": ("无法查询", "无法直接查询"),
    "无法确认": ("无法确认", "无法直接确认", "无法实时确认"),
    "实时库存": ("实时库存", "实时数据", "实时页面显示"),
    "商品页": ("商品页", "商品详情页"),
    "缺货": (
        "缺货",
        "暂无库存",
        "没有库存",
        "已无库存",
        "无库存",
    ),
    "支付选项": ("支付选项", "支付方式", "分期选项"),
    "订单详情": ("订单详情", "我的订单", "具体订单"),
    "订单号": ("订单号", "快递单号"),
    "核对": ("核对", "确认准确信息", "确认准确价格"),
    "14:30": ("14:30", "14点30分", "14 点 30 分"),
    "15:42": ("15:42", "15点42分", "15 点 42 分"),
    "已签收": ("已签收", "已经签收", "签收"),
    "失败": ("失败", "未通过"),
    "不支持": ("不支持", "无法开具"),
    "补充地址": ("补充地址", "补充完整地址", "完善地址"),
    "处理中": ("处理中", "审核中"),
}

NEGATION_MARKERS = (
    "不能确认",
    "无法确认",
    "不能直接断定",
    "无法承诺",
    "不能承诺",
    "无法保证",
    "不能保证",
    "不能证明",
    "不能说明",
    "不代表",
    "不是",
    "并未",
    "尚未",
    "还未",
    "还没有",
    "没有",
    "未",
)

SUFFIX_NEGATION_MARKERS = (
    "不可用",
    "不适用",
    "无效",
    "不成立",
)


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    messages: tuple[dict[str, str], ...]
    expect: dict[str, Any]
    system_context: str | None = None


@dataclass(frozen=True)
class EvalResult:
    id: str
    category: str
    answer: str
    latency_ms: float
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def _string_list(value: object, field: str, where: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{where}: {field} 必须是字符串数组")
    return value


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    seen: set[str] = set()
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        where = f"{path}:{line_number}"
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise TypeError(f"{where}: 每行必须是 JSON 对象")
        case_id = payload.get("id")
        category = payload.get("category")
        raw_messages = payload.get("messages")
        expect = payload.get("expect", {})
        system_context = payload.get("system_context")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{where}: id 必须是非空字符串")
        if case_id in seen:
            raise ValueError(f"{where}: id 重复：{case_id}")
        if not isinstance(category, str) or not category:
            raise ValueError(f"{where}: category 必须是非空字符串")
        if not isinstance(raw_messages, list) or not raw_messages:
            raise ValueError(f"{where}: messages 必须是非空数组")
        messages: list[dict[str, str]] = []
        for message in raw_messages:
            if not isinstance(message, dict):
                raise TypeError(f"{where}: message 必须是对象")
            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str):
                raise ValueError(f"{where}: message 只支持 user/assistant 字符串内容")
            messages.append({"role": role, "content": content})
        if messages[-1]["role"] != "user":
            raise ValueError(f"{where}: 最后一条消息必须来自 user")
        if not isinstance(expect, dict):
            raise TypeError(f"{where}: expect 必须是对象")
        if system_context is not None and (
            not isinstance(system_context, str) or not system_context.strip()
        ):
            raise ValueError(f"{where}: system_context 必须是非空字符串")
        for field in (
            "must_include_any",
            "must_include_all",
            "must_not_include",
            "must_match_any",
            "must_not_match",
        ):
            _string_list(expect.get(field), field, where)
        seen.add(case_id)
        cases.append(
            EvalCase(case_id, category, tuple(messages), expect, system_context)
        )
    if not cases:
        raise ValueError(f"{path}: 没有评测用例")
    return cases


def load_system_prompt(seed_path: Path) -> str:
    first_line = next(
        (
            line
            for line in seed_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ),
        "",
    )
    if not first_line:
        raise ValueError(f"{seed_path}: 没有可读取的 SFT 样本")
    payload = json.loads(first_line)
    messages = payload.get("messages", [])
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "system":
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content
    raise ValueError(f"{seed_path}: 首条样本没有 system prompt")


def _repetition_failure(answer: str) -> str | None:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    counts = Counter(lines)
    repeated_lines = [
        line for line, count in counts.items() if len(line) >= 2 and count >= 3
    ]
    if repeated_lines:
        return f"重复行至少 3 次：{repeated_lines[0][:24]}"
    repeated_fragment = re.search(r"(.{2,12})(?:\1){4,}", answer)
    if repeated_fragment:
        return f"短片段异常重复：{repeated_fragment.group(1)[:24]}"
    return None


def contains_required_phrase(answer: str, phrase: str) -> bool:
    """Match a small audited set of equivalent status expressions."""
    return any(alias in answer for alias in REQUIRED_PHRASE_ALIASES.get(phrase, (phrase,)))


def find_unnegated_phrases(answer: str, phrases: list[str]) -> list[str]:
    """Return forbidden phrases asserted positively, not merely denied nearby."""
    hits: list[str] = []
    for phrase in phrases:
        start = 0
        asserted = False
        while True:
            index = answer.find(phrase, start)
            if index < 0:
                break
            prefix = answer[max(0, index - 12) : index]
            suffix = answer[index + len(phrase) : index + len(phrase) + 12]
            is_negated = any(marker in prefix for marker in NEGATION_MARKERS) or any(
                marker in suffix for marker in SUFFIX_NEGATION_MARKERS
            )
            if not is_negated:
                asserted = True
                break
            start = index + len(phrase)
        if asserted:
            hits.append(phrase)
    return hits


def evaluate_answer(case: EvalCase, answer: str) -> tuple[str, ...]:
    failures: list[str] = []
    clean_answer = answer.strip()
    expect = case.expect
    if not clean_answer:
        return ("回答为空",)

    global_hits = [phrase for phrase in GLOBAL_FORBIDDEN if phrase in clean_answer]
    if global_hits:
        failures.append(f"出现全局禁用内容：{'、'.join(global_hits)}")

    repetition = _repetition_failure(clean_answer)
    if repetition:
        failures.append(repetition)

    max_chars = expect.get("max_chars", 180)
    min_chars = expect.get("min_chars", 2)
    if not isinstance(max_chars, int) or isinstance(max_chars, bool):
        raise TypeError(f"{case.id}: max_chars 必须是整数")
    if not isinstance(min_chars, int) or isinstance(min_chars, bool):
        raise TypeError(f"{case.id}: min_chars 必须是整数")
    if len(clean_answer) > max_chars:
        failures.append(f"回答 {len(clean_answer)} 字，超过 {max_chars} 字")
    if len(clean_answer) < min_chars:
        failures.append(f"回答 {len(clean_answer)} 字，少于 {min_chars} 字")

    must_include_any = _string_list(
        expect.get("must_include_any"), "must_include_any", case.id
    )
    if must_include_any and not any(
        contains_required_phrase(clean_answer, phrase) for phrase in must_include_any
    ):
        failures.append(f"未包含任一关键词：{'、'.join(must_include_any)}")

    must_include_all = _string_list(
        expect.get("must_include_all"), "must_include_all", case.id
    )
    missing = [
        phrase
        for phrase in must_include_all
        if not contains_required_phrase(clean_answer, phrase)
    ]
    if missing:
        failures.append(f"缺少关键词：{'、'.join(missing)}")

    must_not_include = _string_list(
        expect.get("must_not_include"), "must_not_include", case.id
    )
    forbidden_hits = find_unnegated_phrases(clean_answer, must_not_include)
    if forbidden_hits:
        failures.append(f"出现禁用表述：{'、'.join(forbidden_hits)}")

    must_match_any = _string_list(
        expect.get("must_match_any"), "must_match_any", case.id
    )
    if must_match_any and not any(
        re.search(pattern, clean_answer) for pattern in must_match_any
    ):
        failures.append("未匹配任一要求模式")

    must_not_match = _string_list(
        expect.get("must_not_match"), "must_not_match", case.id
    )
    matched_forbidden = [
        pattern for pattern in must_not_match if re.search(pattern, clean_answer)
    ]
    if matched_forbidden:
        failures.append(f"匹配禁用模式：{'、'.join(matched_forbidden)}")
    return tuple(failures)


def _render_markdown(
    *,
    label: str,
    model_path: str,
    adapter_path: str | None,
    enable_thinking: bool,
    results: list[EvalResult],
    elapsed_seconds: float,
) -> str:
    passed = sum(result.passed for result in results)
    total = len(results)
    category_totals = Counter(result.category for result in results)
    category_passed = Counter(result.category for result in results if result.passed)
    lines = [
        f"# 客服模型回归评测：{label}",
        "",
        f"- 模型：`{model_path}`",
        f"- 适配器：`{adapter_path or '无（基座）'}`",
        f"- 思考模式：`{'开启' if enable_thinking else '关闭'}`",
        f"- 通过：{passed}/{total}（{passed / total * 100:.1f}%）",
        f"- 总耗时：{elapsed_seconds:.2f} 秒",
        "",
        "## 分类结果",
        "",
        "| 分类 | 通过 | 总数 |",
        "| --- | ---: | ---: |",
    ]
    for category in sorted(category_totals):
        lines.append(
            f"| {category} | {category_passed[category]} | {category_totals[category]} |"
        )
    lines.extend(
        [
            "",
            "## 用例明细",
            "",
            "| 用例 | 分类 | 结果 | 失败原因 | 回答 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for result in results:
        status = "通过" if result.passed else "失败"
        failures = "；".join(result.failures).replace("|", "\\|") or "-"
        answer = result.answer.replace("\n", "<br>").replace("|", "\\|")
        lines.append(
            f"| {result.id} | {result.category} | {status} | {failures} | {answer} |"
        )
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> int:
    from mlx_lm import generate, load

    cases = load_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    system_prompt = load_system_prompt(args.seed)
    model, tokenizer = load(args.model, adapter_path=args.adapter)
    results: list[EvalResult] = []
    run_started = perf_counter()
    for index, case in enumerate(cases, start=1):
        case_system_prompt = system_prompt
        if case.system_context:
            case_system_prompt += "\n\n" + case.system_context.strip()
        messages = [
            {"role": "system", "content": case_system_prompt},
            *case.messages,
        ]
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=args.enable_thinking,
        )
        started = perf_counter()
        answer = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=args.max_tokens,
            verbose=False,
        ).strip()
        latency_ms = (perf_counter() - started) * 1000
        failures = evaluate_answer(case, answer)
        results.append(EvalResult(case.id, case.category, answer, latency_ms, failures))
        status = "PASS" if not failures else "FAIL"
        print(f"[{index:02d}/{len(cases):02d}] {status} {case.id} {latency_ms:.0f}ms")

    elapsed_seconds = perf_counter() - run_started
    passed = sum(result.passed for result in results)
    payload = {
        "label": args.label,
        "created_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "adapter": args.adapter,
        "enable_thinking": args.enable_thinking,
        "cases": str(args.cases),
        "summary": {
            "passed": passed,
            "total": len(results),
            "pass_rate": passed / len(results),
            "elapsed_seconds": elapsed_seconds,
        },
        "results": [asdict(result) | {"passed": result.passed} for result in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path = args.output.with_suffix(".md")
    markdown_path.write_text(
        _render_markdown(
            label=args.label,
            model_path=args.model,
            adapter_path=args.adapter,
            enable_thinking=args.enable_thinking,
            results=results,
            elapsed_seconds=elapsed_seconds,
        ),
        encoding="utf-8",
    )
    print(f"通过 {passed}/{len(results)}；JSON: {args.output}；报告: {markdown_path}")
    return 0 if passed / len(results) >= args.require_pass_rate else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--adapter")
    parser.add_argument(
        "--enable-thinking",
        action="store_true",
        help="启用模型思考模式；客服最终回复评测默认关闭",
    )
    parser.add_argument("--label", required=True)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=160)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--require-pass-rate", type=float, default=0.0)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
