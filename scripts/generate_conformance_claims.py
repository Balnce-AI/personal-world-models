#!/usr/bin/env python3
"""Generate commit-bound signed semantic conformance evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "conformance/vectors/signed-semantic-suite.json"
SUITE_ID = "PWM-SIGNED-SEMANTICS-V1"
PROFILE = "pwm-signed-semantics-v1"
REPOSITORY = "https://github.com/Balnce-AI/personal-world-models"
EXCLUSIONS = [
    "Interoperability beyond the exact profile, suite version, and suite digest in this claim.",
    "Production identity, key custody, delegation, recovery, distributed synchronization, and storage durability.",
    "Private Balnce internals, private PLOG semantics, physical actuation, and safety certification.",
]
IMPLEMENTATIONS = {
    "rust-signed-semantic": ("rust", "0.2.0-alpha.1"),
    "python-signed-semantic": ("python", "1.0.0"),
}


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--evidence-commit", required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--completed-at", required=True)
    parser.add_argument("--environment", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit) or not re.fullmatch(r"[0-9a-f]{40}", args.evidence_commit):
        raise SystemExit("commit arguments must be full lowercase Git commits")

    suite_document = json.loads(SUITE.read_text(encoding="utf-8"))
    expected = {case["case_id"]: case["expected"] for case in suite_document["cases"]}
    suite_digest = hashlib.sha256(SUITE.read_bytes()).hexdigest()
    outputs: dict[str, dict] = {}
    for implementation_id, (adapter, version) in IMPLEMENTATIONS.items():
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "conformance/python/signed_semantic_adapter.py"),
                "--implementation", adapter,
                "--bundle", str(SUITE),
                "--profile", PROFILE,
                "--suite", SUITE_ID,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(completed.stdout)
        actual = {case["id"]: case["actual"] for case in result["cases"]}
        if actual != expected:
            raise SystemExit(f"{implementation_id} does not match the signed suite expectations")
        outputs[implementation_id] = result

    encoded_outputs = {canonical(result) for result in outputs.values()}
    if len(encoded_outputs) != 1:
        raise SystemExit("signed semantic implementations do not agree")

    for implementation_id, (_, version) in IMPLEMENTATIONS.items():
        result = outputs[implementation_id]
        result_path = ROOT / f"conformance/results/{implementation_id}-v1.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_bytes(canonical(result))
        result_uri = f"{REPOSITORY}/blob/{args.evidence_commit}/{result_path.relative_to(ROOT)}"
        claim = {
            "claim_version": "1.0.0",
            "profile": PROFILE,
            "profile_status": "PROVISIONAL",
            "implementation": {
                "id": implementation_id,
                "version": version,
                "adapter_version": "1.0.0",
                "source_commit": args.source_commit,
                "source_uri": f"{REPOSITORY}/tree/{args.source_commit}",
            },
            "suite": {"id": SUITE_ID, "version": "1.0.0", "sha256": suite_digest},
            "execution": {
                "started_at": args.started_at,
                "completed_at": args.completed_at,
                "environment": args.environment,
                "runner_uri": f"{REPOSITORY}/blob/{args.source_commit}/scripts/pwm_conformance.py",
                "result_uri": result_uri,
            },
            "case_results": [
                {
                    "case_id": case["id"],
                    "status": "PASS",
                    "output_sha256": hashlib.sha256(canonical(case["actual"])).hexdigest(),
                    "semantic_diff_count": 0,
                }
                for case in result["cases"]
            ],
            "exclusions": EXCLUSIONS,
        }
        write_json(ROOT / f"conformance/claims/{implementation_id}-v1.json", claim)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
