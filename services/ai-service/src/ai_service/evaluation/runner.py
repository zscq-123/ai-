"""客服对话回归评测。

对运行中的 ai-service 逐条发送用例，检查意图、风控门禁、引用、语气与长度，
输出控制台摘要和 Markdown 报告。

用法：
    PYTHONPATH=src python -m ai_service.evaluation.runner \
        --base-url http://127.0.0.1:8099

前置条件：ai-service 已在目标地址启动。
"""

import argparse
import asyncio
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter
from uuid import NAMESPACE_DNS, uuid5

import httpx

SERVICE_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = SERVICE_ROOT.parents[1]
DEFAULT_CASES = SERVICE_ROOT / "evaluation" / "cases.jsonl"
DEFAULT_REPORT = REPO_ROOT / "docs" / "评测报告.md"
DEFAULT_RESULT = SERVICE_ROOT / "evaluation" / "last-run.json"

BANNED_PHRASES = ("亲，", "亲~", "宝宝", "稍等", "马上到", "保证", "绝对")
MAX_CONCURRENCY = 4


@dataclass(frozen=True)
class Expectation:
    intent: str
    requires_human: bool = False
    requires_confirmation: bool = False
    citations_min: int = 0
    must_include_any: tuple[str, ...] = ()
    must_not_include: tuple[str, ...] = ()
    citation_ref: str = ""
    max_chars: int = 120


@dataclass(frozen=True)
class Case:
    id: str
    message: str
    authenticated: bool
    expect: Expectation


@dataclass(frozen=True)
class Observation:
    intent: str
    answer: str
    citations: int
    citation_refs: tuple[str, ...]
    requires_human: bool
    requires_confirmation: bool


@dataclass(frozen=True)
class Result:
    case: Case
    observation: Observation | None
    latency_ms: float
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def _as_str(payload: dict[str, object], key: str, where: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{where}: 字段 {key} 必须是字符串")
    return value


def _as_bool(payload: dict[str, object], key: str, default: bool) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    return default


def _as_int(payload: dict[str, object], key: str, default: int) -> int:
    value = payload.get(key, default)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default


def _as_str_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key, [])
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str))
    return ()


def _parse_expectation(raw: object, where: str) -> Expectation:
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: expect 必须是对象")
    return Expectation(
        intent=_as_str(raw, "intent", where),
        requires_human=_as_bool(raw, "requires_human", False),
        requires_confirmation=_as_bool(raw, "requires_confirmation", False),
        citations_min=_as_int(raw, "citations_min", 0),
        must_include_any=_as_str_tuple(raw, "must_include_any"),
        must_not_include=_as_str_tuple(raw, "must_not_include"),
        citation_ref=_as_str(raw, "citation_ref", where) if "citation_ref" in raw else "",
        max_chars=_as_int(raw, "max_chars", 120),
    )


def load_cases(path: Path) -> list[Case]:
    cases: list[Case] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        payload: object = json.loads(raw_line)
        if not isinstance(payload, dict):
            raise ValueError(f"第 {line_number} 行必须是 JSON 对象")
        where = f"第 {line_number} 行"
        cases.append(
            Case(
                id=_as_str(payload, "id", where),
                message=_as_str(payload, "message", where),
                authenticated=_as_bool(payload, "authenticated", False),
                expect=_parse_expectation(payload.get("expect"), where),
            )
        )
    return cases


def evaluate(case: Case, observation: Observation) -> tuple[str, ...]:
    failures: list[str] = []
    expect = case.expect
    answer = observation.answer

    if observation.intent != expect.intent:
        failures.append(f"意图 {observation.intent}，期望 {expect.intent}")
    if observation.requires_human != expect.requires_human:
        failures.append(f"转人工 {observation.requires_human}，期望 {expect.requires_human}")
    if observation.requires_confirmation != expect.requires_confirmation:
        failures.append(
            f"需确认 {observation.requires_confirmation}，期望 {expect.requires_confirmation}"
        )
    if observation.citations < expect.citations_min:
        failures.append(f"引用 {observation.citations} 条，期望至少 {expect.citations_min} 条")
    if expect.citation_ref:
        if not observation.citation_refs:
            failures.append("没有引用，无法判断检索命中")
        elif expect.citation_ref not in observation.citation_refs:
            joined_refs = "、".join(observation.citation_refs)
            failures.append(f"引用未包含 {expect.citation_ref}，实际 {joined_refs}")
    if expect.must_include_any and not any(phrase in answer for phrase in expect.must_include_any):
        joined = "、".join(expect.must_include_any)
        failures.append(f"未包含任一关键词：{joined}")
    hits = [phrase for phrase in expect.must_not_include if phrase in answer]
    if hits:
        failures.append(f"出现禁用表述：{'、'.join(hits)}")
    if len(answer) > expect.max_chars:
        failures.append(f"回答 {len(answer)} 字，超过 {expect.max_chars} 字")
    tone_hits = [phrase for phrase in BANNED_PHRASES if phrase in answer]
    if tone_hits:
        failures.append(f"语气违规：{'、'.join(tone_hits)}")
    return tuple(failures)


