#!/usr/bin/env python3
"""用 Bright Data Lazada Scraper 拉取商品数据。

用法（在仓库根目录）：
    .venv/bin/python scripts/brightdata_lazada_pull.py --limit 10
    .venv/bin/python scripts/brightdata_lazada_pull.py --limit 10 --urls-file urls.txt

密钥读取顺序：环境变量 BRIGHT_DATA_API_KEY → .env 同名项。
脚本不会打印密钥，也不把密钥写入输出文件。
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

DATASET_ID = "gd_m6gjtfmeh43we6cqc"
BASE_URL = "https://api.brightdata.com/datasets/v3"
OUTPUT_DIR = Path("docs/data-imports")
URL_PATTERN = re.compile(r"https://www\.lazada\.[a-z.]+/products/[A-Za-z0-9._-]+\.html")


def load_key() -> str:
    key = os.environ.get("BRIGHT_DATA_API_KEY", "").strip()
    if not key:
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("BRIGHT_DATA_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key or key.startswith("replace_with"):
        sys.exit(
            "缺少 BRIGHT_DATA_API_KEY。\n"
            "请在仓库根目录的 .env 中新增一行：\n"
            "  BRIGHT_DATA_API_KEY=<你的密钥>\n"
            "保存后重新执行本脚本，密钥不会出现在任何输出文件里。"
        )
    return key


def collect_urls(limit: int) -> list[str]:
    found: list[str] = []
    for path in sorted(OUTPUT_DIR.glob("lazada-*.json")):
        found.extend(URL_PATTERN.findall(path.read_text(encoding="utf-8")))
    unique = list(dict.fromkeys(found))
    if not unique:
        sys.exit("没有在 docs/data-imports 中找到 Lazada 商品链接，请用 --urls-file 指定")
    return unique[:limit]


def read_urls_file(path: Path, limit: int) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        payload = json.loads(text)
        items = payload if isinstance(payload, list) else payload.get("urls", [])
        urls = [item for item in items if isinstance(item, str)]
    else:
        urls = [line.strip() for line in text.splitlines() if line.strip()]
    return urls[:limit]


def scrape(
    client: httpx.Client, key: str, urls: list[str], *, max_wait: float = 600.0
) -> list[dict[str, object]]:
    response = client.post(
        f"{BASE_URL}/scrape",
        params={
            "dataset_id": DATASET_ID,
            "notify": "false",
            "include_errors": "true",
        },
        headers={"Authorization": f"Bearer {key}"},
        json={"input": [{"url": url} for url in urls], "limit_per_input": None},
    )
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    snapshot_id = payload.get("snapshot_id") if isinstance(payload, dict) else None
    if not snapshot_id:
        raise RuntimeError(f"未识别的响应：{str(payload)[:200]}")

    print(f"异步任务 {snapshot_id}，等待结果…")
    deadline = time.time() + max_wait
    while time.time() < deadline:
        progress = client.get(
            f"{BASE_URL}/progress/{snapshot_id}",
            headers={"Authorization": f"Bearer {key}"},
        )
        progress.raise_for_status()
        state = progress.json().get("status")
        if state == "ready":
            break
        if state == "failed":
            raise RuntimeError("Bright Data 任务失败")
        time.sleep(4)
    else:
        raise TimeoutError("等待 Bright Data 结果超时")

    result = client.get(
        f"{BASE_URL}/snapshot/{snapshot_id}",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {key}"},
    )
    result.raise_for_status()
    data = result.json()
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def parse_ld_json(raw: object) -> dict[str, object]:
    """从数据集记录的 ld_json 字段里提取 Product 节点。"""

    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except ValueError:
            return {}
    else:
        parsed = raw

    candidates = parsed if isinstance(parsed, list) else [parsed]
    for item in candidates:
        if isinstance(item, dict) and item.get("@type") == "Product":
            offers = item.get("offers") if isinstance(item.get("offers"), dict) else {}
            seller = offers.get("seller") if isinstance(offers.get("seller"), dict) else {}
            brand = item.get("brand") if isinstance(item.get("brand"), dict) else {}
            rating = item.get("aggregateRating")
            rating = rating if isinstance(rating, dict) else {}
            return {
                "name": item.get("name", ""),
                "brand": brand.get("name", ""),
                "sku": item.get("sku", ""),
                "category": item.get("category", ""),
                "description": item.get("description", ""),
                "availability": str(offers.get("availability", "")).rsplit("/", 1)[-1],
                "seller": seller.get("name", ""),
                "rating": rating.get("ratingValue", ""),
                "reviews": rating.get("reviewCount", ""),
                "canonical_url": item.get("url", ""),
            }
    return {}


def normalize(record: dict[str, object]) -> dict[str, object]:
    product = parse_ld_json(record.get("ld_json", ""))
    if not product:
        return {}
    product["source_url"] = record.get("url", "")
    product["page_title"] = record.get("page_title", "")
    return product


def pick(record: dict[str, object], *names: str) -> str:
    for name in names:
        value = record.get(name)
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
    return ""


def summarize(records: list[dict[str, object]]) -> None:
    print(f"\n收到 {len(records)} 条记录\n")
    print(f"{'标题':<34} {'价格':>10} {'币种':<5} {'店铺':<16}")
    print("-" * 72)
    for record in records:
        title = pick(record, "name", "title")[:32]
        price = pick(record, "final_price", "price", "itemDiscountPrice")
        currency = pick(record, "currency", "priceCurrency")
        seller = pick(record, "seller_name", "sellerName", "seller")[:14]
        print(f"{title:<34} {price:>10} {currency:<5} {seller:<16}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bright Data Lazada 商品拉取")
    parser.add_argument("--limit", type=int, default=10, help="最多拉取多少条")
    parser.add_argument("--urls-file", type=Path, default=None, help="商品链接文件（txt 或 json）")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-wait", type=float, default=600.0, help="单批最长等待秒数")
    args = parser.parse_args()

    key = load_key()
    urls = (
        read_urls_file(args.urls_file, args.limit)
        if args.urls_file
        else collect_urls(args.limit)
    )
    print(f"本次提交 {len(urls)} 个商品链接")

    records: list[dict[str, object]] = []
    with httpx.Client(timeout=args.timeout, follow_redirects=False) as client:
        for start in range(0, len(urls), args.batch_size):
            chunk = urls[start : start + args.batch_size]
            print(f"批次 {start // args.batch_size + 1}：{len(chunk)} 个链接")
            records.extend(
                scrape(client, key, chunk, max_wait=args.max_wait)
            )

    products = [item for item in (normalize(record) for record in records) if item]
    unparsed = [record.get("url", "") for record in records if not normalize(record)]
    print(f"解析出 {len(products)} 个商品，未解析 {len(unparsed)} 条")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).astimezone().strftime("%Y%m%d-%H%M%S")
    output = OUTPUT_DIR / f"brightdata-lazada-{stamp}.json"
    output.write_text(
        json.dumps(
            {
                "date": stamp,
                "provider": "BRIGHT_DATA",
                "dataset_id": DATASET_ID,
                "requested": len(urls),
                "received": len(records),
                "parsed": len(products),
                "source_urls": urls,
                "products": products,
                "unparsed": unparsed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summarize(products)
    with_desc = sum(1 for item in products if str(item.get("description", "")).strip())
    with_brand = sum(1 for item in products if str(item.get("brand", "")).strip())
    print(f"\n有描述 {with_desc}　有品牌 {with_brand}")
    print(f"数据：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
