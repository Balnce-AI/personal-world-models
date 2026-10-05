import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "conformance/python/pwm_semantic_oracle.py"
BYTE_ORACLE_PATH = ROOT / "conformance/python/pwm_oracle.py"


def _load_oracle():
    python_dir = str(ORACLE_PATH.parent)
    sys.path.insert(0, python_dir)
    try:
        specification = importlib.util.spec_from_file_location("pwm_semantic_oracle_test", ORACLE_PATH)
        module = importlib.util.module_from_spec(specification)
        sys.modules[specification.name] = module
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(python_dir)


oracle = _load_oracle()


def event(identifier, kind, data, *, parents=(), valid_from=None, valid_to=None):
    value = {
        "eventId": identifier,
        "eventType": kind,
        "recordedAt": "2026-10-01T00:00:00Z",
        "parents": list(parents),
        "payload": data,
    }
    if valid_from is not None:
        value["validFrom"] = valid_from
    if valid_to is not None:
        value["validTo"] = valid_to
    return value


def evaluate(*events):
    return oracle.evaluate_source(oracle.FixtureSource(tuple(events)))


def model(identifier, evidence_id, **changes):
    value = {
        "modelId": identifier,
        "familyId": "pwm.preference",
        "kind": "SELF",
        "subjectIds": ["person:alice"],
        "perspective": "person:alice",
        "evidenceRefs": [evidence_id],
        "privacyClass": "PERSONAL",
        "field": "delivery.preferredSurface",
        "value": "entry-table",
    }
    value.update(changes)
    return value


def lifecycle(identifier, evidence_id, *, prefix="", **changes):
    proposal = f"{prefix}proposal"
    review = f"{prefix}review"
    return (
        event(proposal, "pwm.model.proposed", model(identifier, evidence_id, **changes)),
        event(
            review,
            "pwm.model.reviewed",
            {"modelId": identifier, "proposalEventId": proposal, "decision": "ACCEPT", "reviewer": "person:alice"},
            parents=(proposal,),
        ),
        event(
            f"{prefix}accept",
            "pwm.model.accepted",
            {"modelId": identifier, "proposalEventId": proposal, "reviewEventId": review},
            parents=(review,),
        ),
    )