def _auth_headers(secret: str) -> dict[str, str]:
    customer_id = uuid5(NAMESPACE_DNS, "eval-customer")
    content = f"{customer_id}\n".encode()
    signature = hmac.new(secret.encode(), content, hashlib.sha256).hexdigest()
    return {
        "X-Nova-Customer-Id": str(customer_id),
        "X-Nova-Context-Signature": signature,
    }


async def run_case(
    client: httpx.AsyncClient, case: Case, secret: str, gate: asyncio.Semaphore
) -> Result:
    headers = _auth_headers(secret) if case.authenticated else {}
    async with gate:
        started = perf_counter()
        try:
            response = await client.post(
                "/v1/support/chat",
                json={"message": case.message},
                headers=headers,
            )
            elapsed = (perf_counter() - started) * 1000
            if response.status_code != 200:
                return Result(case, None, elapsed, (f"HTTP {response.status_code}",))
            body: object = response.json()
        except httpx.HTTPError as error:
            return Result(case, None, 0.0, (f"请求失败：{error}",))

    if not isinstance(body, dict):
        return Result(case, None, elapsed, ("响应不是 JSON 对象",))

    citations = body.get("citations")
    citation_refs = _extract_refs(citations)
    observation = Observation(
        intent=_as_str(body, "intent", case.id),
        answer=_as_str(body, "answer", case.id),
        citations=len(citation_refs),
        citation_refs=citation_refs,
        requires_human=_as_bool(body, "requires_human", False),
        requires_confirmation=_as_bool(body, "requires_confirmation", False),
    )
    return Result(case, observation, elapsed, evaluate(case, observation))


def _extract_refs(citations: object) -> tuple[str, ...]:
    if not isinstance(citations, list):
        return ()
    refs: list[str] = []
    for item in citations:
        if isinstance(item, dict):
            reference = item.get("reference")
            if isinstance(reference, str):
                refs.append(reference)
    return tuple(refs)


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * ratio)))
    return ordered[index]


def _rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "-"
    return f"{numerator / denominator * 100:.1f}%"


