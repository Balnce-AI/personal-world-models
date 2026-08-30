import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_wave01_claim_evidence_paths_exist():
    ledger = json.loads((ROOT / "governance/PUBLIC_CLAIM_LEDGER.json").read_text())
    assert ledger["schema_version"] == "1.0.0"
    identifiers = [claim["claim_id"] for claim in ledger["claims"]]
    assert len(identifiers) == len(set(identifiers))
    for claim in ledger["claims"]:
        assert claim["status"] in {"SUPPORTED", "PARTIAL", "FALSIFIED"}
        assert claim["falsifier"]
        assert claim["limitations"]
        assert claim["evidence"]
        for evidence in claim["evidence"]:
            assert (ROOT / evidence).exists(), evidence


def test_wave01_benchmark_covers_required_scales_with_bounded_claims():
    report = json.loads((ROOT / "benchmarks/results/wave01-dag.json").read_text())
    assert [case["events"] for case in report["cases"]] == [1_000, 10_000, 100_000]
    assert all(case["replayed_events"] == case["events"] for case in report["cases"])
    assert report["environment"]["build_profile"] == "release"
    assert len(report["limitations"]) >= 3
