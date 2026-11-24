#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_customer_service_zh.py")
SPEC = importlib.util.spec_from_file_location("build_customer_service_zh", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BuilderTests(unittest.TestCase):
    def test_normalize_and_redact(self) -> None:
        text, count = MODULE.redact_pii(
            "订单号 123456789，手机13800138000，邮箱 user@example.com，身份证11010519491231002X"
        )
        self.assertEqual(count, 4)
        self.assertIn("<ORDER_ID>", text)
        self.assertIn("<PHONE>", text)
        self.assertIn("<EMAIL>", text)
        self.assertIn("<ID_CARD>", text)

    def test_finrag_parser(self) -> None:
        text = (
            "[客户问题]\n问题\n"
            "[客服A的回答开始]\n回答A\n[客服A的回答结束]\n"
            "[客服B的回答开始]\n回答B\n[客服B的回答结束]"
        )
        self.assertEqual(MODULE.parse_finrag_prompt(text), ("问题", "回答A", "回答B"))

    def test_unsupported_action_is_penalized(self) -> None:
        self.assertGreater(MODULE.grounding_penalty("订单怎么了", "我已为您联系快递并申请补偿"), 0)
        self.assertEqual(
            MODULE.grounding_penalty("订单怎么了", "请提供订单号，我需要查询后才能确认状态"),
            0,
        )

    def test_messages_are_merged_and_grounded(self) -> None:
        normalized = MODULE.normalize_messages(
            [
                {"role": "assistant", "content": "欢迎"},
                {"role": "user", "content": "我的订单在哪里?"},
                {"role": "assistant", "content": "请提供订单号。"},
                {"role": "assistant", "content": "我需要查询后确认。"},
                {"role": "user", "content": "好的"},
            ]
        )
        self.assertIsNotNone(normalized)
        messages, _ = normalized
        self.assertEqual([item["role"] for item in messages], ["system", "user", "assistant"])
        self.assertIn("查询后确认", messages[-1]["content"])

    def test_exact_and_near_dedup(self) -> None:
        deduper = MODULE.PromptDeduper(max_hamming=3)
        self.assertIsNone(deduper.add("我的订单 123456 怎么还没有发货?"))
        self.assertEqual(
            deduper.add("我的订单 987654 怎么还没有发货?"),
            "duplicate_exact_user",
        )

    def test_infinity_filter(self) -> None:
        self.assertIsNone(
            MODULE.infinity_filter_reason(
                "你好,我的订单一直没有发货,请问怎么处理?",
                "请提供订单号,我需要查询后才能确认状态。",
            )
        )
        self.assertEqual(
            MODULE.infinity_filter_reason(
                "题目:一件商品15元,买三件多少钱?",
                "答案是45元。",
            ),
            "infinity_not_direct_support",
        )


if __name__ == "__main__":
    unittest.main()
