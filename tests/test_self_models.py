from dataclasses import replace

import pytest

from pwm_hpl_ref.calibration import binary_calibration_record
from pwm_hpl_ref.contradiction import ContradictionLifecycle, ResolutionRecord, detect_simple_contradictions
from pwm_hpl_ref.meta_models import model_quality_candidate
from pwm_hpl_ref.model_derivation import derive_numeric_capability
from pwm_hpl_ref.model_query import ModelQuery, ModelQueryAuthorization, execute_query
from pwm_hpl_ref.model_registry import default_registry
from pwm_hpl_ref.plog import PLog
from pwm_hpl_ref.possible_worlds import PossibleWorld
from pwm_hpl_ref.prediction import Prediction, resolve_prediction
from pwm_hpl_ref.pwm import Materializer
from pwm_hpl_ref.self_models import ModelLifecycle, ModelRecord
from pwm_hpl_ref.schema_validation import validate_record
from pwm_hpl_ref.topology import ModelEdge, model_topography, validate_topology


NOW = "2026-10-01T12:00:00+00:00"
LATER = "2026-10-02T12:00:00+00:00"
PERSON = "person:self"


def authorization(privacy="PERSONAL"):
    return ModelQueryAuthorization(
        "authority:test", "research", "local:researcher", privacy, (PERSON,), "world:actual",
        "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00", NOW,
    )


def accepted_model(log, lifecycle, model):
    if not set(model.provenance_refs).issubset(log.events):
        evidence_events = []
        for index, source_ref in enumerate(model.provenance_refs):
            evidence_events.append(log.append(
                "assertion.put",
                {"id": f"test-evidence:{index}:{source_ref}", "subject": PERSON, "predicate": "test.evidence", "object": source_ref, "recordTime": NOW, "epistemicStatus": "OBSERVED"},
                PERSON,
                record_time=NOW,
            ).event_id)
        model = replace(model, provenance_refs=tuple(evidence_events))
    proposal = lifecycle.propose(log, model, PERSON)
    lifecycle.accept(log, model, PERSON, proposal)
    return replace(model, lifecycle_status="ACCEPTED", provenance_refs=model.provenance_refs + (proposal.event_id,))


def test_proposal_does_not_mutate_accepted_state_and_acceptance_retains_provenance():
    log = PLog()
    lifecycle = ModelLifecycle(default_registry())
    evidence = log.append("assertion.put", {"id":"meal-evidence","subject":PERSON,"predicate":"meal","object":"vegetarian","recordTime":NOW,"epistemicStatus":"ASSERTED"}, PERSON, record_time=NOW)
    model = ModelRecord.create(
        model_kind="SELF",
        family_id="pwm.preference",
        subject_ids=(PERSON,),
        perspective=PERSON,
        state={"meal": "vegetarian"},
        epistemic_status="INFERRED",
        confidence_ppm=700_000,
        uncertainty={"kind": "sparse-evidence"},
        provenance_refs=(evidence.event_id,),
        record_time=NOW,
    )
    proposal = lifecycle.propose(log, model, "model:external")
    proposed_state = Materializer().materialize(log)
    assert model.model_id in proposed_state.model_candidates
    assert model.model_id not in proposed_state.models

    lifecycle.accept(log, model, PERSON, proposal)
    accepted_state = Materializer().materialize(log)
    assert accepted_state.models[model.model_id]["lifecycleStatus"] == "ACCEPTED"
    assert proposal.event_id in accepted_state.models[model.model_id]["provenanceRefs"]


def test_deterministic_derivation_keeps_assertions_distinct_from_model():
    assertions = [
        {"id": "run-1", "subject": PERSON, "predicate": "exercise.run_miles", "object": 3, "epistemicStatus": "OBSERVED"},
        {"id": "run-2", "subject": PERSON, "predicate": "exercise.run_miles", "object": 5, "epistemicStatus": "OBSERVED"},
    ]
    result = derive_numeric_capability(
        assertions,
        subject_id=PERSON,
        evidence_predicate="exercise.run_miles",
        family_id="fc.action-capability",
        output_key="ordinaryRunMiles",
        record_time=NOW,
    )
    assert result.model.state["ordinaryRunMiles"] == {"lower": 3, "upper": 5}
    assert result.model.lifecycle_status == "PROPOSED"
    assert result.record["evidenceRefs"] == ["run-1", "run-2"]


