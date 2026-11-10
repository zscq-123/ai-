#!/usr/bin/env python3
"""复用 picolah 的 Bright Data 凭据抓取网页。

默认从 ~/Documents/ChatGPT/picolah/.env 读取 BRIGHTDATA_API_TOKEN / BRIGHTDATA_ZONE，
调用 Web Unlocker（POST /request），把原始 HTML 存到 docs/data-imports/brightdata/。

用法：
    .venv/bin/python scripts/brightdata_fetch.py --url <商品链接> --country sg
    .venv/bin/python scripts/brightdata_fetch.py --urls-file urls.txt --country sg

密钥只从文件读取，不打印、不写入输出。
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

DEFAULT_ENV = Path.home() / "Documents" / "ChatGPT" / "picolah" / ".env"
ENDPOINT = "https://api.brightdata.com/request"
OUTPUT_DIR = Path("docs/data-imports/brightdata")


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        sys.exit(f"找不到凭据文件：{path}，用 --env-file 指定")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def credentials(env: dict[str, str]) -> tuple[str, str]:
    token = env.get("BRIGHTDATA_API_TOKEN", "").strip()
    zone = env.get("BRIGHTDATA_ZONE", "").strip()
    if not token or not zone:
        sys.exit("凭据文件里缺少 BRIGHTDATA_API_TOKEN 或 BRIGHTDATA_ZONE")
    return token, zone


def fetch(
    client: httpx.Client,
    token: str,
    zone: str,
    url: str,
    *,
    country: str | None,
    render: bool,
    timeout: float,
) -> tuple[str, int]:
    payload: dict[str, object] = {"zone": zone, "url": url, "format": "raw"}
    if country:
        payload["country"] = country.lower()
    if render:
        payload["render"] = True

    response = client.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )

    error = response.headers.get("x-brd-error")
    message = response.headers.get("x-brd-err-msg")
    if error:
        hint = f"（{message}）" if message else ""
        raise RuntimeError(f"Bright Data 拒绝：{error}{hint}")

    body = response.text
    if response.status_code != 200:
        raise RuntimeError(f"Bright Data HTTP {response.status_code}")
    if not body.strip():
        raise RuntimeError("Bright Data 返回空响应")
    return body, len(body)


def slug(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.path.rsplit("/", 1)[-1] or "page").removesuffix(".html")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bright Data Web Unlocker 抓取")
    parser.add_argument("--url", action="append", default=[], help="可重复")
    parser.add_argument("--urls-file", type=Path, default=None)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--country", default="sg")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--render", action="store_true", help="让 Bright Data 执行页面 JS")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    urls = list(args.url)
    if args.urls_file:
        urls.extend(
            line.strip()
            for line in args.urls_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    if not urls:
        sys.exit("请用 --url 或 --urls-file 指定目标页面")
    urls = urls[: args.limit]

    env = read_env(args.env_file)
    token, zone = credentials(env)
    print(f"凭据：zone={zone} token=***{token[-4:]}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []

    with httpx.Client(follow_redirects=False) as client:
        for index, url in enumerate(urls, start=1):
            try:
                body, size = fetch(
                    client,
                    token,
                    zone,
                    url,
                    country=args.country,
                    render=args.render,
                    timeout=args.timeout,
                )
            except (httpx.HTTPError, RuntimeError) as error:
                print(f"[{index}/{len(urls)}] 失败 {url}\n    {error}")
                manifest.append({"url": url, "ok": False, "error": str(error)})
                continue

            name = f"{slug(url)}-{datetime.now(UTC).strftime('%H%M%S')}.html"
            path = OUTPUT_DIR / name
            path.write_text(body, encoding="utf-8")
            ok = "<html" in body[:2000].lower()
            print(f"[{index}/{len(urls)}] {size / 1024:.0f} KB  {name}  html={ok}")
            manifest.append({"url": url, "ok": True, "file": name, "bytes": size})
            time.sleep(args.interval)

    manifest_path = OUTPUT_DIR / "manifest.json"
    existing: list[object] = []
    if manifest_path.exists():
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            existing = loaded
    manifest_path.write_text(
        json.dumps(existing + manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok_count = sum(1 for item in manifest if item["ok"])
    print(f"\n成功 {ok_count}/{len(manifest)}，目录：{OUTPUT_DIR}")
    return 0 if ok_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
