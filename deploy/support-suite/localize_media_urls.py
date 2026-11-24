#!/usr/bin/env python3
"""Replace disabled CHUNG YIP OSS media URLs with verified same-origin assets."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
from urllib.parse import urlsplit


OSS_ORIGIN = "https://medical-sg.oss-ap-southeast-1.aliyuncs.com"
URL_PATTERN = re.compile(re.escape(OSS_ORIGIN) + r"[^\"'\s)\\]+")
TEXT_SUFFIXES = {".json", ".js", ".ts", ".tsx"}

# These legacy CMS references do not have matching files in the release.
# Keep them useful by pointing to the closest verified local artwork.
FALLBACKS = {
    "/images/categories/a5923401932fa98598790a00e0591dbd.png": "/images/cms/buzud-home-4.png",
    "/images/categories/1637f5d71bf7a54747ee4ddf987c75a3.png": "/images/products/buzud-8885020710304-1.png",
    "/images/categories/9cae1772a85f0343d510fcddcfdb30e7.png": "/images/products/buzud-8885020710014-1.png",
    "/images/cms/buzud-support-banner-v3.png": "/images/cms/buzud-support-banner.png",
    "/images/customer-service/health-experience-imdec-2026-04.jpg": "/images/customer-service/health-experience-imdec-2026-01.jpg",
    "/images/customer-service/health-experience-imdec-2026-05.jpg": "/images/customer-service/health-experience-imdec-2026-02.jpg",
    "/images/customer-service/health-experience-imdec-2026-06.jpg": "/images/customer-service/health-experience-imdec-2026-03.jpg",
}


def local_url(url: str, public_root: Path) -> str:
    parsed = urlsplit(url)
    path = FALLBACKS.get(parsed.path, parsed.path)
    if path.endswith("/..."):
        return path
    target = public_root / path.lstrip("/")
    if not target.is_file():
        raise FileNotFoundError(f"missing local media for {url}: {target}")
    query = f"?{parsed.query}" if parsed.query and path == parsed.path else ""
    return f"{path}{query}"


def atomic_write(path: Path, text: str) -> None:
    stat = path.stat()
    temporary = path.with_name(f".{path.name}.media-localize.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, stat.st_mode)
    os.chown(temporary, stat.st_uid, stat.st_gid)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cms_root", type=Path)
    parser.add_argument("public_root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    changed: list[tuple[Path, str]] = []
    rewrites = 0
    for path in sorted(args.cms_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        original = path.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            nonlocal rewrites
            rewrites += 1
            return local_url(match.group(0), args.public_root)

        updated = URL_PATTERN.sub(replace, original)
        if updated != original:
            changed.append((path, updated))

    if args.apply:
        for path, updated in changed:
            atomic_write(path, updated)

    mode = "updated" if args.apply else "verified"
    print(f"{mode} {rewrites} media URLs across {len(changed)} files")


if __name__ == "__main__":
    main()