def test_temporal_private_query_is_deterministic_and_excludes_disputed_models():
    log = PLog()
    lifecycle = ModelLifecycle(default_registry())
    current = ModelRecord.create(
        model_kind="SELF", family_id="pwm.professional-work", subject_ids=(PERSON,), perspective=PERSON,
        state={"role": "researcher"}, epistemic_status="ASSERTED", confidence_ppm=1_000_000,
        uncertainty={}, provenance_refs=("assertion:role",), record_time=NOW,
        valid_time={"start": NOW, "end": None},
    )
    accepted_model(log, lifecycle, current)
    disputed = ModelRecord.create(
        model_kind="SELF", family_id="pwm.preference", subject_ids=(PERSON,), perspective=PERSON,
        state={"travel": "frequent"}, epistemic_status="INFERRED", confidence_ppm=600_000,
        uncertainty={}, provenance_refs=("assertion:travel",), record_time=NOW,
    )
    disputed_accepted = accepted_model(log, lifecycle, disputed)
    lifecycle.transition(log, disputed_accepted.model_id, "DISPUTED", PERSON, "contradictory recent evidence")
    state = Materializer().materialize(log)
    query = ModelQuery((PERSON,), valid_at=LATER, min_confidence_ppm=500_000)
    first = execute_query(state, query, authorization())
    second = execute_query(state, query, authorization())
    assert first == second
    assert [item["familyId"] for item in first["models"]] == ["pwm.professional-work"]
    validate_record("pwm-self-model.schema.json", state.models[disputed.model_id])


def test_meta_model_and_acyclic_topology_are_queryable():
    log = PLog()
    lifecycle = ModelLifecycle(default_registry())
    capability = ModelRecord.create(
        model_kind="SELF", family_id="fc.action-capability", subject_ids=(PERSON,), perspective=PERSON,
        state={"rangeMiles": 4}, epistemic_status="INFERRED", confidence_ppm=600_000,
        uncertainty={"kind": "sparse"}, provenance_refs=("run-1",), record_time=NOW,
    )
    capability = accepted_model(log, lifecycle, capability)
    meta = model_quality_candidate(
        subject_id=PERSON, target_model_id=capability.model_id, quality_kind="STALE_KNOWLEDGE",
        assessment={"stale": True}, confidence_ppm=800_000, provenance_refs=("clock:1",), record_time=NOW,
    )
    meta = accepted_model(log, lifecycle, meta)
    edge = ModelEdge.create(meta.model_id, "UNCERTAINTY_SOURCE", capability.model_id, ("review:1",))
    log.append("model.edge.put", edge.to_record(), PERSON)
    state = Materializer().materialize(log)
    validate_topology(state.models, state.model_edges.values())
    projection = execute_query(state, ModelQuery((PERSON,), include_topology=True), authorization())
    assert len(projection["edges"]) == 1
    assert model_topography(state.models.values(), state.model_edges.values(), "action-capability")["modelCount"] == 1


def test_dependency_cycles_are_rejected():
    models = {"a": {}, "b": {}}
    edges = [
        {"edgeId": "ab", "sourceModelId": "a", "edgeType": "DEPENDS_ON", "targetModelId": "b"},
        {"edgeId": "ba", "sourceModelId": "b", "edgeType": "DEPENDS_ON", "targetModelId": "a"},
    ]
    with pytest.raises(ValueError, match="cycle"):
        validate_topology(models, edges)


def test_prediction_resolution_and_calibration_preserve_history():
    prediction = Prediction.create(
        subject_id=PERSON,
        predicate="schedule.arrives_on_time",
        predicted_value=True,
        probability_ppm=800_000,
        target_time=LATER,
        record_time=NOW,
        model_refs=("model:schedule",),
        provenance_refs=("assertion:calendar",),
    ).to_record()
    outcome = resolve_prediction(prediction, False, LATER, ("observation:arrival",))
    calibration = binary_calibration_record([prediction], {prediction["predictionId"]: outcome}, evaluated_at=LATER)
    assert prediction["status"] == "OPEN"
    assert outcome["observedValue"] is False
    assert calibration["metricValuePpm"] == 640_000
    assert calibration["sampleCount"] == 1


