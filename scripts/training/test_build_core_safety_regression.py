import tempfile
import unittest
from pathlib import Path

from build_core_safety_regression import (
    assert_independent,
    build_cases,
    build_combined_cases,
    write_cases,
)
from evaluate_mlx_customer_service import load_cases


class BuildCoreSafetyRegressionTest(unittest.TestCase):
    def test_builds_165_unique_independent_cases(self) -> None:
        cases = build_cases()
        self.assertEqual(len(cases), 165)
        self.assertEqual(len({case["id"] for case in cases}), 165)
        assert_independent(cases)

    def test_combines_to_200_unique_cases(self) -> None:
        cases = build_combined_cases(build_cases())
        self.assertEqual(len(cases), 200)
        self.assertEqual(len({case["id"] for case in cases}), 200)

    def test_generated_file_is_accepted_by_evaluator(self) -> None:
        cases = build_cases()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "core-safety.jsonl")
            write_cases(path, cases)
            loaded = load_cases(path)
        self.assertEqual(len(loaded), 165)


if __name__ == "__main__":
    unittest.main()
