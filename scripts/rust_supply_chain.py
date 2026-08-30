#!/usr/bin/env python3
"""Emit the declared license inventory for the locked Rust dependency graph."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    result = subprocess.run(
        ["cargo", "metadata", "--format-version=1", "--locked"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        return result.returncode

    metadata = json.loads(result.stdout)
    dependencies = []
    missing = []
    for package in metadata["packages"]:
        if package["source"] is None:
            continue
        license_expression = package.get("license")
        if not license_expression:
            missing.append(f"{package['name']} {package['version']}")
            continue
        dependencies.append(
            {
                "name": package["name"],
                "version": package["version"],
                "source": package["source"],
                "license": license_expression,
            }
        )
    dependencies.sort(key=lambda item: (item["name"], item["version"], item["source"]))
    if missing:
        print("dependencies without declared licenses: " + ", ".join(sorted(missing)), file=sys.stderr)
        return 1

    report = {
        "schema_version": "1.0.0",
        "source": "cargo metadata --format-version=1 --locked",
        "dependencies": dependencies,
        "limitations": [
            "This inventory reports package-declared SPDX expressions; it is not legal advice.",
            "File-level notices and non-code assets require separate review.",
        ],
    }
    arguments.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"recorded {len(dependencies)} Rust dependency licenses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
