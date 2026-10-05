import importlib.util
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pwm_hpl_ref.adapters import EvidenceAdapter, LifecycleError, UnknownSemanticsError


ROOT = Path(__file__).parents[1]


def test_example_extension_manifest_is_registered_and_valid():
    manifest = json.loads((ROOT / "examples/third-party-adapter/extension-manifest.json").read_text())
    schema = json.loads((ROOT / "schemas/json-schema/extension-manifest.schema.json").read_text())
    Draft202012Validator(schema).validate(manifest)
    registry = json.loads((ROOT / "extensions/registry.json").read_text())
    assert any(item["extensionId"] == manifest["extensionId"] for item in registry["extensions"])
    implementation = ROOT / "examples/third-party-adapter/acme_weather/adapter.py"
    assert manifest["contractDigest"] == "sha256:" + hashlib.sha256(implementation.read_bytes()).hexdigest()


def load_example():
    path = ROOT / "examples/third-party-adapter/acme_weather/adapter.py"
    spec = importlib.util.spec_from_file_location("acme_weather.adapter", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_third_party_adapter_uses_public_protocol_and_fails_unknown_closed():
    module = load_example()
    adapter = module.AcmeWeatherAdapter({"air.temperature.celsius": 21.5})
    assert isinstance(adapter, EvidenceAdapter)
    with pytest.raises(LifecycleError):
        adapter.observe("air.temperature.celsius")
    adapter.start()
    manifest = json.loads((ROOT / "examples/third-party-adapter/extension-manifest.json").read_text())
    assert adapter.capabilities()[0].version == manifest["version"]
    observation = adapter.observe("air.temperature.celsius")
    assert observation.references[0].provenance_refs == ("acme:fixture:1",)
    with pytest.raises(UnknownSemanticsError):
        adapter.observe("vendor.secret.score")
    adapter.stop()