def test_unknown_events_are_not_reported_as_applied():
    log = PLog()
    event = log.append("model.typo", {"modelId": "x"}, PERSON, record_time=NOW)
    state = Materializer().materialize(log)
    assert event.event_id in state.unsupported_events
    assert event.event_id not in state.applied_events


def test_schema_invalid_prediction_is_not_materialized():
    log = PLog()
    event = log.append("prediction.put", {"predictionId": "invalid"}, PERSON, record_time=NOW)
    state = Materializer().materialize(log)
    assert state.predictions == {}
    assert event.event_id in state.unsupported_events


def test_revision_preserves_queryable_lineage_and_supersedes_prior_model():
    log = PLog()
    lifecycle = ModelLifecycle(default_registry())
    original = ModelRecord.create(
        model_kind="SELF", family_id="pwm.identity-persona", subject_ids=(PERSON,), perspective=PERSON,
        state={"role": "designer"}, epistemic_status="ASSERTED", confidence_ppm=1_000_000,
        uncertainty={}, provenance_refs=("declaration:2018",), record_time=NOW,
    )
    original = accepted_model(log, lifecycle, original)
    revised = ModelRecord.create(
        model_kind="SELF", family_id="pwm.identity-persona", subject_ids=(PERSON,), perspective=PERSON,
        state={"role": "researcher"}, epistemic_status="ASSERTED", confidence_ppm=1_000_000,
        uncertainty={}, provenance_refs=("declaration:2026",), record_time=LATER,
    )
    revision_evidence = log.append("assertion.put", {"id":"role-2026","subject":PERSON,"predicate":"role","object":"researcher","recordTime":LATER,"epistemicStatus":"ASSERTED"}, PERSON, record_time=LATER)
    revised = replace(revised, provenance_refs=(revision_evidence.event_id,))
    lifecycle.revise(log, original, revised, PERSON)
    state = Materializer().materialize(log)
    assert state.models[original.model_id]["lifecycleStatus"] == "SUPERSEDED"
    assert state.models[revised.model_id]["lineage"]["previousModelId"] == original.model_id
    projection = execute_query(state, ModelQuery((PERSON,), model_families=("pwm.identity-persona",)), authorization())
    assert [model["state"]["role"] for model in projection["models"]] == ["researcher"]


def test_contradiction_events_preserve_then_resolve_the_record():
    log = PLog()
    assertions = [
        {"id": "assertion:a", "subject": PERSON, "predicate": "role", "object": "designer", "recordTime": NOW, "epistemicStatus": "ASSERTED", "privacyClass": "PERSONAL"},
        {"id": "assertion:b", "subject": PERSON, "predicate": "role", "object": "researcher", "recordTime": NOW, "epistemicStatus": "ASSERTED", "privacyClass": "PERSONAL"},
    ]
    evidence_events = [log.append("assertion.put", assertion, PERSON, record_time=NOW) for assertion in assertions]
    detected = detect_simple_contradictions(assertions, NOW)[0]
    lifecycle = ContradictionLifecycle()
    proposal = lifecycle.propose(log, detected, PERSON)
    lifecycle.accept(log, detected, PERSON, proposal)
    lifecycle.resolve(
        log, detected.contradiction_id,
        ResolutionRecord("RESOLVED", "new evidence", PERSON, LATER, (evidence_events[1].event_id,)), PERSON,
    )
    state = Materializer().materialize(log)
    assert state.contradictions[detected.contradiction_id]["status"] == "RESOLVED"
    assert state.contradictions[detected.contradiction_id]["provenanceRefs"] == ["assertion:a", "assertion:b"]
    assert state.contradictions[detected.contradiction_id]["resolutions"][0]["explanation"] == "new evidence"


def test_possible_world_branch_does_not_mutate_canonical_state():
    log = PLog()
    evidence = log.append("assertion.put", {"id":"prediction:train","subject":PERSON,"predicate":"train.prediction","object":"late","recordTime":NOW,"epistemicStatus":"PREDICTED","privacyClass":"PERSONAL"}, PERSON, record_time=NOW)
    canonical = Materializer().materialize(log)
    world = PossibleWorld.create(
        "missed train",
        ({"subject": PERSON, "predicate": "arrival.delayMinutes", "object": 30},),
        (evidence.event_id,),
    ).bind(canonical, NOW)
    branch = world.branch(canonical)
    assert set(canonical.assertions) == {"prediction:train"}
    assert len(branch.assertions) == 2
    hypothetical = next(item for item in branch.assertions.values() if item.get("possibleWorldId"))
    assert hypothetical["epistemicStatus"] == "PREDICTED"


