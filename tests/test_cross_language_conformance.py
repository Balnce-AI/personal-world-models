import json
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VECTOR = ROOT / "conformance" / "vectors" / "wave01-valid.json"
ORACLE = ROOT / "conformance" / "python" / "pwm_oracle.py"
INVALID = ROOT / "conformance" / "vectors" / "wave01-invalid.json"


def run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )


def test_checked_in_vectors_are_reproducible_and_cross_language_equal(tmp_path: Path):
    generated = tmp_path / "generated.json"
    emit = run("cargo", "run", "-q", "-p", "pwm-cli", "--", "vectors", "emit", "--output", str(generated))
    assert emit.returncode == 0, emit.stderr
    assert generated.read_bytes() == VECTOR.read_bytes()

    rust = run("cargo", "run", "-q", "-p", "pwm-cli", "--", "event", "replay", "--bundle", str(VECTOR))
    python = run(sys.executable, str(ORACLE), "--emit-replay", str(VECTOR))
    assert rust.returncode == 0, rust.stderr
    assert python.returncode == 0, python.stderr
    assert json.loads(rust.stdout) == json.loads(python.stdout)


def test_rust_and_python_reject_a_mutated_signed_body(tmp_path: Path):
    specification = importlib.util.spec_from_file_location("pwm_wave01_oracle_mutation", ORACLE)
    oracle = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = oracle
    specification.loader.exec_module(oracle)
    bundle = json.loads(VECTOR.read_text(encoding="utf-8"))
    body = oracle.decode_canonical(bytes.fromhex(bundle["records"][0]["body_cbor_hex"]))
    body["event_time"] += 1
    bundle["records"][0]["body_cbor_hex"] = oracle.encode(body).hex()
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(bundle), encoding="utf-8")

    rust = run("cargo", "run", "-q", "-p", "pwm-cli", "--", "event", "verify", "--bundle", str(mutated))
    python = run(sys.executable, str(ORACLE), str(mutated))
    assert rust.returncode != 0
    assert python.returncode != 0


def test_rust_and_python_reject_key_used_before_activation(tmp_path: Path):
    bundle = json.loads(VECTOR.read_text(encoding="utf-8"))
    bundle["author_keys"][0]["active_from_log_sequence"] = 100
    mutated = tmp_path / "preactivation.json"
    mutated.write_text(json.dumps(bundle), encoding="utf-8")

    rust = run("cargo", "run", "-q", "-p", "pwm-cli", "--", "event", "verify", "--bundle", str(mutated))
    python = run(sys.executable, str(ORACLE), str(mutated))
    assert rust.returncode != 0
    assert python.returncode != 0


def test_vectors_cover_historical_verification_after_key_rotation_and_revocation():
    bundle = json.loads(VECTOR.read_text(encoding="utf-8"))
    keys = {item["key_id"]: item for item in bundle["author_keys"]}
    assert keys["key:root"]["revoked_at_log_sequence"] == 1
    assert keys["key:root:v2"]["active_from_log_sequence"] == 1

    frontiers = [
        record["receipt_body_cbor_hex"] for record in bundle["records"]
    ]
    assert frontiers[0] != frontiers[1]

    rust = run("cargo", "run", "-q", "-p", "pwm-cli", "--", "event", "verify", "--bundle", str(VECTOR))
    python = run(sys.executable, str(ORACLE), str(VECTOR))
    assert rust.returncode == 0, rust.stderr
    assert python.returncode == 0, python.stderr


def test_python_oracle_rejects_every_published_malformed_cbor_vector():
    specification = importlib.util.spec_from_file_location("pwm_wave01_oracle", ORACLE)
    oracle = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = oracle
    specification.loader.exec_module(oracle)
    corpus = json.loads(INVALID.read_text(encoding="utf-8"))
    for case in corpus["canonical_cbor"]:
        try:
            oracle.decode_canonical(bytes.fromhex(case["hex"]))
        except oracle.ProfileError:
            continue
        raise AssertionError(f"Python oracle accepted invalid case {case['name']}")


def test_python_oracle_rejects_non_exact_record_shapes():
    specification = importlib.util.spec_from_file_location("pwm_wave01_oracle_shapes", ORACLE)
    oracle = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = oracle
    specification.loader.exec_module(oracle)
    bundle = json.loads(VECTOR.read_text(encoding="utf-8"))
    body = oracle.decode_canonical(bytes.fromhex(bundle["records"][0]["body_cbor_hex"]))
    receipt = oracle.decode_canonical(bytes.fromhex(bundle["records"][0]["receipt_body_cbor_hex"]))

    malformed_bodies = [
        {**body, "extra": None},
        {**body, "author_sequence": False},
        {**body, "event_time": "not-an-integer"},
    ]
    malformed_receipts = [
        {**receipt, "extra": None},
        {**receipt, "log_sequence": False},
        {**receipt, "ingestion_time": "not-an-integer"},
    ]
    for malformed in malformed_bodies:
        try:
            oracle.validate_event_body(malformed)
        except oracle.ProfileError:
            continue
        raise AssertionError("Python oracle accepted a malformed EventBody")
    for malformed in malformed_receipts:
        try:
            oracle.validate_receipt_body(malformed)
        except oracle.ProfileError:
            continue
        raise AssertionError("Python oracle accepted a malformed AppendReceiptBody")

    for boundary in (-(2**63), 2**63 - 1):
        oracle.validate_event_body({**body, "event_time": boundary})
        oracle.validate_receipt_body({**receipt, "ingestion_time": boundary})

    for out_of_range in (-(2**63) - 1, 2**63):
        for validate, malformed in (
            (oracle.validate_event_body, {**body, "event_time": out_of_range}),
            (
                oracle.validate_receipt_body,
                {**receipt, "ingestion_time": out_of_range},
            ),
        ):
            try:
                validate(malformed)
            except oracle.ProfileError:
                continue
            raise AssertionError("Python oracle accepted an out-of-range timestamp")
