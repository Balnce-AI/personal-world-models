from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import pytest

from pwm import PersonalWorldModel as PublicPersonalWorldModel

from pwm_hpl_ref.adapters import (
    AuthorizationRequiredError,
    EventDraft,
    InMemoryStorageAdapter,
    LifecycleError,
    MultimodalReference,
    StreamWindow,
)
from pwm_hpl_ref.model_query import ModelQuery, ModelQueryAuthorization
from pwm_hpl_ref.sdk import PersonalWorldModel, discover_capabilities
from pwm_hpl_ref.self_models import ModelRecord
from pwm_hpl_ref.simulation import SimulationSource, SimulationStep


ROOT = Path(__file__).parents[1]


def deny(_operation, _request):
    return None


def allow(operation, request):
    if operation == "query":
        return ModelQueryAuthorization(
            "auth:test", request.purpose, request.recipient, "PERSONAL", request.subjects,
            request.world_id, "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00",
            "2026-06-01T00:00:00+00:00",
        )
    return {"authorizationRef": f"auth:{operation}"}


def test_public_pwm_package_exposes_the_sdk_facade():
    assert PublicPersonalWorldModel is PersonalWorldModel
    assert isinstance(PublicPersonalWorldModel.open(authorize=deny), PersonalWorldModel)


def test_storage_has_bounded_lifecycle_and_isolation():
    storage = InMemoryStorageAdapter()
    with pytest.raises(LifecycleError):
        storage.append_event(EventDraft("entity.put", {"id": "x"}, "owner"))
    storage.start()
    payload = {"id": "x", "nested": {"value": 1}}
    storage.append_event(EventDraft("entity.put", payload, "owner", "2026-01-01T00:00:00+00:00"))
    payload["nested"]["value"] = 2
    assert storage.ordered_events()[0].payload["nested"]["value"] == 1
    storage.stop()
    with pytest.raises(LifecycleError):
        storage.start()


def test_sdk_append_materialize_and_capability_discovery_do_not_grant_authority():
    storage = InMemoryStorageAdapter()
    with PersonalWorldModel.experimental(storage, allow) as pwm:
        pwm.append_event(EventDraft("entity.put", {"id": "person", "type": "Person"}, "person"))
        assert "person" in pwm.materialize().entities
        descriptors = discover_capabilities(storage)
        assert descriptors[0].capability_id == "pwm.storage.memory"
        assert not hasattr(descriptors[0], "authorized")


def test_simulation_is_deterministic_and_event_only():
    steps = (
        SimulationStep(2, "entity.put", {"id": "second", "type": "Device"}),
        SimulationStep(1, "entity.put", {"id": "first", "type": "Device"}),
    )
    ids = []
    for _ in range(2):
        storage = InMemoryStorageAdapter()
        with PersonalWorldModel.experimental(storage, allow) as pwm:
            ids.append(tuple(event.event_id for event in SimulationSource(steps).emit(pwm)))
            assert set(pwm.materialize().entities) == {"first", "second"}
    assert ids[0] == ids[1]


def test_multimodal_stream_window_requires_provenance_and_marks_promotion_boundary():
    reference = MultimodalReference("cas://sha256/abc", "audio/wav", "sha256:abc", ("event:capture",))
    window = StreamWindow("microphone", 0, "2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z", (reference,))
    assert window.durable_event_ref is None
    assert replace(window, durable_event_ref="event:promoted").durable_event_ref == "event:promoted"
    with pytest.raises(ValueError):
        MultimodalReference("cas://x", "image/png", "sha256:x", ())


def test_query_requires_injected_bound_authorization():
    storage = InMemoryStorageAdapter()

    def authorize(operation, request):
        assert operation == "query"
        return ModelQueryAuthorization(
            "auth:1", request.purpose, request.recipient, "PERSONAL", request.subjects,
            request.world_id, "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00",
            "2026-06-01T00:00:00+00:00",
        )

    with PersonalWorldModel.experimental(storage, authorize) as pwm:
        result = pwm.query(ModelQuery(("person",)))
    assert result["authorizationRef"] == "auth:1"


def test_possible_world_is_isolated_from_materialized_state():
    storage = InMemoryStorageAdapter()
    with PersonalWorldModel.experimental(storage, allow) as pwm:
        evidence = pwm.append_event(EventDraft("entity.put", {"id": "person", "type": "Person"}, "person"))
        world, branch = pwm.possible_world(
            "rain", ({"predicate": "weather", "object": "rain"},), (evidence.event_id,)
        )
        assert world.world_id
        assert world.to_record()["baseStateId"]
        assert len(branch.assertions) == 1
        assert pwm.materialize().assertions == {}


def test_sdk_model_lifecycle_persists_only_generated_events():
    storage = InMemoryStorageAdapter()
    with PersonalWorldModel.experimental(storage, allow) as pwm:
        evidence = pwm.append_event(EventDraft("assertion.put", {
            "id": "evidence:1", "subject": "person", "predicate": "meal", "object": "vegetarian",
            "recordTime": "2026-01-01T00:00:00+00:00", "epistemicStatus": "ASSERTED",
        }, "person", "2026-01-01T00:00:00+00:00"))
        model = ModelRecord.create(
            model_kind="SELF", family_id="pwm.preference", subject_ids=("person",), perspective="person",
            state={"meal": "vegetarian"}, epistemic_status="INFERRED", confidence_ppm=700_000,
            uncertainty={"kind": "sparse-evidence"}, provenance_refs=(evidence.event_id,),
            record_time="2026-01-01T00:00:01+00:00",
        )
        proposal = pwm.propose_model(model, "model:external")
        pwm.accept_model(model, "person", proposal.event_id)
        assert pwm.materialize().models[model.model_id]["lifecycleStatus"] == "ACCEPTED"


def test_sdk_denies_canonical_writes_without_injected_authorization():
    storage = InMemoryStorageAdapter()
    with PersonalWorldModel.experimental(storage, deny) as pwm:
        with pytest.raises(AuthorizationRequiredError, match="authorization required"):
            pwm.append_event(EventDraft("entity.put", {"id": "person"}, "person"))


def test_documented_quickstart_examples_execute():
    scripts = (
        "a_create.py", "b_derive_model.py", "c_local_model.py", "d_hpl_projection.py",
        "e_possible_world.py", "f_custom_adapter.py", "g_benchmark.py",
    )
    for name in scripts:
        result = subprocess.run(
            [sys.executable, str(ROOT / "examples/quickstart" / name)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{name}: {result.stdout}{result.stderr}"
