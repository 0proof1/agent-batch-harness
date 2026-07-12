#!/usr/bin/env python3
from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path


DENIED_SUFFIXES = {".log", ".lock", ".pem", ".key", ".sqlite", ".db"}
DENIED_PARTS = {"__pycache__", ".git", ".venv"}


def archive_names(path: Path) -> list[str]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            return archive.getnames()
    raise ValueError(f"unsupported artifact: {path}")


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_artifact.py ARTIFACT...", file=sys.stderr)
        return 2
    errors: list[str] = []
    for value in argv:
        path = Path(value)
        for name in archive_names(path):
            normalized = name.replace("\\", "/").lower()
            if any(part in normalized.split("/") for part in DENIED_PARTS):
                errors.append(f"excluded directory in {path.name}: {name}")
            if Path(normalized).suffix in DENIED_SUFFIXES:
                errors.append(f"excluded file type in {path.name}: {name}")
    if errors:
        print("artifact check failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"artifact check passed: {len(argv)} archive(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
