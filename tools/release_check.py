#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "README.md",
    "README.ko.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "GOVERNANCE.md",
    "PUBLICATION_POLICY.md",
    ".github/ISSUE_TEMPLATE/bug.yml",
    ".github/ISSUE_TEMPLATE/feature.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml",
}
IGNORED_PARTS = {".git", ".venv", "__pycache__", "build", "dist", ".pytest_cache"}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".tsv", ".json", ".yml", ".yaml", ".txt"}
FORBIDDEN = {
    "private key": re.compile(r"BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY"),
    "GitHub token": re.compile(r"(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Unix home path": re.compile(r"/home/[A-Za-z0-9._-]+/"),
    "Windows home path": re.compile(r"[A-Za-z]:\\Users\\[^\\]+\\"),
}


def public_text_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in TEXT_SUFFIXES
        and not IGNORED_PARTS.intersection(path.relative_to(ROOT).parts)
    ]


def main() -> int:
    errors: list[str] = []
    missing = sorted(name for name in REQUIRED if not (ROOT / name).is_file())
    errors.extend(f"missing required file: {name}" for name in missing)

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = metadata.get("project", {})
    if project.get("license") != "MIT":
        errors.append("pyproject.toml must declare the MIT license")
    if project.get("dependencies"):
        errors.append("runtime dependencies require explicit publication review")
    package_source = (ROOT / "src" / "agent_batch_harness" / "__init__.py").read_text(encoding="utf-8")
    package_version = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']$', package_source, re.MULTILINE)
    if package_version is None:
        errors.append("src/agent_batch_harness/__init__.py must declare __version__")
    elif package_version.group(1) != project.get("version"):
        errors.append("package __version__ must match pyproject.toml")

    for path in public_text_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in FORBIDDEN.items():
            if pattern.search(text):
                errors.append(f"{label} candidate: {path.relative_to(ROOT)}")

    if errors:
        print("release check failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"release check passed: {len(REQUIRED)} required files, {len(public_text_files())} text files scanned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
