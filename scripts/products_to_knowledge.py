#!/usr/bin/env python3
"""把抓取到的商品数据转成知识库 JSONL。

输入：docs/data-imports/brightdata-products-*.json 或 brightdata-lazada-*.json
输出：services/ai-service/knowledge/products.jsonl

用法：
    .venv/bin/python scripts/products_to_knowledge.py
    .venv/bin/python scripts/products_to_knowledge.py --input <文件> --limit 50
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

import httpx

INPUT_DIR = Path("docs/data-imports")
OUTPUT = Path("services/ai-service/knowledge/products.jsonl")
MAX_DESCRIPTION = 240
STOPWORDS = {"the", "and", "with", "for", "pcs", "pack", "new", "original"}


def latest_input() -> Path:
    candidates = sorted(
        list(INPUT_DIR.glob("brightdata-products-*.json"))
        + list(INPUT_DIR.glob("brightdata-lazada-*.json")),
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        raise SystemExit("没有找到抓取结果，先运行 brightdata_lazada_pull.py")
    return candidates[-1]


def keywords_for(product: dict[str, object]) -> list[str]:
    text = " ".join(
        str(product.get(field, "")) for field in ("name", "brand", "category")
    )
    tokens = [
        token.strip("[]()|,").lower()
        for token in re.split(r"[\s/>&|]+", text)
        if len(token.strip("[]()|,")) >= 3
    ]
    unique: list[str] = []
    for token in tokens:
        if token in STOPWORDS or token in unique:
            continue
        unique.append(token)
    brand = str(product.get("brand", "")).strip()
    if brand and brand.lower() not in unique:
        unique.insert(0, brand.lower())
    return unique[:12]


def load_deepseek_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("缺少 DEEPSEEK_API_KEY，无法翻译")


def translate(client: httpx.Client, key: str, text: str) -> str:
    payload = {
        "model": "deepseek-flash",
        "temperature": 0.1,
        "max_tokens": 800,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是电商商品资料翻译。把输入翻译成简洁中文，保留品牌、型号和关键规格，"
                    "只输出一行，不超过 80 字，不要任何解释。"
                ),
            },
            {"role": "user", "content": text},
        ],
    }
    for _ in range(3):
        response = client.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        answer = str(data["choices"][0]["message"]["content"] or "").strip()
        if answer:
            return re.sub(r"\s+", " ", answer)
        time.sleep(0.5)
    raise ValueError("模型返回空内容")


def content_for(product: dict[str, object]) -> str:
    description = str(product.get("description", "")).strip()
    description = re.sub(r"\s+", " ", description)[:MAX_DESCRIPTION]
    parts = [f"商品：{product.get('name', '')}"]
    if product.get("brand"):
        parts.append(f"品牌：{product['brand']}")
    if product.get("category"):
        parts.append(f"类目：{str(product['category']).replace(' > ', '/')}")
    if description:
        parts.append(description)
    return "。".join(parts[:3]) + ("。" + description if description else "。")


def reference_for(product: dict[str, object]) -> str:
    sku = str(product.get("sku", "")).strip()
    if sku:
        return f"product://{sku}"
    url = str(product.get("source_url", "")).strip()
    match = re.search(r"-i(\d+)-", url)
    return f"product://i{match.group(1)}" if match else f"product://{abs(hash(url))}"


def main() -> int:
    parser = argparse.ArgumentParser(description="商品数据转知识条目")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--translate", action="store_true", help="把商品资料译成中文")
    args = parser.parse_args()

    source = args.input or latest_input()
    payload = json.loads(source.read_text(encoding="utf-8"))
    products = payload.get("products") if isinstance(payload, dict) else None
    if not isinstance(products, list):
        raise SystemExit(f"{source} 里没有 products 数组")

    client = httpx.Client(timeout=60.0)
    key = load_deepseek_key() if args.translate else ""

    seen: set[str] = set()
    lines: list[str] = []
    for product in products[: args.limit]:
        if not isinstance(product, dict) or not str(product.get("name", "")).strip():
            continue
        reference = reference_for(product)
        if reference in seen:
            continue
        seen.add(reference)
        content = content_for(product)
        if args.translate:
            try:
                content = translate(client, key, content)
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
                print(f"  翻译失败，保留原文：{error}")
        lines.append(
            json.dumps(
                {
                    "content": content,
                    "reference": reference,
                    "title": "商品资料",
                    "keywords": keywords_for(product),
                },
                ensure_ascii=False,
            )
        )

    client.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"来源：{source}")
    print(f"写入 {len(lines)} 条 → {args.output}")
    if lines:
        print(f"示例：{json.loads(lines[0])['content'][:100]}")
    return 0 if lines else 1


if __name__ == "__main__":
    raise SystemExit(main())
