from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .plog import PLog
from .schema_validation import validate_record
from .model_registry import ModelRegistry, default_registry
from .privacy import effective_privacy, most_sensitive, validate_boundary_authority
from .topology import validate_topology
from jsonschema.exceptions import ValidationError

@dataclass
class PWMState:
    entities: dict[str, dict[str,Any]] = field(default_factory=dict)
    relations: dict[str, dict[str,Any]] = field(default_factory=dict)
    assertions: dict[str, dict[str,Any]] = field(default_factory=dict)
    policies: dict[str, dict[str,Any]] = field(default_factory=dict)
    model_candidates: dict[str, dict[str,Any]] = field(default_factory=dict)
    model_candidate_events: dict[str, str] = field(default_factory=dict)
    model_reviews: dict[str, dict[str,Any]] = field(default_factory=dict)
    model_review_events: dict[str, str] = field(default_factory=dict)
    models: dict[str, dict[str,Any]] = field(default_factory=dict)
    model_edges: dict[str, dict[str,Any]] = field(default_factory=dict)
    predictions: dict[str, dict[str,Any]] = field(default_factory=dict)
    prediction_outcomes: dict[str, dict[str,Any]] = field(default_factory=dict)
    calibration_records: dict[str, dict[str,Any]] = field(default_factory=dict)
    contradictions: dict[str, dict[str,Any]] = field(default_factory=dict)
    contradiction_candidates: dict[str, dict[str,Any]] = field(default_factory=dict)
    contradiction_candidate_events: dict[str, str] = field(default_factory=dict)
    contradiction_reviews: dict[str, dict[str,Any]] = field(default_factory=dict)
    contradiction_review_events: dict[str, str] = field(default_factory=dict)
    world_id: str = "world:actual"
    parent_world_id: str | None = None
    base_state_id: str | None = None
    base_time: str | None = None
    applied_events: list[str] = field(default_factory=list)
    unsupported_events: list[str] = field(default_factory=list)
    applied_event_types: dict[str, str] = field(default_factory=dict)
    applied_event_payloads: dict[str, dict[str,Any]] = field(default_factory=dict)

