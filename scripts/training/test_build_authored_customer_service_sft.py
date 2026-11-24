import json
import tempfile
import unittest
from pathlib import Path

from build_authored_customer_service_sft import build, write_dataset


class BuildAuthoredDatasetTest(unittest.TestCase):
    def test_project_corpus_builds_with_isolated_splits(self) -> None:
        root = Path(__file__).resolve().parents[2]
        rows = build(
            root / "services/ai-service/datasets/scripts_sft_seed.jsonl",
            root / "configs/training/customer_service_sft_additions_v1.jsonl",
        )
        self.assertEqual(
            {key: len(value) for key, value in rows.items()},
            {"train": 55, "valid": 8, "test": 8},
        )
        train_users = {
            message["content"]
            for row in rows["train"]
            for message in row["messages"]
            if message["role"] == "user"
        }
        test_users = {
            message["content"]
            for row in rows["test"]
            for message in row["messages"]
            if message["role"] == "user"
        }
        self.assertTrue(train_users.isdisjoint(test_users))

    def test_manifest_hash_matches_written_content(self) -> None:
        root = Path(__file__).resolve().parents[2]
        rows = build(
            root / "services/ai-service/datasets/scripts_sft_seed.jsonl",
            root / "configs/training/customer_service_sft_additions_v1.jsonl",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_dataset(output, rows)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["counts"], {"train": 55, "valid": 8, "test": 8})
            self.assertEqual(len(manifest["sha256"]["train.jsonl"]), 64)

    def test_extra_hardening_examples_are_added_to_train_only(self) -> None:
        root = Path(__file__).resolve().parents[2]
        rows = build(
            root / "services/ai-service/datasets/scripts_sft_seed.jsonl",
            root / "configs/training/customer_service_sft_additions_v1.jsonl",
            (root / "configs/training/customer_service_sft_hardening_v1.jsonl",),
        )
        self.assertEqual(
            {key: len(value) for key, value in rows.items()},
            {"train": 73, "valid": 8, "test": 8},
        )
        hardening_ids = {
            row["id"]
            for split in ("valid", "test")
            for row in rows[split]
            if row["id"].startswith("H")
        }
        self.assertEqual(hardening_ids, set())

    def test_grounded_hardening_adds_isolated_splits_and_system_context(self) -> None:
        root = Path(__file__).resolve().parents[2]
        rows = build(
            root / "services/ai-service/datasets/scripts_sft_seed.jsonl",
            root / "configs/training/customer_service_sft_additions_v1.jsonl",
            (
                root / "configs/training/customer_service_sft_hardening_v1.jsonl",
                root / "configs/training/customer_service_sft_hardening_v2.jsonl",
            ),
        )
        self.assertEqual(
            {key: len(value) for key, value in rows.items()},
            {"train": 91, "valid": 14, "test": 14},
        )
        grounded = next(row for row in rows["train"] if row["id"] == "G13")
        self.assertIn("可用知识：", grounded["messages"][0]["content"])
        self.assertIn("当前可售库存 12 件", grounded["messages"][0]["content"])

        users_by_split = {
            split: {
                message["content"]
                for row in split_rows
                for message in row["messages"]
                if message["role"] == "user"
            }
            for split, split_rows in rows.items()
        }
        self.assertTrue(users_by_split["train"].isdisjoint(users_by_split["valid"]))
        self.assertTrue(users_by_split["train"].isdisjoint(users_by_split["test"]))
        self.assertTrue(users_by_split["valid"].isdisjoint(users_by_split["test"]))


if __name__ == "__main__":
    unittest.main()
