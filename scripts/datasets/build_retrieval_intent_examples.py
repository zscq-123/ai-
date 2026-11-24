"""从已降级为开发集的检索用例构建运行时意图样例。"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_ROOT = REPO_ROOT / "services/ai-service/evaluation"
SOURCES = (
    EVALUATION_ROOT / "retrieval_cases.jsonl",
    EVALUATION_ROOT / "retrieval_holdout_200.jsonl",
    EVALUATION_ROOT / "retrieval_holdout_v2_200.jsonl",
    EVALUATION_ROOT / "retrieval_holdout_v3_200.jsonl",
)
OUTPUT = (
    REPO_ROOT
    / "services/ai-service/src/ai_service/resources/retrieval_intent_examples.jsonl"
)


def main() -> int:
    records: list[dict[str, str]] = []
    queries: set[str] = set()
    for source in SOURCES:
        for line_number, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            payload = json.loads(raw)
            query = payload["query"]
            if query in queries:
                raise ValueError(f"重复查询：{source.name}:{line_number}: {query}")
            queries.add(query)
            records.append({"query": query, "reference": payload["expect"]})

    if len(records) != 624:
        raise ValueError(f"意图样例应为 624 条，实际 {len(records)} 条")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"写入 {len(records)} 条：{OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
