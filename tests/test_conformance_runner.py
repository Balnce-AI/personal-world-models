import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "pwm_conformance.py"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def write_catalog(tmp_path: Path, outputs: dict[str, dict], pretty: bool = False):
    vector = {
        "suiteId": "TEST-SUITE",
        "profile": "test-profile-v1",
        "cases": [
            {
                "id": "case-1",
                "input": {"events": [{"eventId": "evt-1"}, {"eventId": "evt-2"}]},
                "expected": {
                    "decision": "ACCEPT",
                    "materialized": {"modelIds": ["model-a"]},
                    "query": {"modelIds": ["model-a"]},
                    "invariants": ["not part of adapter output"],
                },
            }
        ],
    }
    vector_path = tmp_path / "vector.json"
    vector_path.write_text(json.dumps(vector), encoding="utf-8")
    catalog = {
        "suites": [
            {
                "id": "TEST-SUITE",
                "profile": "test-profile-v1",
                "fixtures": [str(vector_path)],
            }
        ],
        "levels": [{"id": "TEST-LEVEL", "requiredSuites": ["TEST-SUITE"]}],
    }
    catalog_path = tmp_path / "manifest.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    adapter = tmp_path / "fake_adapter.py"
    adapter.write_text(
        "import json,sys\n"
        f"outputs = {outputs!r}\n"
        "name, profile, suite = sys.argv[1:]\n"
        "value = {'contract':'pwm-conformance-result-v1','profile':profile,'suite':suite,'cases':[outputs[name]]}\n"
        + ("print(json.dumps(value, indent=2, sort_keys=True))\n" if pretty else "print(json.dumps(value, sort_keys=True, separators=(',', ':')))\n"),
        encoding="utf-8",
    )
    implementations = tmp_path / "implementations"
    implementations.mkdir()
    for name in outputs:
        implementation = {
            "name": name,
            "version": "1.0.0",
            "language": "test",
            "command": [sys.executable, str(adapter), name, "{profile}", "{suite}", "{bundle}"],
            "profiles": ["test-profile-v1"],
        }
        # The fake ignores the final bundle argument but every adapter receives it.
        implementation["command"] = [sys.executable, "-c", (
            "import json,runpy,sys;sys.argv=[sys.argv[1],*sys.argv[2:5]];runpy.run_path(sys.argv[0],run_name='__main__')"
        ), str(adapter), name, "{profile}", "{suite}", "{bundle}"]
        (implementations / f"{name}.json").write_text(json.dumps(implementation), encoding="utf-8")
    return catalog_path, implementations


def run(*args: str):
    return subprocess.run(
        [sys.executable, str(RUNNER), *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def test_verify_passes_with_temporary_language_neutral_adapter(tmp_path: Path):
    actual = {
        "id": "case-1",
        "actual": {
            "decision": "ACCEPT",
            "materialized": {"modelIds": ["model-a"]},
            "query": {"modelIds": ["model-a"]},
        },
    }
    catalog, implementations = write_catalog(tmp_path, {"fake-python": actual})
    result = run(
        "verify", "--implementation", "fake-python", "--profile", "TEST-LEVEL",
        "--conformance-manifest", str(catalog), "--implementations-dir", str(implementations),
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS fake-python TEST-LEVEL (1 cases)" in result.stdout


def test_compare_reports_first_event_and_section_divergence(tmp_path: Path):
    expected = {
        "id": "case-1",
        "actual": {"decision": "ACCEPT", "materialized": {"modelIds": ["model-a"]}, "query": {"modelIds": ["model-a"]}},
        "events": [{"eventId": "evt-1", "status": "applied"}, {"eventId": "evt-2", "status": "applied"}],
    }
    divergent = {
        "id": "case-1",
        "actual": {"decision": "ACCEPT", "materialized": {"modelIds": ["model-b"]}, "query": {"modelIds": ["model-a"]}},
        "events": [{"eventId": "evt-1", "status": "applied"}, {"eventId": "evt-2", "status": "rejected"}],
    }
    catalog, implementations = write_catalog(tmp_path, {"one": expected, "two": divergent})
    result = run(
        "compare", "--implementations", "one", "two", "--suite", "TEST-SUITE",
        "--conformance-manifest", str(catalog), "--implementations-dir", str(implementations),
    )
    assert result.returncode == 1
    assert "first divergent event [1] evt-2" in result.stdout
    assert "materialized state" in result.stdout
    assert "model-b" in result.stdout


def test_diff_reports_named_semantic_sections(tmp_path: Path):
    expected = {
        "privacy": {"effective": "HIGHLY_SENSITIVE"},
        "topology": {"acyclic": True},
        "projection": {"issued": False},
        "error": {"code": "AUTHORITY_EXPIRED"},
        "canonicalBytes": "00ff",
    }
    actual = {
        "privacy": {"effective": "PERSONAL"},
        "topology": {"acyclic": False},
        "projection": {"issued": True},
        "error": {"code": "WRONG_ERROR"},
        "canonicalBytes": "ff00",
    }
    expected_path = tmp_path / "expected.json"
    actual_path = tmp_path / "actual.json"
    expected_path.write_text(canonical(expected), encoding="utf-8")
    actual_path.write_text(canonical(actual), encoding="utf-8")
    result = run("diff", "--expected", str(expected_path), "--actual", str(actual_path))
    assert result.returncode == 1
    for section in ("privacy", "topology", "HPL", "error code", "canonical bytes"):
        assert section in result.stdout


def test_verify_rejects_noncanonical_adapter_stdout(tmp_path: Path):
    actual = {
        "id": "case-1",
        "actual": {"decision": "ACCEPT", "materialized": {"modelIds": ["model-a"]}, "query": {"modelIds": ["model-a"]}},
    }
    catalog, implementations = write_catalog(tmp_path, {"pretty": actual}, pretty=True)
    result = run(
        "verify", "--implementation", "pretty", "--profile", "TEST-SUITE",
        "--conformance-manifest", str(catalog), "--implementations-dir", str(implementations),
    )
    assert result.returncode == 2
    assert "output is not canonical JSON" in result.stderr


def test_compare_requires_two_implementations(tmp_path: Path):
    actual = {"id": "case-1", "actual": {"decision": "ACCEPT"}}
    catalog, implementations = write_catalog(tmp_path, {"only": actual})
    result = run(
        "compare", "--implementations", "only", "--suite", "TEST-SUITE",
        "--conformance-manifest", str(catalog), "--implementations-dir", str(implementations),
    )
    assert result.returncode == 2
    assert "at least two implementations" in result.stderr


def test_packaged_cli_loads_repository_runner():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from pwm_hpl_ref.conformance_cli import main; "
            "sys.argv = ['pwm-conformance', '--help']; main()",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Language-neutral PWM conformance runner" in result.stdout
