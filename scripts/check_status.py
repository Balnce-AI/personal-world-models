#!/usr/bin/env python3
import json
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).parents[1]
ALLOWED = {
    "truth_plane": {
        "CANONICAL",
        "OPERATIONALIZING",
        "IMPLEMENTED",
        "RESEARCH_HYPOTHESIS",
    },
    "evidence_status": {"REAL", "EXPERIMENTAL_REAL", "SIMULATED", "SPECIFIED", "RESEARCH"},
    "publication_class": {"PUBLIC_FULL", "PUBLIC_INTERFACE_ONLY", "INTERNAL"},
    "assurance_level": {
        "NOT_ASSESSED",
        "BASELINE_CAPTURED",
        "UNIT_PASS",
        "CONFORMANCE_PASS",
        "REPRODUCED",
    },
    "release_disposition": {
        "RELEASABLE",
        "HOLD_IP",
        "HOLD_SECURITY",
        "HOLD_LEGAL",
        "INTERNAL_ONLY",
    },
}
REQUIRED = {
    "id",
    "path",
    *ALLOWED,
    "included_in_release",
    "last_verified",
    "source_refs",
    "limitations",
}


def validate(path: Path) -> list[str]:
    try:
        registry = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        return [f"registry: {error}"]

    errors: list[str] = []
    components = registry.get("components")
    if registry.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if not isinstance(components, list) or not components:
        return errors + ["components: expected a non-empty array"]

    seen: set[str] = set()
    for index, component in enumerate(components):
        label = f"components[{index}]"
        if not isinstance(component, dict):
            errors.append(f"{label}: expected object")
            continue
        missing = sorted(REQUIRED - component.keys())
        if missing:
            errors.append(f"{label}: missing {', '.join(missing)}")
            continue
        component_id = component["id"]
        if not isinstance(component_id, str) or not component_id:
            errors.append(f"{label}.id: expected non-empty string")
        elif component_id in seen:
            errors.append(f"{label}.id: duplicate {component_id}")
        else:
            seen.add(component_id)
        component_path = ROOT / component["path"]
        if not component_path.exists():
            errors.append(f"{label}.path: does not exist: {component['path']}")
        for field, values in ALLOWED.items():
            if component[field] not in values:
                errors.append(f"{label}.{field}: unknown value {component[field]!r}")
        if not isinstance(component["included_in_release"], bool):
            errors.append(f"{label}.included_in_release: expected boolean")
        if component["release_disposition"].startswith("HOLD_") and component["included_in_release"]:
            errors.append(f"{label}.included_in_release: held component cannot enter a release")
        try:
            date.fromisoformat(component["last_verified"])
        except (TypeError, ValueError):
            errors.append(f"{label}.last_verified: expected ISO date")
        for field in ("source_refs", "limitations"):
            value = component[field]
            if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
                errors.append(f"{label}.{field}: expected non-empty string array")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_status.py REGISTRY.json", file=sys.stderr)
        return 2
    errors = validate(Path(sys.argv[1]))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("status metadata valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