class Materializer:
    def __init__(self, registry: ModelRegistry | None = None):
        self.registry = registry or default_registry()

    def _model_privacy(self, state: PWMState, model: dict[str, Any]) -> str:
        evidence_refs = [
            ref for ref in model["provenanceRefs"]
            if ref in state.applied_event_payloads
            and state.applied_event_types.get(ref) in {"assertion.put", "prediction.resolved", "calibration.put", "model.accepted", "model.updated"}
        ]
        evidence = [state.applied_event_payloads[ref] for ref in evidence_refs]
        derivations = [state.applied_event_payloads[ref] for ref in model.get("derivationRefs", []) if ref in state.applied_event_payloads]
        dependencies = [state.models[ref] for ref in model.get("dependencyRefs", []) if ref in state.models]
        policies = {ref: state.policies[ref] for ref in model.get("policyRefs", []) if ref in state.policies}
        if (len(dependencies) != len(model.get("dependencyRefs", []))
            or len(derivations) != len(model.get("derivationRefs", []))
            or len(policies) != len(model.get("policyRefs", []))):
            raise ValueError("model privacy inputs must resolve in the event closure")
        dependency_ids = set(model.get("dependencyRefs", []))
        edges = [
            edge for edge in state.model_edges.values()
            if model["modelId"] in {edge["sourceModelId"], edge["targetModelId"]}
            or {edge["sourceModelId"], edge["targetModelId"]}.issubset(dependency_ids)
        ]
        boundaries = model.get("privacyBoundaries", [])
        validate_boundary_authority(
            boundaries,
            source_refs=(*evidence_refs, *model.get("dependencyRefs", []), *model.get("derivationRefs", [])),
            policies=policies,
        )
        return effective_privacy(
            model["privacyClass"], evidence=evidence, dependencies=dependencies, edges=edges,
            policies=policies.values(), derivations=derivations, boundaries=boundaries,
        )[0]

    def materialize(self, plog:PLog, at_time:str|None=None) -> PWMState:
        state=PWMState()
        for event in plog.ordered(at_time):
            p=event.payload
            applied=True
            if event.event_type == "entity.put":
                try: validate_record("pwm-entity.schema.json",p)
                except (KeyError,TypeError,ValueError,ValidationError): applied=False
                else: state.entities[p["id"]]=dict(p)
            elif event.event_type == "relation.put":
                try: validate_record("pwm-relation.schema.json",p)
                except (KeyError,TypeError,ValueError,ValidationError): applied=False
                else: state.relations[p["id"]]=dict(p)
            elif event.event_type == "assertion.put":
                try: validate_record("pwm-assertion.schema.json",p)
                except (KeyError,TypeError,ValueError,ValidationError): applied=False
                else: state.assertions[p["id"]]=dict(p)
            elif event.event_type == "assertion.revoke" and p["id"] in state.assertions:
                state.assertions[p["id"]]["epistemicStatus"]="REVOKED"
            elif event.event_type == "policy.put": state.policies[p["id"]]=dict(p)
            elif event.event_type == "model.proposed":
                try:
                    schema="pwm-meta-model.schema.json" if p.get("modelKind") == "META" else "pwm-self-model.schema.json"
                    validate_record(schema,p)
                    self.registry.validate_model(p, state.models)
                    expected_privacy = self._model_privacy(state, p)
                except (KeyError, TypeError, ValueError, ValidationError):
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                allowed_evidence={"assertion.put","prediction.resolved","calibration.put","model.accepted","model.updated"}
                if (not p["provenanceRefs"]
                    or any(state.applied_event_types.get(ref) not in allowed_evidence for ref in p["provenanceRefs"])
                    or p["effectivePrivacyClass"] != expected_privacy):
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                state.model_candidates[p["modelId"]]=dict(p)
                state.model_candidate_events[p["modelId"]]=event.event_id
            elif event.event_type == "model.reviewed":
                proposal_ref=state.model_candidate_events.get(p["modelId"])
                candidate=state.model_candidates.get(p["modelId"])
                if candidate is None or p.get("proposalEventId") != proposal_ref or p.get("decision") != "ACCEPT" or event.actor != candidate["perspective"]:
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                state.model_reviews[p["modelId"]]=dict(p)
                state.model_review_events[p["modelId"]]=event.event_id
            elif event.event_type in {"model.accepted", "model.updated"}:
                candidate=state.model_candidates.get(p["modelId"])
                proposal_ref=state.model_candidate_events.get(p["modelId"])
                review=state.model_reviews.get(p["modelId"])
                review_ref=state.model_review_events.get(p["modelId"])
                candidate_body=dict(candidate or {}); candidate_body.pop("lifecycleStatus",None); candidate_body.pop("provenanceRefs",None)
                accepted_body=dict(p); accepted_body.pop("lifecycleStatus",None); accepted_body.pop("provenanceRefs",None)
                expected_refs=set((candidate or {}).get("provenanceRefs",[])) | {proposal_ref, review_ref}
                actual_refs=set(p.get("provenanceRefs",[]))
                previous=(p.get("lineage") or {}).get("previousModelId")
                lifecycle_valid = (
                    p.get("lifecycleStatus") == "ACCEPTED"
                    and ((event.event_type == "model.updated") == bool(previous))
                )
                try:
                    schema="pwm-meta-model.schema.json" if p.get("modelKind") == "META" else "pwm-self-model.schema.json"
                    validate_record(schema,p)
                    self.registry.validate_model(p, state.models)
                    expected_privacy = self._model_privacy(state, p)
                except (KeyError, TypeError, ValueError, ValidationError):
                    expected_privacy = None
                if candidate is None or review is None or not lifecycle_valid or candidate_body != accepted_body or actual_refs != expected_refs or event.actor != p["perspective"] or (previous and previous not in state.models) or p.get("effectivePrivacyClass") != expected_privacy:
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                if previous in state.models:
                    state.models[previous]["lifecycleStatus"]="SUPERSEDED"
                state.models[p["modelId"]]=dict(p)
                state.model_candidates.pop(p["modelId"],None)
                state.model_candidate_events.pop(p["modelId"],None)
                state.model_reviews.pop(p["modelId"],None)
                state.model_review_events.pop(p["modelId"],None)
            elif event.event_type in {"model.disputed", "model.revoked"} and p["modelId"] in state.models:
                expected_status="DISPUTED" if event.event_type == "model.disputed" else "REVOKED"
                if p.get("status") != expected_status:
                    applied=False
                else:
                    state.models[p["modelId"]]["lifecycleStatus"]=expected_status
                    state.models[p["modelId"]]["statusReason"]=p["reason"]
            elif event.event_type == "model.edge.put":
                try:
                    validate_record("pwm-model-edge.schema.json", p)
                    if p["sourceModelId"] not in state.models or p["targetModelId"] not in state.models:
                        raise ValueError("dangling model edge")
                    evidence = [state.applied_event_payloads[ref] for ref in p["provenanceRefs"] if ref in state.applied_event_payloads]
                    effective = most_sensitive((
                        p["privacyClass"], state.models[p["sourceModelId"]]["effectivePrivacyClass"],
                        state.models[p["targetModelId"]]["effectivePrivacyClass"],
                        *(item.get("privacyClass", "PERSONAL") for item in evidence),
                    ))
                except (KeyError, TypeError, ValueError, ValidationError):
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                candidate_edges = {**state.model_edges, p["edgeId"]: {**p, "effectivePrivacyClass": effective}}
                try:
                    validate_topology(state.models, candidate_edges.values())
                except ValueError:
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                state.model_edges[p["edgeId"]]=candidate_edges[p["edgeId"]]
            elif event.event_type == "model.edge.remove": state.model_edges.pop(p["edgeId"],None)
            elif event.event_type == "prediction.put":
                try: validate_record("pwm-prediction.schema.json",p)
                except (KeyError,TypeError,ValueError,ValidationError): applied=False
                else: state.predictions[p["predictionId"]]=dict(p)
            elif event.event_type == "prediction.resolved":
                try:
                    validate_record("pwm-prediction-outcome.schema.json",p)
                    if p["predictionId"] not in state.predictions: raise ValueError("unknown prediction")
                except (KeyError,TypeError,ValueError,ValidationError): applied=False
                else:
                    state.prediction_outcomes[p["predictionId"]]=dict(p)
                    state.predictions[p["predictionId"]]["status"]="RESOLVED"
            elif event.event_type == "calibration.put":
                try:
                    validate_record("pwm-calibration-record.schema.json",p)
                    for pair in p["pairs"]:
                        if pair["predictionId"] not in state.predictions: raise ValueError("unknown prediction")
                        outcome=state.prediction_outcomes.get(pair["predictionId"])
                        if outcome is None or outcome["outcomeId"] != pair["outcomeId"]: raise ValueError("unknown outcome")
                except (KeyError,TypeError,ValueError,ValidationError): applied=False
                else: state.calibration_records[p["calibrationId"]]=dict(p)
            elif event.event_type == "contradiction.proposed":
                try:
                    validate_record("pwm-contradiction.schema.json", p)
                    if p["acceptanceStatus"] != "PROPOSED":
                        raise ValueError("candidate must be proposed")
                    assertion_inputs = [state.assertions[ref] for ref in p["assertionRefs"]]
                    model_inputs = [state.models[ref] for ref in p["modelRefs"]]
                    contradiction_privacy = effective_privacy(
                        p["privacyClass"], evidence=assertion_inputs, dependencies=model_inputs,
                    )[0]
                    if p["effectivePrivacyClass"] != contradiction_privacy:
                        raise ValueError("contradiction effective privacy does not match its inputs")
                except (KeyError, TypeError, ValueError, ValidationError):
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                state.contradiction_candidates[p["contradictionId"]]=dict(p)
                state.contradiction_candidate_events[p["contradictionId"]]=event.event_id
            elif event.event_type == "contradiction.reviewed":
                candidate=state.contradiction_candidates.get(p.get("contradictionId"))
                proposal_ref=state.contradiction_candidate_events.get(p.get("contradictionId"))
                if (candidate is None or p.get("proposalEventId") != proposal_ref
                    or p.get("decision") != "ACCEPT" or event.actor != candidate["subjectId"]):
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                state.contradiction_reviews[p["contradictionId"]]=dict(p)
                state.contradiction_review_events[p["contradictionId"]]=event.event_id
            elif event.event_type == "contradiction.accepted":
                candidate=state.contradiction_candidates.get(p.get("contradictionId"))
                review=state.contradiction_reviews.get(p.get("contradictionId"))
                review_ref=state.contradiction_review_events.get(p.get("contradictionId"))
                candidate_body=dict(candidate or {}); candidate_body["acceptanceStatus"]="ACCEPTED"
                try: validate_record("pwm-contradiction.schema.json", p)
                except (KeyError, TypeError, ValueError, ValidationError): candidate=None
                if (candidate is None or review is None or p != candidate_body
                    or event.actor != p["subjectId"] or event.parents != (review_ref,)):
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                state.contradictions[p["contradictionId"]]=dict(p)
                state.contradiction_candidates.pop(p["contradictionId"],None)
                state.contradiction_reviews.pop(p["contradictionId"],None)
                state.contradiction_review_events.pop(p["contradictionId"],None)
            elif event.event_type == "contradiction.resolved" and p.get("contradictionId") in state.contradictions:
                resolution=p.get("resolution")
                if (not isinstance(resolution,dict)
                    or resolution.get("status") not in {"EXPLAINED","SUPERSEDED","RESOLVED","IRREDUCIBLE","PERSPECTIVE_DEPENDENT"}
                    or resolution.get("resolver") != event.actor
                    or any(ref not in state.applied_events for ref in resolution.get("provenanceRefs", []))):
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                updated = dict(state.contradictions[p["contradictionId"]])
                updated["status"] = resolution["status"]
                updated["resolutions"] = [*updated["resolutions"], dict(resolution)]
                try: validate_record("pwm-contradiction.schema.json", updated)
                except (KeyError, TypeError, ValueError, ValidationError):
                    applied=False
                    state.unsupported_events.append(event.event_id)
                    continue
                state.contradictions[p["contradictionId"]]["status"]=resolution["status"]
                state.contradictions[p["contradictionId"]]["resolutions"].append(dict(resolution))
            else: applied=False
            if applied:
                state.applied_events.append(event.event_id)
                state.applied_event_types[event.event_id]=event.event_type
                state.applied_event_payloads[event.event_id]=dict(p)
            elif event.event_id not in state.unsupported_events: state.unsupported_events.append(event.event_id)
        return state