def test_module_imports_only_stdlib_and_sibling_byte_oracle():
    tree = ast.parse(ORACLE_PATH.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports <= {
        "__future__", "argparse", "copy", "dataclasses", "datetime", "hashlib", "json", "pathlib", "sys", "typing", "pwm_oracle"
    }
    assert "pwm_hpl_ref" not in ORACLE_PATH.read_text(encoding="utf-8")


def test_lifecycle_privacy_query_and_projection_are_reduced_independently():
    records = [
        event("genesis", "pwm.genesis", {}),
        event("evidence", "pwm.evidence.recorded", {"evidenceId": "ev:1", "privacyClass": "PERSONAL"}, parents=("genesis",)),
        *lifecycle("model:1", "ev:1", prefix="one-"),
        event(
            "authority",
            "pwm.query.authority-granted",
            {
                "authorityId": "auth:1",
                "principalId": "person:alice",
                "recipientId": "robot:7",
                "purpose": "delivery",
                "subjectIds": ["person:alice"],
                "familyIds": ["pwm.preference"],
                "allowedFields": ["delivery.preferredSurface"],
                "maximumPrivacyClass": "PERSONAL",
                "issuedAt": "2026-01-01T00:00:00Z",
                "expiresAt": "2027-01-01T00:00:00Z",
            },
        ),
        event(
            "query",
            "pwm.query.executed",
            {
                "authorityId": "auth:1",
                "query": {
                    "principalId": "person:alice",
                    "recipientId": "robot:7",
                    "purpose": "delivery",
                    "at": "2026-10-01T00:00:00Z",
                    "subjectIds": ["person:alice"],
                    "familyIds": ["pwm.preference"],
                    "maximumPrivacyClass": "PERSONAL",
                },
            },
        ),
        event(
            "projection",
            "hpl.projection.issued",
            {
                "projectionId": "projection:1",
                "authorityId": "auth:1",
                "principalId": "person:alice",
                "recipientId": "robot:7",
                "purpose": "delivery",
                "requestedFields": ["delivery.preferredSurface", "health.medication"],
                "at": "2026-10-01T00:00:00Z",
            },
        ),
    ]
    result = evaluate(*records)
    assert result["decision"] == "ACCEPT"
    assert result["state"]["query"] == {"modelIds": ["model:1"], "worldId": "world:actual"}
    assert result["state"]["projections"]["projection:1"]["fields"] == {
        "delivery.preferredSurface": "entry-table"
    }


def test_rejection_returns_stable_error_and_unmodified_accepted_prefix():
    result = evaluate(
        event("genesis", "pwm.genesis", {}),
        event("bad", "pwm.model.accepted", {"modelId": "missing", "proposalEventId": "p", "reviewEventId": "r"}),
        event("never", "pwm.evidence.recorded", {"evidenceId": "ev:never", "privacyClass": "LOW"}),
    )
    assert result["decision"] == "REJECT"
    assert result["error"] == {
        "code": "LIFECYCLE_PRECONDITION_MISSING",
        "eventId": "bad",
        "eventIndex": 1,
    }
    assert result["state"]["acceptedEventIds"] == ["genesis"]
    assert result["state"]["evidence"] == {}


def test_declassification_requires_policy_and_complete_source_coverage():
    boundary = {
        "boundaryKind": "PROOF",
        "inputPrivacyClass": "SENSITIVE",
        "outputPrivacyClass": "PERSONAL",
        "sourceRefs": [],
        "policyRef": "policy:proof",
        "approved": True,
        "releasedFields": ["aggregate"],
    }
    result = evaluate(
        event("genesis", "pwm.genesis", {}),
        event("evidence", "pwm.evidence.recorded", {"evidenceId": "ev:s", "privacyClass": "SENSITIVE"}),
        event("policy", "pwm.policy.registered", {"policyId": "policy:proof", "privacyFloor": "PUBLIC"}),
        event("proposal", "pwm.model.proposed", model("model:s", "ev:s", privacyBoundaries=[boundary])),
    )
    assert result["error"]["code"] == "DECLASSIFICATION_NOT_AUTHORIZED"
    assert result["state"]["acceptedEventIds"] == ["genesis", "evidence", "policy"]


def test_dependency_cycle_rejects_only_cycle_forming_edge():
    records = [
        event("genesis", "pwm.genesis", {}),
        event("evidence", "pwm.evidence.recorded", {"evidenceId": "ev:1", "privacyClass": "LOW"}),
        *lifecycle("model:a", "ev:1", prefix="a-"),
        *lifecycle("model:b", "ev:1", prefix="b-"),
        event("edge:a-b", "pwm.topology.edge-added", {"edgeId": "a-b", "sourceModelId": "model:a", "edgeType": "DEPENDS_ON", "targetModelId": "model:b", "privacyClass": "LOW"}),
        event("edge:b-a", "pwm.topology.edge-added", {"edgeId": "b-a", "sourceModelId": "model:b", "edgeType": "DEPENDS_ON", "targetModelId": "model:a", "privacyClass": "LOW"}),
    ]
    result = evaluate(*records)
    assert result["error"]["code"] == "DEPENDENCY_CYCLE"
    assert list(result["state"]["edges"]) == ["a-b"]


def test_signed_adapter_verifies_whole_bundle_before_semantic_reduction(monkeypatch, tmp_path):
    called = []

    def reject(_path):
        called.append(True)
        raise oracle.pwm_oracle.ProfileError("bad signature")

    monkeypatch.setattr(oracle.pwm_oracle, "verify_bundle_object", reject)
    source = tmp_path / "source.json"
    source.write_text(json.dumps({
        "source_version": "1.0.0",
        "source_id": "source:test",
        "profile": oracle.PROFILE,
        "trust_anchor": {"key_id": "key:root", "public_key_hex": "00" * 32},
        "bundle": {
            "profile": "pwm-public-provenance-v1",
            "appender_key_id": "key:appender",
            "appender_public_key_hex": "11" * 32,
            "author_keys": [{"key_id": "key:root", "public_key_hex": "00" * 32, "active_from_log_sequence": 0, "revoked_at_log_sequence": None}],
            "schemas": [{"event_kind": "pwm.genesis", "schema_version": "1.0.0"}],
            "records": [{"body_cbor_hex": "00", "body_cid": "ba", "event_signature_hex": "00", "payload_cbor_hex": "00", "receipt_body_cbor_hex": "00", "receipt_cid": "ba", "receipt_signature_hex": "00"}],
        },
        "command": {"operation": "REDUCE", "evaluation_log_sequence": 0},
    }))
    result = oracle.evaluate_bundle(source)
    assert called == [True]
    assert result["error"]["code"] == "SIGNATURE_INVALID"
    assert result["processed_records"] == 0


def test_verified_record_adapter_requires_canonical_semantic_envelope():
    body = {
        "event_kind": "pwm.genesis",
        "event_time": 0,
        "parent_event_cids": [],
        "principal_scope": "person:alice",
        "author_key_id": "key:root",
        "schema_version": "1.0.0",
    }
    genesis = {
        "scope_id": "person:alice",
        "root_principal_id": "person:alice",
        "root_key_id": "key:root",
        "principals": [{"principal_class": "PERSON", "principal_id": "person:alice"}],
        "grants": [{
            "grant_id": "grant:root", "principal_id": "person:alice", "key_id": "key:root",
            "scope_id": "person:alice", "operations": ["*"], "capabilities": [], "grant_class": "ROOT",
            "valid_from_log_sequence": 0, "valid_to_log_sequence": None,
        }],
    }
    valid = {
        "body_cid": "bafkreiaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "log_sequence": 0,
        "body": body,
        "payload": {"profile": oracle.PROFILE, "schema_version": "1.0.0", "data": genesis, "valid_from_ns": 0, "valid_to_ns": None},
    }
    assert oracle.evaluate_records([valid])["decision"] == "ACCEPT"
    invalid = {**valid, "payload": {**valid["payload"], "schema_version": "2.0.0"}}
    result = oracle.evaluate_records([invalid])
    assert result["error"]["code"] == "UNSUPPORTED_SCHEMA_VERSION"


def test_cli_identify_is_deterministic_canonical_json():
    completed = subprocess.run(
        [sys.executable, str(ORACLE_PATH), "identify"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    parsed = json.loads(completed.stdout)
    assert parsed == oracle.identify()
    assert completed.stdout.strip() == oracle.canonical_json(parsed)


def test_byte_oracle_exposes_verified_records_without_changing_old_api():
    python_dir = str(BYTE_ORACLE_PATH.parent)
    sys.path.insert(0, python_dir)
    try:
        vector = ROOT / "conformance/vectors/wave01-valid.json"
        order = oracle.pwm_oracle.verify_bundle(vector)
        records = oracle.pwm_oracle.verify_bundle_records(vector)
    finally:
        sys.path.remove(python_dir)
    assert [record["body_cid"] for record in records] == order
    assert records[0]["body"]["event_kind"] == "pwm.genesis"
