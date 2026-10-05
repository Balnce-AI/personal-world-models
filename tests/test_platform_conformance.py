import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = re.compile(r"^(?:[a-z][a-z0-9-]*\.)+[a-z][a-z0-9-]*$")


def load(path):
    return json.loads((ROOT / path).read_text())


def validate(schema_path, value):
    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def test_schema_catalog_is_complete_and_resolvable():
    catalog = load("schemas/catalog.json")
    ids = [entry["id"] for entry in catalog["entries"]]
    assert len(ids) == len(set(ids))
    assert {entry["classification"] for entry in catalog["entries"]} == {"NORMATIVE", "REFERENCE"}

    schema_ids = []
    for entry in catalog["entries"]:
        path = ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        schema_ids.append(schema["$id"])
    assert len(schema_ids) == len(set(schema_ids))
    cataloged_public = {
        entry["path"] for entry in catalog["entries"]
        if entry["path"].startswith("schemas/json-schema/")
    }
    actual_public = {
        str(path.relative_to(ROOT)) for path in (ROOT / "schemas/json-schema").glob("*.json")
    }
    assert cataloged_public == actual_public


def test_conformance_manifest_references_suites_and_files_without_claiming_conformance():
    manifest = load("conformance/manifest.json")
    validate("conformance/schemas/conformance-manifest.schema.json", manifest)
    assert manifest["claims"] == []

    suites = {suite["id"]: suite for suite in manifest["suites"]}
    assert len(suites) == len(manifest["suites"])
    fixture_paths = [fixture for suite in suites.values() for fixture in suite["fixtures"]]
    assert len(fixture_paths) == len(set(fixture_paths))
    assert suites["PWM-PROVENANCE-WAVE01"]["profile"] == "pwm-public-provenance-v1"
    assert suites["PWM-PROVENANCE-WAVE01"]["format"] == "wave01-profile-v1"
    assert all((ROOT / fixture).is_file() for suite in suites.values() for fixture in suite["fixtures"])

    levels = sorted(manifest["levels"], key=lambda level: level["ordinal"])
    assert len({level["id"] for level in levels}) == len(levels)
    assert [level["ordinal"] for level in levels] == list(range(1, len(levels) + 1))
    for level in levels:
        assert set(level["requiredSuites"]) <= suites.keys()
        available = {feature for suite_id in level["requiredSuites"] for feature in suites[suite_id]["features"]}
        assert set(level["features"]) <= available


def test_semantic_vectors_validate_and_have_unique_ids_and_observable_expectations():
    manifest = load("conformance/manifest.json")
    semantic_suites = [suite for suite in manifest["suites"] if suite["format"] == "semantic-vector-v1"]
    case_ids = []
    for suite in semantic_suites:
        for fixture in suite["fixtures"]:
            vector = load(fixture)
            validate("conformance/schemas/conformance-vector.schema.json", vector)
            assert vector["suiteId"] == suite["id"]
            assert vector["suiteVersion"] == suite["version"]
            expected_decision = "ACCEPT" if vector["polarity"] == "valid" else "REJECT"
            for case in vector["cases"]:
                case_ids.append(case["id"])
                assert case["expected"]["decision"] == expected_decision
                assert case["expected"]["invariants"]
                assert set(case["expected"]) - {"decision", "invariants"}
    assert len(case_ids) == len(set(case_ids))


def test_required_semantic_behaviors_have_vectors():
    text = " ".join(
        json.dumps(load(path), sort_keys=True).lower()
        for path in (
            "conformance/vectors/model-ecology-valid.json",
            "conformance/vectors/model-ecology-invalid.json",
            "conformance/vectors/hpl-valid.json",
            "conformance/vectors/hpl-invalid.json",
        )
    )
    for term in (
        "replay", "lifecycle", "temporal", "family-kind", "contradiction", "privacy",
        "filtering", "cycle-rejection", "possible-world", "authorization-binding",
    ):
        assert term in text


def test_extension_registry_and_template_enforce_namespaces():
    registry = load("extensions/registry.json")
    assert registry["reservedNamespaces"] == ["pwm", "hpl", "fc", "conformance"]
    assert registry["stabilityLevels"] == ["EXPERIMENTAL", "PROVISIONAL", "STABLE", "DEPRECATED"]
    assert len({item["extensionId"] for item in registry["extensions"]}) == len(registry["extensions"])
    assert all(NAMESPACE.fullmatch(item["extensionId"]) for item in registry["extensions"])
    for item in registry["extensions"]:
        manifest = load(item["manifest"])
        validate("schemas/json-schema/extension-manifest.schema.json", manifest)
        assert manifest["extensionId"] == item["extensionId"]
        assert manifest["version"] == item["version"]
        assert manifest["stability"] == item["stability"]
        assert all(
            name.startswith(manifest["extensionId"] + ".")
            for name in manifest["features"] + manifest["eventTypes"]
        )

    manifest = load("templates/extension/manifest.json")
    validate("schemas/json-schema/extension-manifest.schema.json", manifest)
    assert NAMESPACE.fullmatch(manifest["extensionId"])
    for name in manifest["features"] + manifest["eventTypes"]:
        assert name.startswith(manifest["extensionId"] + ".")

    validate("schemas/json-schema/pwm-model-family.schema.json", load("templates/model-family/manifest.json"))


def test_wave01_vectors_remain_distinct_from_json_semantic_envelopes():
    assert load("conformance/vectors/wave01-valid.json")["profile"] == "pwm-public-provenance-v1"
    assert load("conformance/vectors/wave01-invalid.json")["profile"] == "pwm-public-provenance-v1"
    for path in ROOT.glob("conformance/vectors/model-ecology-*.json"):
        assert json.loads(path.read_text())["profile"] == "pwm-json-semantics-v1"
    for path in ROOT.glob("conformance/vectors/hpl-*.json"):
        assert json.loads(path.read_text())["profile"] == "pwm-json-semantics-v1"
    expected = load("conformance/expectations/wave01-valid.json")
    bundle = load(expected["fixture"])
    assert expected["acceptedRecordCount"] == len(bundle["records"])
    assert set(expected["expectedReplayOrder"]) == {record["body_cid"] for record in bundle["records"]}
    negative = load("conformance/expectations/wave01-negative-operations.json")
    assert negative["baseFixture"] == expected["fixture"]
    assert len(negative["cases"]) >= 12
    assert len({case["id"] for case in negative["cases"]}) == len(negative["cases"])
    assert all(re.fullmatch(r"[A-Z][A-Z0-9_]+", case["expectedError"]) for case in negative["cases"])