def test_prediction_and_calibration_events_materialize_without_overwriting_forecast():
    log = PLog()
    prediction = Prediction.create(
        subject_id=PERSON, predicate="event.happens", predicted_value=True, probability_ppm=700_000,
        target_time=LATER, record_time=NOW, model_refs=(), provenance_refs=("evidence:1",),
    ).to_record()
    outcome = resolve_prediction(prediction, True, LATER, ("observation:1",))
    calibration = binary_calibration_record([prediction], {prediction["predictionId"]: outcome}, evaluated_at=LATER)
    log.append("prediction.put", prediction, PERSON, record_time=NOW)
    log.append("prediction.resolved", outcome, PERSON, record_time=LATER)
    log.append("calibration.put", calibration, PERSON, record_time=LATER)
    state = Materializer().materialize(log)
    assert state.predictions[prediction["predictionId"]]["probabilityPpm"] == 700_000
    assert state.predictions[prediction["predictionId"]]["status"] == "RESOLVED"
    assert calibration["calibrationId"] in state.calibration_records


def test_default_registry_is_machine_validated_and_open_to_extensions():
    registry = default_registry()
    record = registry.to_record()
    assert len(record["families"]) == 34
    assert record["ontologyVersion"].endswith("experimental")


def test_direct_acceptance_without_matching_proposal_is_rejected():
    log = PLog()
    model = ModelRecord.create(
        model_kind="SELF", family_id="pwm.preference", subject_ids=(PERSON,), perspective=PERSON,
        state={"color": "blue"}, epistemic_status="ASSERTED", confidence_ppm=900_000,
        uncertainty={}, provenance_refs=("evidence:1",), record_time=NOW,
    )
    forged = replace(model, lifecycle_status="ACCEPTED").to_record()
    event = log.append("model.accepted", forged, PERSON, record_time=NOW)
    state = Materializer().materialize(log)
    assert model.model_id not in state.models
    assert event.event_id in state.unsupported_events


def test_transition_event_cannot_restore_or_mislabel_model_state():
    log = PLog()
    lifecycle = ModelLifecycle(default_registry())
    accepted = accepted_model(log, lifecycle, ModelRecord.create(
        model_kind="SELF", family_id="pwm.preference", subject_ids=(PERSON,), perspective=PERSON,
        state={"color":"blue"}, epistemic_status="ASSERTED", confidence_ppm=900_000,
        uncertainty={}, provenance_refs=("source:color",), record_time=NOW,
    ))
    event = log.append(
        "model.revoked", {"modelId": accepted.model_id, "status": "ACCEPTED", "reason": "forged"},
        PERSON, record_time=LATER,
    )
    state = Materializer().materialize(log)
    assert state.models[accepted.model_id]["lifecycleStatus"] == "ACCEPTED"
    assert event.event_id in state.unsupported_events


def test_query_projection_is_isolated_and_filters_private_edges():
    log = PLog()
    lifecycle = ModelLifecycle(default_registry())
    first = accepted_model(log, lifecycle, ModelRecord.create(
        model_kind="SELF", family_id="pwm.preference", subject_ids=(PERSON,), perspective=PERSON,
        state={"color": "blue"}, epistemic_status="ASSERTED", confidence_ppm=900_000,
        uncertainty={}, provenance_refs=("evidence:1",), record_time=NOW,
    ))
    second = accepted_model(log, lifecycle, ModelRecord.create(
        model_kind="SELF", family_id="fc.goals", subject_ids=(PERSON,), perspective=PERSON,
        state={"goal": "paint"}, epistemic_status="ASSERTED", confidence_ppm=900_000,
        uncertainty={}, provenance_refs=("evidence:2",), record_time=NOW,
    ))
    edge = ModelEdge.create(first.model_id, "INFORMED_BY", second.model_id, ("evidence:3",), privacy_class="HIGHLY_SENSITIVE")
    log.append("model.edge.put", edge.to_record(), PERSON, record_time=NOW)
    state = Materializer().materialize(log)
    projection = execute_query(state, ModelQuery((PERSON,), max_privacy_class="PERSONAL"), authorization())
    assert projection["edges"] == []
    projected_preference = next(model for model in projection["models"] if model["familyId"] == "pwm.preference")
    projected_preference["state"]["color"] = "red"
    assert state.models[first.model_id]["state"]["color"] == "blue"


