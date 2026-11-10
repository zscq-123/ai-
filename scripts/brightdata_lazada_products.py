#!/usr/bin/env python3
"""批量抓取 Lazada 商品详情并解析成结构化记录。

复用 picolah 的 Bright Data Web Unlocker 凭据，通过 scripts/brightdata_fetch.py 取页面，
再从 JSON-LD 的 Product 节点提取标题、品牌、类目、描述、库存与退货政策。

用法：
    .venv/bin/python scripts/brightdata_lazada_products.py --limit 15
    .venv/bin/python scripts/brightdata_lazada_products.py --limit 5 --urls-file urls.txt

输出：docs/data-imports/brightdata-products-<时间>.json
"""

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from brightdata_fetch import (  # noqa: E402
    DEFAULT_ENV,
    credentials,
    fetch,
    read_env,
    slug,
)

URLS_DIR = Path("docs/data-imports")
PAGES_DIR = URLS_DIR / "brightdata"
URL_PATTERN = re.compile(r"https://www\.lazada\.[a-z.]+/products/[A-Za-z0-9._-]+\.html")
LD_JSON = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)


def collect_urls(limit: int) -> list[str]:
    found: list[str] = []
    for path in sorted(URLS_DIR.glob("lazada-*.json")):
        found.extend(URL_PATTERN.findall(path.read_text(encoding="utf-8")))
    return list(dict.fromkeys(found))[:limit]


def parse_product(html: str, url: str) -> dict[str, object] | None:
    for block in LD_JSON.findall(html):
        if '"Product"' not in block:
            continue
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        offers = data.get("offers") if isinstance(data.get("offers"), dict) else {}
        seller = offers.get("seller") if isinstance(offers.get("seller"), dict) else {}
        brand = data.get("brand") if isinstance(data.get("brand"), dict) else {}
        rating = data.get("aggregateRating")
        rating = rating if isinstance(rating, dict) else {}

        return {
            "url": url,
            "name": data.get("name", ""),
            "brand": brand.get("name", ""),
            "sku": data.get("sku", ""),
            "category": data.get("category", ""),
            "description": data.get("description", ""),
            "availability": str(offers.get("availability", "")).rsplit("/", 1)[-1],
            "seller": seller.get("name", ""),
            "rating": rating.get("ratingValue", ""),
            "reviews": rating.get("reviewCount", ""),
            "image_count": len(data.get("image", []) or []),
        }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="批量抓取 Lazada 商品")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--urls-file", type=Path, default=None)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--country", default="sg")
    parser.add_argument("--interval", type=float, default=1.5)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    if args.urls_file:
        urls = [
            line.strip()
            for line in args.urls_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ][: args.limit]
    else:
        urls = collect_urls(args.limit)
    if not urls:
        sys.exit("没有可抓取的 URL")

    env = read_env(args.env_file)
    token, zone = credentials(env)
    print(f"zone={zone} token=***{token[-4:]}  目标 {len(urls)} 个商品")

    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []

    with httpx.Client(follow_redirects=False) as client:
        for index, url in enumerate(urls, start=1):
            try:
                html, size = fetch(
                    client,
                    token,
                    zone,
                    url,
                    country=args.country,
                    render=True,
                    timeout=args.timeout,
                )
            except (httpx.HTTPError, RuntimeError) as error:
                print(f"[{index}/{len(urls)}] 抓取失败 {url}：{error}")
                failures.append({"url": url, "error": str(error)})
                continue

            (PAGES_DIR / f"{slug(url)}.html").write_text(html, encoding="utf-8")
            record = parse_product(html, url)
            if record is None:
                print(f"[{index}/{len(urls)}] 无 JSON-LD　{size / 1024:.0f} KB")
                failures.append({"url": url, "error": "no product json-ld"})
            else:
                records.append(record)
                print(
                    f"[{index}/{len(urls)}] {str(record['name'])[:40]} "
                    f"| {record['brand']} | {record['category']}"
                )
            time.sleep(args.interval)

    stamp = datetime.now(UTC).astimezone().strftime("%Y%m%d-%H%M%S")
    output = URLS_DIR / f"brightdata-products-{stamp}.json"
    output.write_text(
        json.dumps(
            {
                "date": stamp,
                "provider": "BRIGHT_DATA_WEB_UNLOCKER",
                "zone": zone,
                "requested": len(urls),
                "parsed": len(records),
                "failures": failures,
                "products": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with_desc = sum(1 for r in records if str(r["description"]).strip())
    with_brand = sum(1 for r in records if str(r["brand"]).strip())
    print(
        f"\n解析成功 {len(records)}/{len(urls)}"
        f"　有描述 {with_desc}　有品牌 {with_brand}"
        f"　失败 {len(failures)}"
    )
    print(f"输出：{output}")
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
