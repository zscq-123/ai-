#!/usr/bin/env python3
"""Audit rendered chat-template token lengths for an MLX JSONL SFT dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from mlx_lm.utils import load_tokenizer


def percentile(values: list[int], quantile: float) -> int:
    values = sorted(values)
    return values[min(int((len(values) - 1) * quantile), len(values) - 1)]


def summarize(values: list[int]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "mean": round(mean(values), 2),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "maximum": max(values),
    }


def audit(dataset: Path, model: Path, max_seq_length: int) -> dict[str, Any]:
    tokenizer = load_tokenizer(str(model))
    full_lengths: list[int] = []
    prompt_lengths: list[int] = []
    answer_lengths: list[int] = []
    source_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    over_limit = 0
    prompt_at_or_over_limit = 0
    minimum_visible_answer = 10**9
    longest: list[tuple[int, str, str]] = []
    for split in ("train", "valid", "test"):
        path = dataset / f"{split}.jsonl"
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                messages = row["messages"]
                prompt_tokens = tokenizer.apply_chat_template(
                    messages[:-1], tokenize=True, add_generation_prompt=True
                )
                full_tokens = tokenizer.apply_chat_template(messages, tokenize=True)
                prompt_length = len(prompt_tokens)
                full_length = len(full_tokens)
                answer_length = max(full_length - prompt_length, 0)
                visible_answer = max(min(full_length, max_seq_length) - prompt_length, 0)
                full_lengths.append(full_length)
                prompt_lengths.append(prompt_length)
                answer_lengths.append(answer_length)
                source = str((row.get("meta") or {}).get("source_dataset") or "unknown")
                source_counts[source] += 1
                split_counts[split] += 1
                over_limit += full_length > max_seq_length
                prompt_at_or_over_limit += prompt_length >= max_seq_length
                minimum_visible_answer = min(minimum_visible_answer, visible_answer)
                longest.append((full_length, str(row.get("id") or ""), split))
    longest.sort(reverse=True)
    return {
        "dataset": str(dataset.resolve()),
        "model": str(model.resolve()),
        "max_seq_length": max_seq_length,
        "records": len(full_lengths),
        "split_counts": dict(split_counts),
        "source_counts": dict(source_counts),
        "rendered_full_tokens": summarize(full_lengths),
        "rendered_prompt_tokens": summarize(prompt_lengths),
        "assistant_tokens": summarize(answer_lengths),
        "records_over_max_seq_length": over_limit,
        "records_with_prompt_at_or_over_max_seq_length": prompt_at_or_over_limit,
        "minimum_visible_assistant_tokens_after_truncation": minimum_visible_answer,
        "longest_records": [
            {"tokens": length, "id": record_id, "split": split}
            for length, record_id, split in longest[:20]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--max-seq-length", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.dataset.resolve(), args.model.resolve(), args.max_seq_length)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["records_with_prompt_at_or_over_max_seq_length"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
