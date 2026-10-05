from dataclasses import replace

import pytest

from pwm_hpl_ref.contradiction import ContradictionLifecycle, ContradictionRecord, detect_simple_contradictions
from pwm_hpl_ref.model_query import ModelQuery, ModelQueryAuthorization, execute_query
from pwm_hpl_ref.model_registry import default_registry
from pwm_hpl_ref.plog import PLog
from pwm_hpl_ref.possible_worlds import PossibleWorld
from pwm_hpl_ref.privacy import DeclassificationBoundary
from pwm_hpl_ref.pwm import Materializer
from pwm_hpl_ref.self_models import ModelLifecycle, ModelRecord
from pwm_hpl_ref.topology import ModelEdge


NOW = "2026-10-01T12:00:00+00:00"
PERSON = "person:self"


def _evidence(identifier, privacy="PERSONAL", value=True):
    return {
        "id": identifier, "subject": PERSON, "predicate": "test.evidence", "object": value,
        "recordTime": NOW, "epistemicStatus": "OBSERVED", "privacyClass": privacy,
    }


def _grant(privacy="PERSONAL", world_id="world:actual"):
    return ModelQueryAuthorization(
        "authority:test", "research", "local:researcher", privacy, (PERSON,), world_id,
        "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00", NOW,
    )


def _model(evidence_ref, **kwargs):
    values = dict(
        model_kind="SELF", family_id="pwm.preference", subject_ids=(PERSON,), perspective=PERSON,
        state={"aggregate": "vegetarian", "secret": "medical reason"}, epistemic_status="INFERRED",
        confidence_ppm=800_000, uncertainty={}, provenance_refs=(evidence_ref,), record_time=NOW,
    )
    values.update(kwargs)
    return ModelRecord.create(**values)


def test_relationship_and_perspective_constraints_apply_helper_and_replay_side():
    log = PLog()
    evidence = log.append("assertion.put", _evidence("e"), PERSON, record_time=NOW)
    invalid = _model(evidence.event_id, model_kind="OTHER", perspective=PERSON)
    lifecycle = ModelLifecycle(default_registry())
    with pytest.raises(ValueError, match="distinct"):
        lifecycle.propose(log, invalid, PERSON)

    forged = _model(evidence.event_id, model_kind="OTHER", perspective="person:observer").to_record()
    forged["perspective"] = PERSON
    event = log.append("model.proposed", forged, PERSON, record_time=NOW)
    assert event.event_id in Materializer().materialize(log).unsupported_events

    relationship = _model(evidence.event_id, model_kind="RELATIONSHIP", family_id="fc.social")
    with pytest.raises(ValueError, match="two distinct"):
        lifecycle.propose(log, relationship, PERSON)


def test_sensitive_evidence_propagates_and_forged_downgrade_fails_closed():
    log = PLog()
    evidence = log.append("assertion.put", _evidence("sensitive", "SENSITIVE"), PERSON, record_time=NOW)
    lifecycle = ModelLifecycle(default_registry())
    model = _model(evidence.event_id, privacy_class="PUBLIC")
    proposal = lifecycle.propose(log, model, PERSON)
    lifecycle.accept(log, model, PERSON, proposal)
    state = Materializer().materialize(log)
    assert state.models[model.model_id]["effectivePrivacyClass"] == "SENSITIVE"
    assert execute_query(state, ModelQuery((PERSON,)), _grant())["models"] == []

    forged_log = PLog()
    forged_evidence = forged_log.append("assertion.put", _evidence("s", "SENSITIVE"), PERSON, record_time=NOW)
    forged = _model(forged_evidence.event_id, privacy_class="PUBLIC").to_record()
    event = forged_log.append("model.proposed", forged, PERSON, record_time=NOW)
    assert event.event_id in Materializer().materialize(forged_log).unsupported_events


