#!/usr/bin/env python3
"""Exercise NOVA's live inventory, order, logistics, and payment tools."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import psycopg
from ai_service.infrastructure.commerce_tools import CommerceSupportTools

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO_ROOT / "data/training/evaluations/nova-live-commerce-tools-20261103.json"
)
MERCHANT_ID = UUID("20000000-0000-0000-0000-000000000001")
CUSTOMER_ID = UUID("91000000-0000-0000-0000-000000000001")
OTHER_CUSTOMER_ID = UUID("91000000-0000-0000-0000-000000000002")
PRODUCT_ID = UUID("92000000-0000-0000-0000-000000000001")
SKU_IN_STOCK_ID = UUID("93000000-0000-0000-0000-000000000001")
SKU_OUT_OF_STOCK_ID = UUID("93000000-0000-0000-0000-000000000002")
SHIPPED_ORDER_ID = UUID("94000000-0000-0000-0000-000000000001")
PENDING_ORDER_ID = UUID("94000000-0000-0000-0000-000000000002")
REFUND_ORDER_ID = UUID("94000000-0000-0000-0000-000000000003")
SHIPPED_ORDER_NO = "NOACC202611030001"
PENDING_ORDER_NO = "NOACC202611030002"
REFUND_ORDER_NO = "NOACC202611030003"


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def _assert_contains(values: list[str], *required: str) -> None:
    joined = "\n".join(values)
    missing = [value for value in required if value not in joined]
    if missing:
        raise AssertionError(f"missing {missing}; received: {joined}")


def _check(name: str, action: Any) -> Check:
    try:
        detail = action()
    except Exception as exc:  # noqa: BLE001 - acceptance report must record failures
        return Check(name, False, f"{type(exc).__name__}: {exc}")
    return Check(name, True, str(detail))


def _seed(connection: psycopg.Connection[Any]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into customers(id,email,display_name,password_hash,status,created_at,updated_at)
            values
              (%s,'acceptance-1@nova.invalid','验收客户一','not-used','ACTIVE',now(),now()),
              (%s,'acceptance-2@nova.invalid','验收客户二','not-used','ACTIVE',now(),now())
            """,
            (CUSTOMER_ID, OTHER_CUSTOMER_ID),
        )
        cursor.execute(
            """
            insert into products(id,merchant_id,category_id,name,subtitle,status,created_at,updated_at)
            values (%s,%s,'10000000-0000-0000-0000-000000000001',
                    'NOVA 实时工具验收商品','仅用于隔离验收','ACTIVE',now(),now())
            """,
            (PRODUCT_ID, MERCHANT_ID),
        )
        cursor.execute(
            """
            insert into product_skus(id,product_id,sku_code,title,sale_price,market_price,available_stock)
            values
              (%s,%s,'ACCEPT-LIVE-7','验收现货规格',777.00,888.00,7),
              (%s,%s,'ACCEPT-LIVE-0','验收缺货规格',666.00,777.00,0)
            """,
            (SKU_IN_STOCK_ID, PRODUCT_ID, SKU_OUT_OF_STOCK_ID, PRODUCT_ID),
        )
        cursor.execute(
            """
            insert into orders(id,order_no,customer_id,merchant_id,status,total_amount,
                               idempotency_key,created_at,paid_at)
            values
              (%s,%s,%s,%s,'SHIPPED',777.00,'accept-live-1',now()-interval '3 hours',now()-interval '2 hours'),
              (%s,%s,%s,%s,'PENDING_PAYMENT',666.00,'accept-live-2',now()-interval '2 hours',null),
              (%s,%s,%s,%s,'REFUND_PENDING',555.00,'accept-live-3',now()-interval '1 hour',now()-interval '50 minutes')
            """,
            (
                SHIPPED_ORDER_ID,
                SHIPPED_ORDER_NO,
                CUSTOMER_ID,
                MERCHANT_ID,
                PENDING_ORDER_ID,
                PENDING_ORDER_NO,
                CUSTOMER_ID,
                MERCHANT_ID,
                REFUND_ORDER_ID,
                REFUND_ORDER_NO,
                CUSTOMER_ID,
                MERCHANT_ID,
            ),
        )
        cursor.execute(
            """
            insert into order_shipments(order_id,carrier_code,carrier_name,tracking_no,status,
                                        latest_event,shipped_at,updated_at)
            values (%s,'SF','顺丰速运','SF-ACCEPT-001','OUT_FOR_DELIVERY',
                    '快件正在派送，请保持电话畅通',now()-interval '90 minutes',now())
            """,
            (SHIPPED_ORDER_ID,),
        )
    connection.commit()


