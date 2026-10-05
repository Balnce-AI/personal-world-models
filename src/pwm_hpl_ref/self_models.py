from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from .canonical import sha256_urn
from .model_registry import ModelRegistry
from .plog import Event, PLog
from .privacy import DeclassificationBoundary, effective_privacy, validate_boundary_authority
from .schema_validation import validate_record


MODEL_KINDS = frozenset({"SELF", "OTHER", "RELATIONSHIP", "WORLD", "META", "POSSIBLE_WORLD"})
MODEL_STATUSES = frozenset({"PROPOSED", "ACCEPTED", "DISPUTED", "SUPERSEDED", "REVOKED"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ModelRecord:
    model_id: str
    model_kind: str
    family_id: str
    subject_ids: tuple[str, ...]
    perspective: str
    state: dict[str, Any]
    record_time: str
    epistemic_status: str
    lifecycle_status: str
    confidence_ppm: int
    uncertainty: dict[str, Any]
    provenance_refs: tuple[str, ...]
    dependency_refs: tuple[str, ...] = ()
    prediction_refs: tuple[str, ...] = ()
    policy_refs: tuple[str, ...] = ()
    valid_time: dict[str, str | None] | None = None
    freshness: dict[str, Any] | None = None
    calibration: dict[str, Any] | None = None
    lineage: dict[str, Any] | None = None
    privacy_class: str = "PERSONAL"
    effective_privacy_class: str | None = None
    derivation_refs: tuple[str, ...] = ()
    privacy_boundaries: tuple[DeclassificationBoundary, ...] = ()
    schema_version: str = "1.0.0"

    @classmethod
    def create(
        cls,
        *,
        model_kind: str,
        family_id: str,
        subject_ids: tuple[str, ...],
        perspective: str,
        state: dict[str, Any],
        epistemic_status: str,
        confidence_ppm: int,
        uncertainty: dict[str, Any],
        provenance_refs: tuple[str, ...],
        record_time: str | None = None,
        **kwargs: Any,
    ) -> "ModelRecord":
        record_time = record_time or utc_now()
        identity_options = dict(kwargs)
        identity_options.pop("effective_privacy_class", None)
        if "privacy_boundaries" in identity_options:
            identity_options["privacy_boundaries"] = [
                boundary.to_record() for boundary in identity_options["privacy_boundaries"]
            ]
        identity = {
            "modelKind": model_kind,
            "familyId": family_id,
            "subjectIds": list(subject_ids),
            "perspective": perspective,
            "state": state,
            "recordTime": record_time,
            "provenanceRefs": list(provenance_refs),
            "epistemicStatus": epistemic_status,
            "confidencePpm": confidence_ppm,
            "uncertainty": uncertainty,
            "options": identity_options,
        }
        return cls(
            model_id=sha256_urn("pwm:model", identity),
            model_kind=model_kind,
            family_id=family_id,
            subject_ids=subject_ids,
            perspective=perspective,
            state=state,
            record_time=record_time,
            epistemic_status=epistemic_status,
            lifecycle_status="PROPOSED",
            confidence_ppm=confidence_ppm,
            uncertainty=uncertainty,
            provenance_refs=provenance_refs,
            **kwargs,
        )

    def to_record(self) -> dict[str, Any]:
        if self.model_kind not in MODEL_KINDS:
            raise ValueError(f"unsupported model kind: {self.model_kind}")
        if self.lifecycle_status not in MODEL_STATUSES:
            raise ValueError(f"unsupported lifecycle status: {self.lifecycle_status}")
        if len(self.subject_ids) != len(set(self.subject_ids)):
            raise ValueError("model subjects must be distinct")
        if self.model_kind == "RELATIONSHIP" and len(self.subject_ids) < 2:
            raise ValueError("RELATIONSHIP models require at least two distinct subjects")
        if self.model_kind == "OTHER" and self.perspective in self.subject_ids:
            raise ValueError("OTHER model perspective must be distinct from modeled subjects")
        if self.model_kind == "SELF" and self.perspective not in self.subject_ids:
            raise ValueError("SELF model perspective must be one of its subjects")
        if self.model_kind == "POSSIBLE_WORLD":
            missing = {"worldId", "parentWorldId", "baseStateId", "baseTime", "privacyClass"} - self.state.keys()
            if missing:
                raise ValueError(f"POSSIBLE_WORLD model is missing binding fields: {sorted(missing)}")
        if not 0 <= self.confidence_ppm <= 1_000_000:
            raise ValueError("confidence_ppm must be between 0 and 1,000,000")
        record = {
            "modelId": self.model_id,
            "modelKind": self.model_kind,
            "familyId": self.family_id,
            "subjectIds": list(self.subject_ids),
            "perspective": self.perspective,
            "state": self.state,
            "validTime": self.valid_time,
            "recordTime": self.record_time,
            "epistemicStatus": self.epistemic_status,
            "lifecycleStatus": self.lifecycle_status,
            "confidencePpm": self.confidence_ppm,
            "uncertainty": self.uncertainty,
            "provenanceRefs": list(self.provenance_refs),
            "dependencyRefs": list(self.dependency_refs),
            "predictionRefs": list(self.prediction_refs),
            "policyRefs": list(self.policy_refs),
            "freshness": self.freshness,
            "calibration": self.calibration,
            "lineage": self.lineage,
            "privacyClass": self.privacy_class,
            "effectivePrivacyClass": self.effective_privacy_class or self.privacy_class,
            "derivationRefs": list(self.derivation_refs),
            "privacyBoundaries": [boundary.to_record() for boundary in self.privacy_boundaries],
            "schemaVersion": self.schema_version,
        }
        schema = "pwm-meta-model.schema.json" if self.model_kind == "META" else "pwm-self-model.schema.json"
        validate_record(schema, record)
        return record


class ModelLifecycle:
    """Emits candidate and explicitly reviewed events into the V1 reference log."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry

    def _prepare(self, log: PLog, model: ModelRecord) -> ModelRecord:
        accepted: dict[str, dict[str, Any]] = {}
        policies: dict[str, dict[str, Any]] = {}
        edges = []
        for event in log.ordered():
            if event.event_type in {"model.accepted", "model.updated"}:
                accepted[event.payload["modelId"]] = event.payload
            elif event.event_type == "policy.put":
                policies[event.payload["id"]] = event.payload
            elif event.event_type == "model.edge.put":
                edges.append(event.payload)
        record = model.to_record()
        self.registry.validate_model(record, accepted)
        missing_dependencies = set(model.dependency_refs) - accepted.keys()
        missing_derivations = set(model.derivation_refs) - log.events.keys()
        missing_policies = set(model.policy_refs) - policies.keys()
        if missing_dependencies or missing_derivations or missing_policies:
            raise ValueError("model privacy inputs must resolve in the event closure")
        evidence = [log.events[ref].payload for ref in model.provenance_refs if ref in log.events]
        derivations = [log.events[ref].payload for ref in model.derivation_refs if ref in log.events]
        dependencies = [accepted[ref] for ref in model.dependency_refs if ref in accepted]
        dependency_ids = set(model.dependency_refs)
        related_edges = [
            edge for edge in edges
            if model.model_id in {edge["sourceModelId"], edge["targetModelId"]}
            or {edge["sourceModelId"], edge["targetModelId"]}.issubset(dependency_ids)
        ]
        floor_policies = [policies[ref] for ref in model.policy_refs if ref in policies]
        boundary_records = [boundary.to_record() for boundary in model.privacy_boundaries]
        validate_boundary_authority(
            boundary_records,
            source_refs=(*model.provenance_refs, *model.dependency_refs, *model.derivation_refs),
            policies=policies,
        )
        effective, _ = effective_privacy(
            model.privacy_class, evidence=evidence, dependencies=dependencies, edges=related_edges,
            policies=floor_policies, derivations=derivations,
            boundaries=boundary_records,
        )
        return replace(model, effective_privacy_class=effective)

    def propose(self, log: PLog, model: ModelRecord, actor: str) -> Event:
        model = self._prepare(log, model)
        if model.lifecycle_status != "PROPOSED":
            raise ValueError("a proposal must have PROPOSED lifecycle status")
        missing = set(model.provenance_refs) - log.events.keys()
        if missing:
            raise ValueError(f"model proposal has provenance outside the event closure: {sorted(missing)}")
        return log.append("model.proposed", model.to_record(), actor)

    def accept(self, log: PLog, model: ModelRecord, actor: str, proposal: Event) -> Event:
        model = self._prepare(log, model)
        if proposal.event_type != "model.proposed" or proposal.payload != model.to_record():
            raise ValueError("acceptance must reference the matching proposal")
        if actor != model.perspective:
            raise ValueError("reference-profile reviewer must be the modeled perspective")
        review_body = {
            "modelId": model.model_id,
            "proposalEventId": proposal.event_id,
            "decision": "ACCEPT",
            "reviewer": actor,
            "reason": "explicit reference-profile acceptance",
        }
        review_body["reviewId"] = sha256_urn("pwm:model-review", review_body)
        review = log.append("model.reviewed", review_body, actor, parents=(proposal.event_id,))
        accepted = replace(
            model,
            lifecycle_status="ACCEPTED",
            provenance_refs=tuple(sorted(set(model.provenance_refs + (proposal.event_id, review.event_id)))),
        )
        event_type = "model.updated" if accepted.lineage else "model.accepted"
        return log.append(event_type, accepted.to_record(), actor, parents=(review.event_id,))

    def revise(self, log: PLog, previous: ModelRecord, revised: ModelRecord, actor: str) -> Event:
        if previous.lifecycle_status != "ACCEPTED":
            raise ValueError("only an accepted model can be revised")
        proposed = replace(
            revised,
            lineage={"previousModelId": previous.model_id, "operation": "REVISION"},
        )
        proposal = self.propose(log, proposed, actor)
        return self.accept(log, proposed, actor, proposal)

    def transition(self, log: PLog, model_id: str, status: str, actor: str, reason: str) -> Event:
        if status not in {"DISPUTED", "REVOKED"}:
            raise ValueError("transition status must be DISPUTED or REVOKED")
        return log.append(
            f"model.{status.lower()}",
            {"modelId": model_id, "status": status, "reason": reason},
            actor,
        )