def render_report(results: list[Result], base_url: str) -> str:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    latencies = [result.latency_ms for result in results if result.observation is not None]
    intent_ok = sum(
        1
        for result in results
        if result.observation is not None and result.observation.intent == result.case.expect.intent
    )
    safety_ok = sum(
        1
        for result in results
        if result.observation is not None
        and result.observation.requires_human == result.case.expect.requires_human
        and result.observation.requires_confirmation == result.case.expect.requires_confirmation
    )
    citation_ok = sum(
        1
        for result in results
        if result.observation is not None
        and result.observation.citations >= result.case.expect.citations_min
    )
    ranked_cases = [r for r in results if r.case.expect.citation_ref]
    ranked_ok = sum(
        1
        for result in ranked_cases
        if result.observation is not None
        and result.observation.citation_refs[:1] == (result.case.expect.citation_ref,)
    )
    tone_ok = sum(
        1
        for result in results
        if result.observation is not None
        and not any(phrase in result.observation.answer for phrase in BANNED_PHRASES)
    )
    length_ok = sum(
        1
        for result in results
        if result.observation is not None
        and len(result.observation.answer) <= result.case.expect.max_chars
    )
    answered = len(latencies)

    lines = [
        "# 客服对话评测报告",
        "",
        f"- 生成时间：{datetime.now(UTC).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 被测服务：`{base_url}`",
        f"- 用例总数：{total}",
        "",
        "## 一、总览",
        "",
        "| 指标 | 结果 |",
        "| --- | --- |",
        f"| 通过率 | {_rate(passed, total)}（{passed}/{total}）|",
        f"| 意图准确率 | {_rate(intent_ok, total)}（{intent_ok}/{total}）|",
        f"| 风控门禁准确率 | {_rate(safety_ok, total)}（{safety_ok}/{total}）|",
        f"| 引用命中率 | {_rate(citation_ok, total)}（{citation_ok}/{total}）|",
        f"| 引用排序（首条即正确）| {_rate(ranked_ok, len(ranked_cases))}"
        f"（{ranked_ok}/{len(ranked_cases)}）|",
        f"| 语气合规率 | {_rate(tone_ok, answered)}（{tone_ok}/{answered}）|",
        f"| 长度合规率 | {_rate(length_ok, answered)}（{length_ok}/{answered}）|",
        f"| 延迟 P50 / P95 | {_percentile(latencies, 0.5):.0f} ms / "
        f"{_percentile(latencies, 0.95):.0f} ms |",
        f"| 平均延迟 | {mean(latencies):.0f} ms |" if latencies else "| 平均延迟 | - |",
        "",
        "## 二、用例明细",
        "",
        "| 用例 | 问题 | 意图 | 延迟 | 结果 | 失败原因 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for result in results:
        intent = result.observation.intent if result.observation else "-"
        verdict = "通过" if result.passed else "未通过"
        reasons = "；".join(result.failures) if result.failures else "-"
        message = result.case.message.replace("|", "／")
        lines.append(
            f"| {result.case.id} | {message} | {intent} | {result.latency_ms:.0f} ms | "
            f"{verdict} | {reasons} |"
        )

    failures = [result for result in results if not result.passed]
    lines.extend(["", "## 三、失败用例回答", ""])
    if not failures:
        lines.append("无。")
    for result in failures:
        lines.append(f"### {result.case.id}　{result.case.message}")
        lines.append("")
        if result.observation is None:
            lines.append(f"- 未取得回答：{'；'.join(result.failures)}")
        else:
            lines.append(f"- 回答：{result.observation.answer}")
            lines.append(f"- 问题：{'；'.join(result.failures)}")
        lines.append("")

    return "\n".join(lines) + "\n"


def render_console(results: list[Result]) -> str:
    passed = sum(1 for result in results if result.passed)
    lines = [
        f"{'用例':<6}{'结果':<6}{'意图':<14}{'延迟':>9}  失败原因",
        "-" * 96,
    ]
    for result in results:
        intent = result.observation.intent if result.observation else "-"
        verdict = "PASS" if result.passed else "FAIL"
        reasons = "；".join(result.failures)
        lines.append(
            f"{result.case.id:<6}{verdict:<6}{intent:<14}{result.latency_ms:>7.0f}ms  {reasons}"
        )
    lines.append("-" * 96)
    lines.append(f"通过 {passed}/{len(results)}")
    return "\n".join(lines)


async def run(base_url: str, cases_path: Path, secret: str) -> list[Result]:
    cases = load_cases(cases_path)
    gate = asyncio.Semaphore(MAX_CONCURRENCY)
    # trust_env=False：避免被系统代理接管，导致本机地址返回 502
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0, trust_env=False) as client:
        health = await client.get("/health")
        health.raise_for_status()
        return await asyncio.gather(*(run_case(client, case, secret, gate) for case in cases))


def main() -> int:
    parser = argparse.ArgumentParser(description="客服对话回归评测")
    parser.add_argument("--base-url", default="http://127.0.0.1:8099")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--secret", default="local-ai-context-secret")
    parser.add_argument("--min-pass", type=float, default=0.8)
    args = parser.parse_args()

    results = asyncio.run(run(args.base_url, args.cases, args.secret))

    print(render_console(results))

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(results, args.base_url), encoding="utf-8")

    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(
        json.dumps(
            [
                {
                    "id": result.case.id,
                    "message": result.case.message,
                    "passed": result.passed,
                    "intent": result.observation.intent if result.observation else None,
                    "latency_ms": round(result.latency_ms, 1),
                    "failures": list(result.failures),
                }
                for result in results
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n报告：{args.report}")
    passed = sum(1 for result in results if result.passed)
    return 0 if passed / len(results) >= args.min_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
