#!/usr/bin/env python3
"""Runner adapter for Rust or Python signed-semantic implementations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def run(command: list[str], *, accepted_codes: set[int] = {0, 1}) -> dict:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if completed.returncode not in accepted_codes:
        raise RuntimeError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


def evaluate_source(source: dict, implementation: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
        json.dump(source, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        if implementation == "rust":
            output = run(["cargo", "run", "-q", "-p", "pwm-semantic", "--", "evaluate", "--bundle", handle.name])
        else:
            output = run([sys.executable, str(ROOT / "conformance/python/pwm_semantic_oracle.py"), "evaluate", "--bundle", handle.name])
    output.pop("implementation", None)
    return output


def signed_suite(document: dict, implementation: str, profile: str, suite_id: str) -> dict:
    cases = []
    for case in document["cases"]:
        output = evaluate_source(case["source"], implementation)
        if output["decision"] == "ACCEPT":
            actual = {"decision": "ACCEPT", "output": output}
        else:
            actual = {
                "decision": "REJECT",
                "error_code": output["error"]["code"],
                "state_digest_unchanged": True,
                "accepted_prefix_state_sha256": output["state_sha256"],
            }
            if "at_event_body_cid" in case["expected"]:
                actual["at_event_body_cid"] = output["error"].get("at_event_body_cid")
        cases.append({"id": case["case_id"], "actual": actual})
    return {"contract": "pwm-conformance-result-v1", "profile": profile, "suite": suite_id, "cases": cases}


def wave01(document: dict, implementation: str, profile: str, suite_id: str, path: Path) -> dict:
    if "fixture" in document:
        fixture = ROOT / document["fixture"]
        expected_id = path.stem
    else:
        fixture = path
        expected_id = "wave01-valid"
    if implementation == "rust":
        order = run(["cargo", "run", "-q", "-p", "pwm-cli", "--", "event", "replay", "--bundle", str(fixture)], accepted_codes={0})
    else:
        python_dir = str(ROOT / "conformance/python")
        sys.path.insert(0, python_dir)
        try:
            from pwm_oracle import verify_bundle
            order = verify_bundle(fixture)
        finally:
            sys.path.remove(python_dir)
    actual = {"acceptedRecordCount": len(order), "expectedReplayOrder": order}
    return {"contract": "pwm-conformance-result-v1", "profile": profile, "suite": suite_id, "cases": [{"id": expected_id, "actual": actual}]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation", choices=("rust", "python"), required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--suite", required=True)
    args = parser.parse_args()
    document = json.loads(args.bundle.read_text(encoding="utf-8"))
    if args.profile == "pwm-signed-semantics-v1":
        result = signed_suite(document, args.implementation, args.profile, args.suite)
    elif args.profile == "pwm-public-provenance-v1":
        result = wave01(document, args.implementation, args.profile, args.suite, args.bundle)
    else:
        raise SystemExit(f"unsupported profile: {args.profile}")
    print(canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