def test_approved_proof_boundary_releases_only_named_fields_without_raw_provenance():
    log = PLog()
    evidence = log.append("assertion.put", _evidence("sensitive", "SENSITIVE"), PERSON, record_time=NOW)
    log.append("policy.put", {"id": "policy:proof", "privacyFloor": "PUBLIC"}, PERSON, record_time=NOW)
    boundary = DeclassificationBoundary.create(
        "PROOF", "SENSITIVE", "PERSONAL", (evidence.event_id,), "policy:proof", "release aggregate only",
        released_fields=("aggregate",), approved=True,
    )
    model = _model(
        evidence.event_id, privacy_class="SENSITIVE", policy_refs=("policy:proof",),
        privacy_boundaries=(boundary,),
    )
    lifecycle = ModelLifecycle(default_registry())
    proposal = lifecycle.propose(log, model, PERSON)
    lifecycle.accept(log, model, PERSON, proposal)
    projected = execute_query(Materializer().materialize(log), ModelQuery((PERSON,)), _grant())["models"][0]
    assert projected["state"] == {"aggregate": "vegetarian"}
    assert "provenanceRefs" not in projected
    assert "dependencyRefs" not in projected


def test_semantic_contradictions_remain_candidates_and_simple_detection_is_deterministic():
    assertions = [
        {"id": "b", "subject": PERSON, "predicate": "role", "object": "researcher", "recordTime": NOW, "epistemicStatus": "ASSERTED"},
        {"id": "a", "subject": PERSON, "predicate": "role", "object": "designer", "recordTime": NOW, "epistemicStatus": "ASSERTED"},
    ]
    first = detect_simple_contradictions(assertions, NOW)[0]
    second = detect_simple_contradictions(reversed(assertions), NOW)[0]
    assert first.contradiction_id == second.contradiction_id

    semantic = replace(first, detection_method="SEMANTIC")
    log = PLog()
    for assertion in assertions:
        log.append("assertion.put", {**assertion, "privacyClass": "PERSONAL"}, PERSON, record_time=NOW)
    ContradictionLifecycle().propose(log, semantic, PERSON)
    state = Materializer().materialize(log)
    assert semantic.contradiction_id in state.contradiction_candidates
    assert semantic.contradiction_id not in state.contradictions


def test_possible_world_binding_prevents_actual_world_query_leakage():
    log = PLog()
    evidence = log.append("assertion.put", _evidence("prediction:1"), PERSON, record_time=NOW)
    actual = Materializer().materialize(log)
    world = PossibleWorld.create(
        "missed train", ({"subject": PERSON, "predicate": "delay", "object": 30},), (evidence.event_id,)
    ).bind(actual, NOW)
    branch = world.branch(actual)
    assert world.to_record()["baseStateId"] == branch.base_state_id
    assert set(actual.assertions) == {"prediction:1"}
    assert not any(item.get("possibleWorldId") for item in actual.assertions.values())
    with pytest.raises(ValueError, match="world"):
        execute_query(branch, ModelQuery((PERSON,)), _grant())
    projection = execute_query(
        branch, ModelQuery((PERSON,), world_id=world.world_id), _grant(world_id=world.world_id)
    )
    assert projection["models"] == []
    with pytest.raises(ValueError, match="distinct|identifier"):
        replace(world, world_id="world:actual").branch(actual)


def test_unknown_privacy_classes_fail_closed():
    with pytest.raises(ValueError, match="unknown privacy"):
        execute_query(Materializer().materialize(PLog()), ModelQuery((PERSON,), max_privacy_class="SECRET"), _grant())


def test_query_authorization_is_world_and_time_bound():
    state = Materializer().materialize(PLog())
    stale = ModelQueryAuthorization(
        "authority:stale", "research", "local:researcher", "PERSONAL", (PERSON,),
        "world:actual", "2025-01-01T00:00:00+00:00", "2025-02-01T00:00:00+00:00", NOW,
    )
    with pytest.raises(ValueError, match="temporally valid"):
        execute_query(state, ModelQuery((PERSON,)), stale)
    wrong_world = ModelQueryAuthorization(
        "authority:world", "research", "local:researcher", "PERSONAL", (PERSON,),
        "world:other", "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00", NOW,
    )
    with pytest.raises(ValueError, match="world"):
        execute_query(state, ModelQuery((PERSON,)), wrong_world)


def test_world_kind_and_family_specific_kind_constraints_are_enforced():
    registry = default_registry()
    world = _model(
        "event:evidence",
        model_kind="WORLD",
        family_id="pwm.physical-environment",
        subject_ids=("place:kitchen",),
        perspective=PERSON,
    ).to_record()
    registry.validate_model(world)
    invalid = dict(world)
    invalid["modelKind"] = "SELF"
    with pytest.raises(ValueError, match="does not allow"):
        registry.validate_model(invalid)


