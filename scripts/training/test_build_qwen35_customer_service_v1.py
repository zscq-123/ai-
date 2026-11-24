import unittest

from scripts.training.build_qwen35_customer_service_v1 import build, similarity


class BuildQwen35CustomerServiceV1Test(unittest.TestCase):
    def test_build_is_balanced_and_evaluation_disjoint(self) -> None:
        rows_by_split, manifest = build()
        self.assertEqual(sum(map(len, rows_by_split.values())), 1184)
        self.assertEqual(manifest["category_counts"]["prompt_injection_fact_forgery"], 160)
        self.assertEqual(manifest["category_counts"]["trusted_evidence_replay"], 256)
        audit = manifest["evaluation_prompt_audit"]
        self.assertEqual(audit["exact_matches"], [])
        self.assertEqual(audit["near_matches_at_or_above_limit"], [])
        self.assertLess(audit["maximum_similarity"], audit["near_overlap_limit"])

    def test_similarity_normalizes_dynamic_ids(self) -> None:
        left = "请查询订单 AB123456 的退款"
        right = "请查询订单 CD999999 的退款"
        self.assertGreater(similarity(left, right), 0.95)

    def test_every_split_is_nonempty(self) -> None:
        rows_by_split, _ = build()
        self.assertTrue(all(rows_by_split[split] for split in ("train", "valid", "test")))


if __name__ == "__main__":
    unittest.main()
