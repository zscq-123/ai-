import tempfile
import unittest
from collections import Counter
from pathlib import Path

from build_customer_service_web_hardening_v1 import build_rows, validate, write_rows


class BuildCustomerServiceWebHardeningV1Test(unittest.TestCase):
    def test_builds_balanced_rows_from_three_sources(self) -> None:
        rows = build_rows()
        validate(rows)
        self.assertEqual(len(rows), 300)
        self.assertEqual(
            Counter(row["split"] for row in rows),
            {"train": 250, "valid": 25, "test": 25},
        )
        self.assertEqual(len({row["source"]["dataset"] for row in rows}), 3)

    def test_writes_jsonl(self) -> None:
        rows = build_rows()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "web-hardening-v1.jsonl")
            write_rows(path, rows)
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 300)


if __name__ == "__main__":
    unittest.main()
