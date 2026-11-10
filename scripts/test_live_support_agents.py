"""Run synthetic signed evidence cases inside the dedicated support AI container.

No customer accounts or business writes. Credentials are read only from its environment.
Use --in-process to test candidate source before switching the running service.
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import time

import httpx
from ai_service.config import settings


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-process", action="store_true")
    args = parser.parse_args()
    transport = None
    if args.in_process:
        from ai_service.api.integrations import router
        from fastapi import FastAPI

        logger = logging.getLogger("uvicorn.error")
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler())
        settings.integration_agents_enabled = True
        app = FastAPI()
        app.include_router(router)
        transport = httpx.ASGITransport(app=app)
    evidence = [
        {
            "content": "订单 AGENTTEST7 当前状态：已取消；订单金额 14.70 SGD。未提供物流轨迹。",
            "title": "合成测试订单",
            "reference": "order://buzud/AGENTTEST7",
        },
        {
            "content": "客服邮箱为 support@example.test。",
            "title": "测试联系方式",
            "reference": "faq://buzud/contact",
            "keywords": ["联系", "邮箱", "contact", "email"],
        },
        {
            "content": "未拆封且凭证齐全的商品可在收货后 7 天内申请退货，最终由客服审核。",
            "title": "测试售后政策",
            "reference": "faq://buzud/aftersales",
            "keywords": ["退货", "售后", "return"],
        },
        {
            "content": "本地配送通常需要 3-7 个工作日，实际以物流情况为准。",
            "title": "测试配送政策",
            "reference": "faq://buzud/delivery",
            "keywords": ["配送", "shipping", "delivery"],
        },
    ]
    cases = [
        ("compound", "buzud", "订单状态和金额是什么，退货条件是什么，客服邮箱是什么？"),
        ("english-delivery", "buzud", "How long does shipping take?"),
        (
            "oms-cancelled-payment",
            "oms",
            "订单状态是什么，还需要付款吗，退款到账了吗？",
        ),
    ]
    results = []
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000", transport=transport, timeout=28
    ) as client:
        for name, source, question in cases:
            items = (
                evidence
                if source == "buzud"
                else [{**evidence[0], "reference": "order://oms/AGENTTEST7"}]
            )
            payload = {
                "message": question,
                "subject": "synthetic-agent-test",
                "evidence": items,
            }
            raw = json.dumps(payload, ensure_ascii=False).encode()
            timestamp = str(int(time.time()))
            secret = (
                settings.buzud_integration_secret
                if source == "buzud"
                else settings.oms_integration_secret
            )
            signature = hmac.new(
                secret.encode(),
                source.encode() + b"\n" + timestamp.encode() + b"\n" + raw,
                hashlib.sha256,
            ).hexdigest()
            started = time.monotonic()
            response = await client.post(
                f"/v1/integrations/{source}/chat",
                content=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-Support-Timestamp": timestamp,
                    "X-Support-Signature": signature,
                },
            )
            body = response.json()
            result = {
                "case": name,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "run_id": response.headers.get("X-Support-Agent-Run"),
                "roles": response.headers.get("X-Support-Agent-Roles"),
                "degraded": response.headers.get("X-Support-Agent-Degraded"),
                "reply": body,
            }
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            assert response.status_code == 200
            assert result["run_id"] and result["degraded"] == "false", name
            if name == "compound":
                assert set(result["roles"].split(",")) == {
                    "order",
                    "knowledge",
                    "aftersales",
                }
                assert all(
                    t in body["answer"]
                    for t in ("已取消", "14.70", "未拆封", "support@example.test")
                )
            elif name == "english-delivery":
                assert (
                    "day" in body["answer"].lower()
                    and "3" in body["answer"]
                    and "7" in body["answer"]
                )
            else:
                assert (
                    "不需要继续付款" in body["answer"]
                    and "不代表退款已经到账" in body["answer"]
                )
    print(json.dumps({"passed": len(results), "synthetic_evidence": True}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
