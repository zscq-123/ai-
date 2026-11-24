#!/usr/bin/env python3
"""Safely extract external dataset delivery ZIP files for offline auditing."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath

MAX_ENTRY_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_member_name(info: zipfile.ZipInfo) -> str:
    """Recover common CP936/GBK ZIP names while preserving valid UTF-8 names."""

    name = info.filename
    if info.flag_bits & 0x800:
        return unicodedata.normalize("NFC", name)
    try:
        raw_name = name.encode("cp437")
    except UnicodeEncodeError:
        return unicodedata.normalize("NFC", name)
    for encoding in ("utf-8", "gb18030"):
        try:
            return unicodedata.normalize("NFC", raw_name.decode(encoding))
        except UnicodeDecodeError:
            continue
    return unicodedata.normalize("NFC", name)


def safe_relative_path(name: str) -> Path:
    normalized = name.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or not pure.parts:
        raise ValueError(f"unsafe absolute or empty archive path: {name!r}")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe archive path component: {name!r}")
    if pure.parts[0].endswith(":"):
        raise ValueError(f"unsafe drive-qualified archive path: {name!r}")
    if any("\x00" in part for part in pure.parts):
        raise ValueError(f"NUL in archive path: {name!r}")
    return Path(*pure.parts)


def extract_archive(archive: Path, destination: Path) -> dict[str, object]:
    archive_target = destination / archive.stem
    archive_target.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, object]] = []
    total_uncompressed = 0
    seen_paths: set[str] = set()

    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            decoded_name = decode_member_name(info)
            relative_path = safe_relative_path(decoded_name)
            relative_key = relative_path.as_posix()
            if relative_key in seen_paths:
                raise ValueError(f"duplicate decoded path in {archive.name}: {relative_key}")
            seen_paths.add(relative_key)

            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"symbolic link is not allowed: {relative_key}")
            if info.flag_bits & 0x1:
                raise ValueError(f"encrypted entry is not allowed: {relative_key}")
            if info.file_size > MAX_ENTRY_BYTES:
                raise ValueError(f"entry exceeds size limit: {relative_key}")
            total_uncompressed += info.file_size
            if total_uncompressed > MAX_ARCHIVE_BYTES:
                raise ValueError(f"archive exceeds total size limit: {archive.name}")

            target = archive_target / relative_path
            target_resolved = target.resolve()
            if archive_target.resolve() not in target_resolved.parents and target_resolved != archive_target.resolve():
                raise ValueError(f"path escapes destination: {relative_key}")

            is_directory = info.is_dir() or decoded_name.endswith(("/", "\\"))
            if is_directory:
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(info) as input_handle, target.open("wb") as output_handle:
                    shutil.copyfileobj(input_handle, output_handle)

            ratio = None
            if info.compress_size:
                ratio = round(info.file_size / info.compress_size, 2)
            rows.append(
                {
                    "path": relative_key,
                    "is_directory": is_directory,
                    "compressed_bytes": info.compress_size,
                    "uncompressed_bytes": info.file_size,
                    "compression_ratio": ratio,
                }
            )

    return {
        "archive": archive.name,
        "archive_sha256": sha256_file(archive),
        "entry_count": len(rows),
        "total_uncompressed_bytes": total_uncompressed,
        "max_compression_ratio": max(
            (row["compression_ratio"] or 0 for row in rows), default=0
        ),
        "entries": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    archives = [path.resolve() for path in args.input]
    for archive in archives:
        if not archive.is_file():
            raise FileNotFoundError(archive)

    results = [extract_archive(archive, args.output) for archive in archives]
    manifest = args.output / "extraction_manifest.json"
    manifest.write_text(
        json.dumps({"archives": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