def _cleanup(connection: psycopg.Connection[Any]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "delete from order_shipments where order_id in (%s,%s,%s)",
            (SHIPPED_ORDER_ID, PENDING_ORDER_ID, REFUND_ORDER_ID),
        )
        cursor.execute(
            "delete from orders where id in (%s,%s,%s)",
            (SHIPPED_ORDER_ID, PENDING_ORDER_ID, REFUND_ORDER_ID),
        )
        cursor.execute(
            "delete from product_skus where id in (%s,%s)",
            (SKU_IN_STOCK_ID, SKU_OUT_OF_STOCK_ID),
        )
        cursor.execute("delete from products where id=%s", (PRODUCT_ID,))
        cursor.execute(
            "delete from customers where id in (%s,%s)",
            (CUSTOMER_ID, OTHER_CUSTOMER_ID),
        )
    connection.commit()


def _count_fixture_rows(connection: psycopg.Connection[Any]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select
              (select count(*) from customers where id in (%s,%s)) +
              (select count(*) from products where id=%s) +
              (select count(*) from product_skus where id in (%s,%s)) +
              (select count(*) from orders where id in (%s,%s,%s)) +
              (select count(*) from order_shipments where order_id=%s)
            """,
            (
                CUSTOMER_ID,
                OTHER_CUSTOMER_ID,
                PRODUCT_ID,
                SKU_IN_STOCK_ID,
                SKU_OUT_OF_STOCK_ID,
                SHIPPED_ORDER_ID,
                PENDING_ORDER_ID,
                REFUND_ORDER_ID,
                SHIPPED_ORDER_ID,
            ),
        )
        return int(cursor.fetchone()[0])


async def _live_checks(base_url: str, secret: str) -> list[Check]:
    tools = CommerceSupportTools(base_url, secret, timeout_seconds=5.0)
    checks: list[Check] = []

    async def lookup(message: str, **scope: Any) -> list[tuple[str, Any]]:
        return await tools.lookup(message, **scope)

    async def record_lookup(
        name: str,
        message: str,
        required: tuple[str, ...],
        references: tuple[str, ...],
        **scope: Any,
    ) -> None:
        try:
            evidence = await lookup(message, **scope)
            contents = [content for content, _ in evidence]
            refs = [citation.reference for _, citation in evidence]
            _assert_contains(contents, *required)
            missing_refs = [ref for ref in references if ref not in refs]
            if missing_refs:
                raise AssertionError(
                    f"missing references {missing_refs}; received: {refs}"
                )
            checks.append(Check(name, True, f"contents={contents}; references={refs}"))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check(name, False, f"{type(exc).__name__}: {exc}"))

    async with httpx.AsyncClient(
        base_url=base_url, timeout=5.0, trust_env=False
    ) as client:
        health = await client.get("/actuator/health")
        checks.append(
            Check(
                "commerce_api_health",
                health.status_code == 200 and health.json().get("status") == "UP",
                f"status={health.status_code}; body={health.text}",
            )
        )

        invalid = await client.post(
            "/api/internal/support/evidence",
            headers={"X-Nova-Tool-Signature": "00" * 32},
            json={
                "message": "查询库存",
                "customerId": None,
                "merchantId": str(MERCHANT_ID),
                "productId": str(PRODUCT_ID),
                "skuId": str(SKU_IN_STOCK_ID),
            },
        )
        checks.append(
            Check(
                "invalid_signature_rejected",
                invalid.status_code == 401,
                f"status={invalid.status_code}",
            )
        )

    await record_lookup(
        "inventory_in_stock",
        "验收现货规格库存还有多少？",
        ("验收现货规格", "库存 7 件"),
        (f"inventory://{SKU_IN_STOCK_ID}",),
        merchant_id=MERCHANT_ID,
        product_id=PRODUCT_ID,
        sku_id=SKU_IN_STOCK_ID,
    )
    await record_lookup(
        "inventory_out_of_stock",
        "验收缺货规格还有现货吗？",
        ("验收缺货规格", "库存 0 件", "缺货"),
        (f"inventory://{SKU_OUT_OF_STOCK_ID}",),
        merchant_id=MERCHANT_ID,
        product_id=PRODUCT_ID,
        sku_id=SKU_OUT_OF_STOCK_ID,
    )
    await record_lookup(
        "order_customer_scoped",
        f"订单 {SHIPPED_ORDER_NO} 当前订单状态是什么？",
        (SHIPPED_ORDER_NO, "已发货", "777.00"),
        (f"order://{SHIPPED_ORDER_NO}",),
        customer_id=CUSTOMER_ID,
        merchant_id=MERCHANT_ID,
    )
    await record_lookup(
        "logistics_live_status",
        f"订单 {SHIPPED_ORDER_NO} 的物流到哪了？",
        ("顺丰速运", "SF-ACCEPT-001", "派送中"),
        (f"logistics://{SHIPPED_ORDER_NO}",),
        customer_id=CUSTOMER_ID,
        merchant_id=MERCHANT_ID,
    )
    await record_lookup(
        "payment_paid_status",
        f"订单 {SHIPPED_ORDER_NO} 的支付状态是什么？",
        (SHIPPED_ORDER_NO, "已支付", "支付时间"),
        (f"payment-status://{SHIPPED_ORDER_NO}",),
        customer_id=CUSTOMER_ID,
        merchant_id=MERCHANT_ID,
    )
    await record_lookup(
        "payment_pending_status",
        f"订单 {PENDING_ORDER_NO} 的付款状态是什么？",
        (PENDING_ORDER_NO, "待付款"),
        (f"payment-status://{PENDING_ORDER_NO}",),
        customer_id=CUSTOMER_ID,
        merchant_id=MERCHANT_ID,
    )
    await record_lookup(
        "refund_pending_status",
        f"订单 {REFUND_ORDER_NO} 的退款到账了吗？",
        (REFUND_ORDER_NO, "已支付", "退款状态为处理中"),
        (f"payment-status://{REFUND_ORDER_NO}",),
        customer_id=CUSTOMER_ID,
        merchant_id=MERCHANT_ID,
    )

    wrong_customer = await lookup(
        f"订单 {SHIPPED_ORDER_NO} 的支付状态是什么？",
        customer_id=OTHER_CUSTOMER_ID,
        merchant_id=MERCHANT_ID,
    )
    checks.append(
        Check(
            "cross_customer_order_blocked",
            wrong_customer == [],
            f"evidence={wrong_customer}",
        )
    )
    no_identity = await lookup(
        f"订单 {SHIPPED_ORDER_NO} 的物流到哪了？",
        merchant_id=MERCHANT_ID,
    )
    checks.append(
        Check(
            "anonymous_order_blocked",
            no_identity == [],
            f"evidence={no_identity}",
        )
    )
    return checks


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# NOVA 真实商城工具验收",
        "",
        f"- 时间：{payload['created_at']}",
        f"- Commerce API：`{payload['base_url']}`",
        f"- 隔离数据库：`{payload['database_name']}`",
        f"- 通过：{payload['summary']['passed']}/{payload['summary']['total']}",
        "",
        "| 检查 | 结果 | 证据 |",
        "| --- | --- | --- |",
    ]
    for check in payload["checks"]:
        status = "通过" if check["passed"] else "失败"
        detail = check["detail"].replace("|", "\\|").replace("\n", "<br>")
        lines.append(f"| {check['name']} | {status} | {detail} |")
    lines.extend(
        [
            "",
            "说明：本验收使用真实 PostgreSQL 记录、Spring Commerce API、HMAC 签名接口和 AI 服务的 CommerceSupportTools 客户端。",
            "测试数据使用固定专用 UUID，验收后已从隔离数据库清理。该结果不代表生产供应商或生产数据库已接通。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18082")
    parser.add_argument("--secret", default="local-support-tool-secret")
    parser.add_argument(
        "--database-url",
        default=(
            "postgresql://commerce:commerce_local@127.0.0.1:55432/"
            "commerce_acceptance_20261103_1500"
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    checks: list[Check] = []
    with psycopg.connect(args.database_url) as connection:
        try:
            _cleanup(connection)
            _seed(connection)
            checks.extend(asyncio.run(_live_checks(args.base_url, args.secret)))
        finally:
            _cleanup(connection)
        remaining = _count_fixture_rows(connection)
        checks.append(
            Check(
                "fixture_cleanup",
                remaining == 0,
                f"remaining_fixture_rows={remaining}",
            )
        )

    passed = sum(check.passed for check in checks)
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "database_name": args.database_url.rsplit("/", 1)[-1],
        "summary": {
            "passed": passed,
            "total": len(checks),
            "pass_rate": passed / len(checks),
        },
        "checks": [asdict(check) for check in checks],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = args.output.with_suffix(".md")
    markdown.write_text(_markdown(payload), encoding="utf-8")
    print(f"通过 {passed}/{len(checks)}；JSON: {args.output}；报告: {markdown}")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
