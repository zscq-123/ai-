import tempfile
import unittest
from collections import Counter
from pathlib import Path

from build_customer_service_hardening_v3 import build_rows, validate, write_rows


class BuildCustomerServiceHardeningV3Test(unittest.TestCase):
    def test_builds_balanced_held_out_rows(self) -> None:
        rows = build_rows()
        validate(rows)
        self.assertEqual(len(rows), 240)
        self.assertEqual(
            Counter(row["split"] for row in rows),
            {"train": 200, "valid": 20, "test": 20},
        )

    def test_writes_jsonl(self) -> None:
        rows = build_rows()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "hardening-v3.jsonl")
            write_rows(path, rows)
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 240)


if __name__ == "__main__":
    unittest.main()
