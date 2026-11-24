#!/usr/bin/env python3
"""Build a small, high-quality SFT corpus from project-authored examples."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = REPO_ROOT / "services/ai-service/datasets/scripts_sft_seed.jsonl"
DEFAULT_ADDITIONS = (
    REPO_ROOT / "configs/training/customer_service_sft_additions_v1.jsonl"
)
DEFAULT_OUTPUT = REPO_ROOT / "data/training/customer-service-authored-v1"
SPLITS = ("train", "valid", "test")
FORBIDDEN_ASSISTANT_PHRASES = (
    "亲亲",
    "亲~",
    "宝宝",
    "嗷",
    "<tool_call>",
    "fromFunction",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number}: 每行必须是 JSON 对象")
        rows.append(payload)
    return rows


def _system_prompt(seed_rows: list[dict[str, Any]]) -> str:
    for message in seed_rows[0].get("messages", []):
        if message.get("role") == "system" and isinstance(message.get("content"), str):
            return message["content"]
    raise ValueError("种子数据首条样本缺少 system prompt")


def _validate_messages(
    messages: object, where: str, require_system: bool
) -> list[dict[str, str]]:
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError(f"{where}: messages 至少需要两条")
    clean: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict):
            raise ValueError(f"{where}: message 必须是对象")
        role = item.get("role")
        content = item.get("content")
        allowed_roles = (
            {"system", "user", "assistant"} if require_system else {"user", "assistant"}
        )
        if (
            role not in allowed_roles
            or not isinstance(content, str)
            or not content.strip()
        ):
            raise ValueError(f"{where}: role/content 不合法")
        clean.append({"role": role, "content": content.strip()})
    if require_system and clean[0]["role"] != "system":
        raise ValueError(f"{where}: 第一条必须是 system")
    if clean[-1]["role"] != "assistant":
        raise ValueError(f"{where}: 最后一条必须是 assistant")
    return clean


def _assistant_text(messages: list[dict[str, str]]) -> str:
    return "\n".join(
        item["content"] for item in messages if item["role"] == "assistant"
    )


def _system_prompt_for_addition(
    row: dict[str, Any], base_prompt: str, where: str
) -> str:
    context = row.get("system_context")
    if context is None:
        return base_prompt
    if not isinstance(context, str) or not context.strip():
        raise ValueError(f"{where}: system_context 必须是非空字符串")
    return base_prompt + "\n\n" + context.strip()


def build(
    seed_path: Path,
    additions_path: Path,
    extra_additions: tuple[Path, ...] = (),
) -> dict[str, list[dict[str, Any]]]:
    seed_rows = _read_jsonl(seed_path)
    system_prompt = _system_prompt(seed_rows)
    output: dict[str, list[dict[str, Any]]] = {split: [] for split in SPLITS}
    seen_ids: set[str] = set()
    seen_conversations: set[str] = set()
    split_users: dict[str, set[str]] = {split: set() for split in SPLITS}

    def append(
        row_id: str,
        split: str,
        category: str,
        messages: list[dict[str, str]],
        source: str,
    ) -> None:
        if row_id in seen_ids:
            raise ValueError(f"样本 id 重复：{row_id}")
        if split not in SPLITS:
            raise ValueError(f"{row_id}: split 必须是 {SPLITS}")
        assistant = _assistant_text(messages)
        hits = [phrase for phrase in FORBIDDEN_ASSISTANT_PHRASES if phrase in assistant]
        if hits:
            raise ValueError(f"{row_id}: assistant 含禁用内容：{hits}")
        fingerprint = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        if fingerprint in seen_conversations:
            raise ValueError(f"{row_id}: 对话内容重复")
        user_text = "\n".join(
            item["content"] for item in messages if item["role"] == "user"
        )
        for other_split, users in split_users.items():
            if other_split != split and user_text in users:
                raise ValueError(f"{row_id}: 用户文本跨 split 重复")
        seen_ids.add(row_id)
        seen_conversations.add(fingerprint)
        split_users[split].add(user_text)
        output[split].append(
            {
                "id": row_id,
                "messages": messages,
                "meta": {"category": category, "source": source},
            }
        )

    for index, row in enumerate(seed_rows, start=1):
        messages = _validate_messages(
            row.get("messages"), f"seed:{index}", require_system=True
        )
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        row_id = str(meta.get("card_id") or f"seed-{index:03d}") + f"-{index:03d}"
        category = str(meta.get("scenario") or "project_seed")
        append(row_id, "train", category, messages, "scripts_sft_seed")

    for addition_path in (additions_path, *extra_additions):
        for index, row in enumerate(_read_jsonl(addition_path), start=1):
            where = f"{addition_path.name}:{index}"
            row_id = row.get("id")
            split = row.get("split")
            category = row.get("category")
            if not all(
                isinstance(value, str) and value for value in (row_id, split, category)
            ):
                raise ValueError(f"{where}: id/split/category 必须是非空字符串")
            messages = _validate_messages(
                row.get("messages"), where, require_system=False
            )
            addition_system_prompt = _system_prompt_for_addition(
                row, system_prompt, where
            )
            append(
                row_id,
                split,
                category,
                [{"role": "system", "content": addition_system_prompt}, *messages],
                addition_path.stem,
            )
    return output


def write_dataset(
    output_dir: Path, rows_by_split: dict[str, list[dict[str, Any]]]
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    counts: dict[str, int] = {}
    categories: Counter[str] = Counter()
    for split in SPLITS:
        path = output_dir / f"{split}.jsonl"
        content = "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows_by_split[split]
        )
        path.write_text(content, encoding="utf-8")
        hashes[path.name] = hashlib.sha256(content.encode()).hexdigest()
        counts[split] = len(rows_by_split[split])
        categories.update(row["meta"]["category"] for row in rows_by_split[split])
    manifest = {
        "dataset": output_dir.name,
        "counts": counts,
        "sha256": hashes,
        "categories": dict(sorted(categories.items())),
        "sources": sorted(
            {row["meta"]["source"] for split in SPLITS for row in rows_by_split[split]}
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--additions", type=Path, default=DEFAULT_ADDITIONS)
    parser.add_argument("--extra-additions", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows_by_split = build(args.seed, args.additions, tuple(args.extra_additions))
    write_dataset(args.output, rows_by_split)
    print(" ".join(f"{split}={len(rows_by_split[split])}" for split in SPLITS))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
