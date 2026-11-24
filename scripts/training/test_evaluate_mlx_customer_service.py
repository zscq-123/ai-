import json
import tempfile
import unittest
from pathlib import Path

from evaluate_mlx_customer_service import EvalCase, evaluate_answer, load_cases


class EvaluateAnswerTest(unittest.TestCase):
    def test_accepts_grounded_clarification(self) -> None:
        case = EvalCase(
            "R01",
            "clarification",
            ({"role": "user", "content": "这件可以吗"},),
            {"must_include_any": ["商品", "链接"], "max_chars": 80},
        )
        self.assertEqual(
            evaluate_answer(case, "请把商品链接发来，我先核对具体信息。"), ()
        )

    def test_rejects_tool_collapse_and_fake_action(self) -> None:
        case = EvalCase("R02", "order", ({"role": "user", "content": "查订单"},), {})
        failures = evaluate_answer(case, "<tool_call>\n已为您查询到订单。")
        self.assertTrue(any("全局禁用" in failure for failure in failures))

    def test_rejects_repeated_line(self) -> None:
        case = EvalCase("R03", "order", ({"role": "user", "content": "查订单"},), {})
        failures = evaluate_answer(case, "请提供订单号\n请提供订单号\n请提供订单号")
        self.assertTrue(any("重复行" in failure for failure in failures))

    def test_accepts_negated_forbidden_status(self) -> None:
        case = EvalCase(
            "R04",
            "logistics",
            ({"role": "user", "content": "签收了吗"},),
            {
                "must_include_all": ["运输中"],
                "must_not_include": ["已经签收"],
            },
        )
        answer = "我不能确认订单已经签收。当前记录显示仍在运输途中，尚未签收。"
        self.assertEqual(evaluate_answer(case, answer), ())

    def test_rejects_positive_forbidden_status(self) -> None:
        case = EvalCase(
            "R05",
            "logistics",
            ({"role": "user", "content": "签收了吗"},),
            {"must_not_include": ["已经签收"]},
        )
        failures = evaluate_answer(case, "订单已经签收，您放心。")
        self.assertTrue(any("禁用表述" in failure for failure in failures))

    def test_accepts_forbidden_value_when_explicitly_rejected(self) -> None:
        case = EvalCase(
            "R05B",
            "price",
            ({"role": "user", "content": "299 元吗"},),
            {"must_not_include": ["299"]},
        )
        self.assertEqual(evaluate_answer(case, "299 元的价格暂不可用。"), ())

    def test_accepts_forbidden_claim_inside_audited_negation(self) -> None:
        case = EvalCase(
            "R05C",
            "policy",
            ({"role": "user", "content": "保证正品吗"},),
            {"must_not_include": ["百分百正品"]},
        )
        self.assertEqual(
            evaluate_answer(case, "当前证据不足，无法承诺百分百正品。"), ()
        )

    def test_accepts_audited_status_alias(self) -> None:
        case = EvalCase(
            "R06",
            "logistics",
            ({"role": "user", "content": "到哪了"},),
            {"must_include_all": ["运输中"]},
        )
        self.assertEqual(evaluate_answer(case, "订单仍在运输途中。"), ())

    def test_accepts_audited_query_inventory_and_time_aliases(self) -> None:
        cases_and_answers = (
            (
                EvalCase(
                    "R07",
                    "order",
                    ({"role": "user", "content": "查订单"},),
                    {"must_include_any": ["无法查询"]},
                ),
                "订单状态我无法直接查询。",
            ),
            (
                EvalCase(
                    "R08",
                    "inventory",
                    ({"role": "user", "content": "有库存吗"},),
                    {"must_include_any": ["缺货"]},
                ),
                "该规格当前已无库存。",
            ),
            (
                EvalCase(
                    "R09",
                    "payment",
                    ({"role": "user", "content": "什么时候付的款"},),
                    {"must_include_all": ["14:30"]},
                ),
                "支付时间为 14 点 30 分。",
            ),
        )
        for case, answer in cases_and_answers:
            with self.subTest(case=case.id):
                self.assertEqual(evaluate_answer(case, answer), ())

    def test_load_cases_rejects_duplicate_ids(self) -> None:
        payload = {
            "id": "R01",
            "category": "order",
            "messages": [{"role": "user", "content": "查订单"}],
            "expect": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "cases.jsonl")
            line = json.dumps(payload, ensure_ascii=False)
            path.write_text(f"{line}\n{line}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "id 重复"):
                load_cases(path)

    def test_load_cases_accepts_system_context(self) -> None:
        payload = {
            "id": "G01",
            "category": "grounded_inventory",
            "system_context": "可用知识：库存为 8 件。",
            "messages": [{"role": "user", "content": "还有多少件"}],
            "expect": {"must_include_all": ["8"]},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "cases.jsonl")
            path.write_text(
                json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            cases = load_cases(path)
        self.assertEqual(cases[0].system_context, "可用知识：库存为 8 件。")


if __name__ == "__main__":
    unittest.main()
