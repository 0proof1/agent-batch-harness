#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def component(name: str, version: str, kind: str = "library") -> dict[str, str]:
    return {"type": kind, "name": name, "version": version}


def main(argv: list[str]) -> int:
    output = Path(argv[0]) if argv else ROOT / "dist" / "sbom.cdx.json"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependencies = [value.split(";", 1)[0].strip() for value in project.get("dependencies", [])]
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": component(project["name"], project["version"], "application")},
        "components": [component(value, "declared") for value in dependencies],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
