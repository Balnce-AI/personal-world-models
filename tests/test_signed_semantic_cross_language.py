import hashlib
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).parents[1]
SUITE = ROOT / "conformance/vectors/signed-semantic-suite.json"
SOURCES = ROOT / "conformance/sources"


def run(command):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def neutral_output(completed):
    assert completed.stdout, completed.stderr
    output = json.loads(completed.stdout)
    output.pop("implementation", None)
    return output


def validators():
    paths = list((ROOT / "conformance/schemas").glob("*.json")) + list((ROOT / "schemas/json-schema").glob("*.json"))
    schemas = [json.loads(path.read_text()) for path in paths]
    registry = Registry().with_resources((schema["$id"], Resource.from_contents(schema)) for schema in schemas)
    return {
        schema["$id"]: Draft202012Validator(schema, registry=registry)
        for schema in schemas
    }


def test_signed_suite_and_every_source_validate_against_public_schemas():
    suite = json.loads(SUITE.read_text())
    checks = validators()
    checks["https://personal-world-models.org/schema/signed-semantic-suite/1-0-0"].validate(suite)
    source_validator = checks["https://personal-world-models.org/schema/signed-semantic-source/1-0-0"]
    assert len(suite["cases"]) >= 16
    for case in suite["cases"]:
        source_validator.validate(case["source"])
        assert (SOURCES / f"signed-semantic-{case['case_id']}.json").is_file()


def test_rust_generation_is_byte_reproducible(tmp_path):
    completed = run(["cargo", "run", "-q", "-p", "pwm-semantic", "--example", "generate_signed_suite", "--", str(tmp_path)])
    assert completed.returncode == 0, completed.stderr
    for checked in sorted(SOURCES.glob("signed-semantic-*.json")):
        generated = tmp_path / "sources" / checked.name
        assert generated.read_bytes() == checked.read_bytes(), checked.name
    assert (tmp_path / "vectors/signed-semantic-suite.json").read_bytes() == SUITE.read_bytes()


def test_rust_and_independent_python_agree_on_every_signed_case():
    suite = json.loads(SUITE.read_text())
    for case in suite["cases"]:
        path = SOURCES / f"signed-semantic-{case['case_id']}.json"
        rust = neutral_output(run(["cargo", "run", "-q", "-p", "pwm-semantic", "--", "evaluate", "--bundle", str(path)]))
        python = neutral_output(run([sys.executable, "conformance/python/pwm_semantic_oracle.py", "evaluate", "--bundle", str(path)]))
        assert rust == python, case["case_id"]
        if case["polarity"] == "valid":
            assert {"decision": "ACCEPT", "output": rust} == case["expected"]
        else:
            assert rust["decision"] == "REJECT"
            assert rust["error"]["code"] == case["expected"]["error_code"]
            assert rust["state_sha256"] == case["expected"]["accepted_prefix_state_sha256"]


def test_negative_suite_covers_transport_authority_and_semantics():
    suite = json.loads(SUITE.read_text())
    identifiers = {case["case_id"] for case in suite["cases"] if case["polarity"] == "invalid"}
    assert {
        "signature-mutation", "payload-mutation", "body-cid-mismatch", "unknown-parent",
        "invalid-author-sequence", "invalid-principal-scope", "unauthorized-operation", "invalid-principal-grant",
        "family-kind", "subject-perspective", "false-effective-privacy",
        "unauthorized-declassification", "contradiction-transition", "hpl-binding",
        "hpl-authorization-expired", "hpl-projection-replay", "signature-and-semantic-invalid",
    } <= identifiers


def test_comprehensive_case_covers_required_semantic_surfaces():
    suite = json.loads(SUITE.read_text())
    cases = {case["case_id"]: case for case in suite["cases"]}
    state = cases["comprehensive"]["expected"]["output"]["result"]["value"]
    assert state["models"]["model:self:v2"]["lifecycleStatus"] == "ACCEPTED"
    assert state["models"]["model:self"]["lifecycleStatus"] == "SUPERSEDED"
    assert state["models"]["model:relationship"]["lifecycleStatus"] == "REVOKED"
    assert state["models"]["model:meta"]["kind"] == "META"
    assert state["models"]["model:world"]["kind"] == "WORLD"
    assert state["models"]["model:possible"]["kind"] == "POSSIBLE_WORLD"
    assert state["contradictions"]["contradiction:one"]["status"] == "EXPLAINED"
    assert state["privacyBoundaries"]["boundary:one"]["boundary_kind"] == "REDACTION"
    assert state["privacyBoundaries"]["boundary:proof"]["boundary_kind"] == "PROOF"
    assert state["privacyBoundaries"]["boundary:proof"]["status"] == "REVOKED"
    assert state["projections"]["projection:one"]["status"] == "REVOKED"
    query = cases["comprehensive-query"]["expected"]["output"]["result"]["value"]
    assert query["model_ids"] == ["model:meta", "model:self:v2", "model:world"]
    projection = cases["comprehensive-hpl"]["expected"]["output"]["result"]["value"]
    assert projection["projection_id"] == "projection:one"
    assert projection["effective_privacy_class"] == "PERSONAL"


def test_runner_compares_rust_and_python_signed_semantics():
    completed = run([
        sys.executable, "scripts/pwm_conformance.py", "compare", "--implementations",
        "rust-signed-semantic", "python-signed-semantic", "--suite", "PWM-SIGNED-SEMANTICS-V1",
    ])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "agree" in completed.stdout
    for implementation in ("rust-signed-semantic", "python-signed-semantic"):
        verified = run([
            sys.executable, "scripts/pwm_conformance.py", "verify", "--implementation",
            implementation, "--profile", "PWM-MODEL-ECOLOGY-1",
        ])
        assert verified.returncode == 0, verified.stdout + verified.stderr
        assert "21 cases" in verified.stdout


def test_suite_digest_is_stable_hex():
    digest = hashlib.sha256(SUITE.read_bytes()).hexdigest()
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)