def test_relationship_projection_requires_authority_for_every_participant():
    log = PLog()
    evidence = log.append(
        "assertion.put",
        _evidence("relationship:evidence"),
        PERSON,
        record_time=NOW,
    )
    model = _model(
        evidence.event_id,
        model_kind="RELATIONSHIP",
        family_id="pwm.relationship",
        subject_ids=(PERSON, "person:other"),
    )
    lifecycle = ModelLifecycle(default_registry())
    proposal = lifecycle.propose(log, model, PERSON)
    lifecycle.accept(log, model, PERSON, proposal)
    state = Materializer().materialize(log)
    assert execute_query(state, ModelQuery((PERSON,)), _grant())["models"] == []
    joint = ModelQueryAuthorization(
        "authority:joint", "research", "local:researcher", "PERSONAL", (PERSON, "person:other"),
        "world:actual", "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00", NOW,
    )
    assert len(execute_query(state, ModelQuery((PERSON,)), joint)["models"]) == 1


def test_event_payload_cannot_change_after_hashing():
    log = PLog()
    event = log.append("assertion.put", _evidence("e", value="original"), PERSON, record_time=NOW)
    event.payload["object"] = "tampered-return-value"
    assert Materializer().materialize(log).assertions["e"]["object"] == "original"
    log.events[event.event_id].payload["object"] = "tampered-storage"
    with pytest.raises(ValueError, match="integrity"):
        Materializer().materialize(log)


def test_declassification_uses_only_boundary_at_effective_output_level():
    log = PLog()
    evidence = log.append("assertion.put", _evidence("s", "SENSITIVE"), PERSON, record_time=NOW)
    log.append("policy.put", {"id": "policy:public", "privacyFloor": "PUBLIC"}, PERSON, record_time=NOW)
    public = DeclassificationBoundary.create(
        "PROOF", "SENSITIVE", "PUBLIC", (evidence.event_id,), "policy:public", "aggregate proof",
        released_fields=("aggregate",), approved=True,
    )
    unrelated = DeclassificationBoundary.create(
        "REDACTION", "SENSITIVE", "SENSITIVE", (evidence.event_id,), "policy:public", "no downgrade",
        released_fields=("secret",), approved=True,
    )
    model = _model(
        evidence.event_id, privacy_class="PUBLIC", policy_refs=("policy:public",),
        privacy_boundaries=(public, unrelated),
    )
    lifecycle = ModelLifecycle(default_registry())
    proposal = lifecycle.propose(log, model, PERSON)
    lifecycle.accept(log, model, PERSON, proposal)
    projected = execute_query(
        Materializer().materialize(log), ModelQuery((PERSON,), max_privacy_class="PUBLIC"), _grant("PUBLIC")
    )["models"][0]
    assert projected["state"] == {"aggregate": "vegetarian"}
    assert "provenanceRefs" not in projected


def test_possible_world_cannot_alias_actual_world_and_cycles_fail_at_replay():
    invalid_world = _model(
        "event:evidence", model_kind="POSSIBLE_WORLD", family_id="pwm.imagination-possible-worlds",
        state={"worldId":"world:actual","parentWorldId":"world:actual","baseStateId":"base:1","baseTime":NOW,"privacyClass":"PERSONAL"},
    ).to_record()
    with pytest.raises(ValueError, match="parent as itself"):
        default_registry().validate_model(invalid_world)

    log = PLog()
    evidence = log.append("assertion.put", _evidence("edge-evidence"), PERSON, record_time=NOW)
    lifecycle = ModelLifecycle(default_registry())
    models = []
    for color in ("blue", "green"):
        model = _model(evidence.event_id, state={"color": color})
        proposal = lifecycle.propose(log, model, PERSON)
        lifecycle.accept(log, model, PERSON, proposal)
        models.append(model)
    first = ModelEdge.create(models[0].model_id, "DEPENDS_ON", models[1].model_id, (evidence.event_id,))
    second = ModelEdge.create(models[1].model_id, "DEPENDS_ON", models[0].model_id, (evidence.event_id,))
    log.append("model.edge.put", first.to_record(), PERSON, record_time=NOW)
    rejected = log.append("model.edge.put", second.to_record(), PERSON, record_time=NOW)
    state = Materializer().materialize(log)
    assert rejected.event_id in state.unsupported_events
    assert set(state.model_edges) == {first.edge_id}
