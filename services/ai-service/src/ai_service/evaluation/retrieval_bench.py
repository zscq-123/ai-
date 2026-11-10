"""检索层对比：关键词、向量与带范围门控的混合检索。

用法：
    PYTHONPATH=src python -m ai_service.evaluation.retrieval_bench

默认用例是开发回归集；只有显式传入冻结文件并标注时，结果才可作为保留集成绩。
"""

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_service.domain.ports import KnowledgeRetriever
from ai_service.infrastructure.embeddings import LazyFastEmbedEmbedder
from ai_service.infrastructure.hybrid_knowledge import HybridKnowledgeRetriever
from ai_service.infrastructure.intent_knowledge import IntentExampleKnowledgeRetriever
from ai_service.infrastructure.local_knowledge import (
    DEFAULT_ENTRIES,
    KnowledgeEntry,
    LocalKnowledgeRetriever,
    load_entries,
)
from ai_service.infrastructure.semantic_scope import SemanticScopeGuard
from ai_service.infrastructure.vector_knowledge import VectorKnowledgeRetriever

SERVICE_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = SERVICE_ROOT.parents[1]
DEFAULT_CASES = SERVICE_ROOT / "evaluation" / "retrieval_cases.jsonl"
DEFAULT_REPORT = REPO_ROOT / "docs" / "检索对比.md"


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    expect: str
    category: str


@dataclass(frozen=True)
class Verdict:
    case: RetrievalCase
    top1: str
    hit: bool


def load_cases(path: Path) -> list[RetrievalCase]:
    cases: list[RetrievalCase] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        payload: object = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError(f"第 {line_number} 行必须是 JSON 对象")
        query = payload.get("query")
        expect = payload.get("expect")
        category = payload.get("category", "未分类")
        if not isinstance(query, str) or not isinstance(expect, str):
            raise ValueError(f"第 {line_number} 行缺少 query 或 expect")
        if not isinstance(category, str):
            raise ValueError(f"第 {line_number} 行 category 必须是字符串")
        cases.append(RetrievalCase(query, expect, category))
    return cases


async def judge(retriever: KnowledgeRetriever, cases: list[RetrievalCase]) -> list[Verdict]:
    verdicts: list[Verdict] = []
    for case in cases:
        results = await retriever.search(case.query, limit=1)
        top1 = results[0][1].reference if results else ""
        verdicts.append(Verdict(case, top1, top1 == case.expect))
    return verdicts


def render(name: str, verdicts: list[Verdict]) -> list[str]:
    hits = sum(1 for verdict in verdicts if verdict.hit)
    lines = [f"## {name}", "", f"命中 {hits}/{len(verdicts)}", ""]
    lines.extend(
        [
            "| 类别 | 查询 | 期望 | 实际首条 | 结果 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for verdict in verdicts:
        mark = "通过" if verdict.hit else "未命中"
        lines.append(
            f"| {verdict.case.category} | {verdict.case.query} | "
            f"{verdict.case.expect or '（应拒绝）'} | "
            f"{verdict.top1 or '（空）'} | {mark} |"
        )
    lines.append("")
    return lines


async def run(
    cases_path: Path,
    report_path: Path,
    model: str,
    knowledge_file: Path | None = None,
    min_score: float = 0.45,
    set_label: str = "开发回归集（可能用于调参，不代表独立盲测）",
) -> int:
    cases = load_cases(cases_path)

    entries: tuple[KnowledgeEntry, ...] = DEFAULT_ENTRIES
    if knowledge_file is not None:
        entries = entries + load_entries(knowledge_file)
        print(f"追加知识 {len(entries) - len(DEFAULT_ENTRIES)} 条，共 {len(entries)} 条")

    keyword = LocalKnowledgeRetriever(entries, allow_bigram_fallback=False)
    embedder = LazyFastEmbedEmbedder(model, local_files_only=True)
    vector = VectorKnowledgeRetriever(embedder, entries=entries, min_score=min_score, fallback=None)
    base_hybrid = SemanticScopeGuard(
        HybridKnowledgeRetriever(
            VectorKnowledgeRetriever(
                embedder, entries=entries, min_score=min_score, fallback=None
            ),
            keyword,
            primary_weight=1.2,
        ),
        embedder,
        supported_texts=[text for entry in entries for text in entry.embedding_texts],
    )
    hybrid = IntentExampleKnowledgeRetriever(embedder, fallback=base_hybrid)

    keyword_verdicts = await judge(keyword, cases)
    vector_verdicts = await judge(vector, cases)
    hybrid_verdicts = await judge(hybrid, cases)

    keyword_hits = sum(1 for verdict in keyword_verdicts if verdict.hit)
    vector_hits = sum(1 for verdict in vector_verdicts if verdict.hit)
    hybrid_hits = sum(1 for verdict in hybrid_verdicts if verdict.hit)
    negative_count = sum(1 for case in cases if not case.expect)
    hybrid_rejections = sum(
        1 for verdict in hybrid_verdicts if not verdict.case.expect and verdict.hit
    )

    lines = [
        "# 检索层对比：关键词 vs 向量",
        "",
        f"- 生成时间：{datetime.now(UTC).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 嵌入模型：`{model}`",
        f"- 知识条目：{len(entries)} 条",
        f"- 数据集性质：{set_label}",
        f"- 用例数：{len(cases)}（其中应拒绝 {negative_count} 条）",
        "",
        "| 方案 | 首条命中率 |",
        "| --- | --- |",
        f"| 关键词检索 | {keyword_hits / len(cases) * 100:.1f}%（{keyword_hits}/{len(cases)}）|",
        f"| 向量检索 | {vector_hits / len(cases) * 100:.1f}%（{vector_hits}/{len(cases)}）|",
        f"| 意图样例路由 + 基础检索降级 | "
        f"{hybrid_hits / len(cases) * 100:.1f}%（{hybrid_hits}/{len(cases)}）|",
        f"| 混合检索应拒绝准确率 | "
        f"{(hybrid_rejections / negative_count * 100 if negative_count else 100):.1f}%"
        f"（{hybrid_rejections}/{negative_count}）|",
        "",
    ]
    lines.extend(render("关键词检索明细", keyword_verdicts))
    lines.extend(render("向量检索明细", vector_verdicts))
    lines.extend(render("意图样例路由 + 基础检索降级明细", hybrid_verdicts))

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"关键词检索 {keyword_hits}/{len(cases)}")
    print(f"向量检索   {vector_hits}/{len(cases)}")
    print(f"混合检索   {hybrid_hits}/{len(cases)}")
    print(f"报告：{report_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="检索层对比")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument("--knowledge-file", type=Path, default=None)
    parser.add_argument("--min-score", type=float, default=0.45)
    parser.add_argument(
        "--set-label",
        default="开发回归集（可能用于调参，不代表独立盲测）",
    )
    args = parser.parse_args()
    return asyncio.run(
        run(
            args.cases,
            args.report,
            args.model,
            knowledge_file=args.knowledge_file,
            min_score=args.min_score,
            set_label=args.set_label,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