def test_material_identifiers_change_with_uncertainty_and_prediction_value():
    base = dict(
        model_kind="SELF", family_id="pwm.preference", subject_ids=(PERSON,), perspective=PERSON,
        state={"color": "blue"}, epistemic_status="INFERRED", confidence_ppm=800_000,
        provenance_refs=("evidence:1",), record_time=NOW,
    )
    first = ModelRecord.create(**base, uncertainty={"kind": "low"})
    second = ModelRecord.create(**base, uncertainty={"kind": "high"})
    assert first.model_id != second.model_id
    prediction = dict(
        subject_id=PERSON, predicate="event.happens", probability_ppm=700_000,
        target_time=LATER, record_time=NOW, model_refs=(), provenance_refs=("evidence:1",),
    )
    assert Prediction.create(**prediction, predicted_value=True).prediction_id != Prediction.create(**prediction, predicted_value=False).prediction_id


def test_query_requires_matching_authorization_binding():
    query = ModelQuery((PERSON,), purpose="planning", recipient="provider:a")
    wrong = ModelQueryAuthorization(
        "authority:1", "planning", "provider:b", "PERSONAL", (PERSON,), "world:actual",
        "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00", NOW,
    )
    with pytest.raises(ValueError, match="not bound"):
        execute_query(Materializer().materialize(PLog()), query, wrong)


def test_empty_family_query_is_restricted_by_authorization():
    log = PLog()
    lifecycle = ModelLifecycle(default_registry())
    accepted_model(log, lifecycle, ModelRecord.create(
        model_kind="SELF", family_id="pwm.preference", subject_ids=(PERSON,), perspective=PERSON,
        state={"color":"blue"}, epistemic_status="ASSERTED", confidence_ppm=900_000,
        uncertainty={}, provenance_refs=("source:preference",), record_time=NOW,
    ))
    accepted_model(log, lifecycle, ModelRecord.create(
        model_kind="SELF", family_id="fc.goals", subject_ids=(PERSON,), perspective=PERSON,
        state={"goal":"paint"}, epistemic_status="ASSERTED", confidence_ppm=900_000,
        uncertainty={}, provenance_refs=("source:goal",), record_time=NOW,
    ))
    state = Materializer().materialize(log)
    grant = ModelQueryAuthorization(
        "authority:family", "research", "local:researcher", "PERSONAL", (PERSON,), "world:actual",
        "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00", NOW,
        ("pwm.preference",),
    )
    projection = execute_query(state, ModelQuery((PERSON,)), grant)
    assert [model["familyId"] for model in projection["models"]] == ["pwm.preference"]


def test_revision_with_missing_predecessor_is_rejected_during_materialization():
    log = PLog()
    lifecycle = ModelLifecycle(default_registry())
    missing = ModelRecord.create(
        model_kind="SELF", family_id="pwm.identity-persona", subject_ids=(PERSON,), perspective=PERSON,
        state={"role": "missing"}, epistemic_status="ASSERTED", confidence_ppm=1_000_000,
        uncertainty={}, provenance_refs=("evidence:missing",), record_time=NOW,
    )
    revised = ModelRecord.create(
        model_kind="SELF", family_id="pwm.identity-persona", subject_ids=(PERSON,), perspective=PERSON,
        state={"role": "new"}, epistemic_status="ASSERTED", confidence_ppm=1_000_000,
        uncertainty={}, provenance_refs=("evidence:new",), record_time=LATER,
    )
    evidence = log.append("assertion.put", {"id":"revision-evidence","subject":PERSON,"predicate":"role","object":"new","recordTime":LATER,"epistemicStatus":"ASSERTED"}, PERSON, record_time=LATER)
    revised = replace(revised, provenance_refs=(evidence.event_id,))
    event = lifecycle.revise(log, replace(missing, lifecycle_status="ACCEPTED"), revised, PERSON)
    state = Materializer().materialize(log)
    assert revised.model_id not in state.models
    assert event.event_id in state.unsupported_events
