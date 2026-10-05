from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

from .canonical import canonical_json, sha256_urn
from .plog import Event, PLog
from .privacy import effective_privacy
from .schema_validation import validate_record


CONFLICT_TYPES = frozenset({
    "ASSERTION_CONFLICT", "MODEL_CONFLICT", "UNCERTAINTY", "TEMPORAL_CHANGE",
    "PERSPECTIVE_DISAGREEMENT", "GENUINE_CONTRADICTION",
})
CONTRADICTION_STATUSES = frozenset({
    "OPEN", "EXPLAINED", "SUPERSEDED", "RESOLVED", "IRREDUCIBLE", "PERSPECTIVE_DEPENDENT",
})


@dataclass(frozen=True)
class ResolutionRecord:
    status: str
    explanation: str
    resolver: str
    record_time: str
    provenance_refs: tuple[str, ...]

    def to_record(self) -> dict[str, Any]:
        if self.status not in CONTRADICTION_STATUSES - {"OPEN"}:
            raise ValueError(f"invalid contradiction resolution status: {self.status}")
        return {
            "status": self.status, "explanation": self.explanation, "resolver": self.resolver,
            "recordTime": self.record_time, "provenanceRefs": list(self.provenance_refs),
        }


@dataclass(frozen=True)
class ContradictionRecord:
    contradiction_id: str
    conflict_type: str
    subject_id: str
    predicate: str
    valid_time: str | None
    incompatible_values: tuple[Any, ...]
    assertion_refs: tuple[str, ...]
    model_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    record_time: str
    status: str = "OPEN"
    acceptance_status: str = "PROPOSED"
    detection_method: str = "DETERMINISTIC"
    resolutions: tuple[ResolutionRecord, ...] = ()
    privacy_class: str = "PERSONAL"
    effective_privacy_class: str | None = None
    schema_version: str = "1.0.0"

    @classmethod
    def create(cls, **kwargs: Any) -> "ContradictionRecord":
        identity = {key: value for key, value in kwargs.items() if key not in {"acceptance_status", "resolutions"}}
        return cls(contradiction_id=sha256_urn("pwm:contradiction", identity), **kwargs)

    def to_record(self) -> dict[str, Any]:
        record = {
            "contradictionId": self.contradiction_id, "conflictType": self.conflict_type,
            "subjectId": self.subject_id, "predicate": self.predicate, "validTime": self.valid_time,
            "incompatibleValues": list(self.incompatible_values), "assertionRefs": list(self.assertion_refs),
            "modelRefs": list(self.model_refs), "provenanceRefs": list(self.provenance_refs),
            "recordTime": self.record_time, "status": self.status,
            "acceptanceStatus": self.acceptance_status, "detectionMethod": self.detection_method,
            "resolutions": [resolution.to_record() for resolution in self.resolutions],
            "privacyClass": self.privacy_class,
            "effectivePrivacyClass": self.effective_privacy_class or self.privacy_class,
            "schemaVersion": self.schema_version,
        }
        validate_record("pwm-contradiction.schema.json", record)
        return record


def detect_simple_contradictions(assertions: Iterable[dict[str, Any]], record_time: str) -> list[ContradictionRecord]:
    groups: dict[tuple[str, str, str | None], list[dict[str, Any]]] = {}
    for assertion in assertions:
        if assertion.get("epistemicStatus") in {"REVOKED", "SUPERSEDED"}:
            continue
        valid_time = assertion.get("validTime", assertion.get("recordTime"))
        if not isinstance(valid_time, (str, type(None))):
            valid_time = canonical_json(valid_time).decode("utf-8")
        key = (assertion["subject"], assertion["predicate"], valid_time)
        groups.setdefault(key, []).append(assertion)
    found = []
    for (subject, predicate, valid_time), candidates in sorted(groups.items()):
        candidates.sort(key=lambda item: item["id"])
        values = {repr(item.get("object")) for item in candidates}
        if len(values) < 2:
            continue
        refs = tuple(sorted(item["id"] for item in candidates))
        privacy = max((item.get("privacyClass", "PERSONAL") for item in candidates),
                      key=lambda value: ("PUBLIC", "LOW", "PERSONAL", "SENSITIVE", "HIGHLY_SENSITIVE").index(value))
        found.append(ContradictionRecord.create(
            conflict_type="ASSERTION_CONFLICT", subject_id=subject, predicate=predicate,
            valid_time=valid_time, incompatible_values=tuple(item.get("object") for item in candidates),
            assertion_refs=refs, model_refs=(), provenance_refs=refs, record_time=record_time,
            privacy_class=privacy,
        ))
    return found


class ContradictionLifecycle:
    def _prepare(self, log: PLog, contradiction: ContradictionRecord) -> ContradictionRecord:
        assertions = {
            event.payload.get("id"): event.payload for event in log.events.values()
            if event.event_type == "assertion.put"
        }
        models = {
            event.payload.get("modelId"): event.payload for event in log.events.values()
            if event.event_type in {"model.accepted", "model.updated"}
        }
        if (not set(contradiction.assertion_refs).issubset(assertions)
            or not set(contradiction.model_refs).issubset(models)):
            raise ValueError("contradiction references must resolve in the event closure")
        assertion_inputs = [assertions[ref] for ref in contradiction.assertion_refs]
        model_inputs = [models[ref] for ref in contradiction.model_refs]
        if any(item.get("subject") != contradiction.subject_id for item in assertion_inputs):
            raise ValueError("contradiction assertions must match the represented subject")
        if any(
            contradiction.subject_id not in item.get("subjectIds", ()) for item in model_inputs
        ):
            raise ValueError("contradiction models must include the represented subject")
        if contradiction.conflict_type in {"ASSERTION_CONFLICT", "GENUINE_CONTRADICTION", "TEMPORAL_CHANGE"}:
            if any(item.get("predicate") != contradiction.predicate for item in assertion_inputs):
                raise ValueError("contradiction assertions must match the represented predicate")
            observed_values = {canonical_json(item.get("object")) for item in assertion_inputs}
            declared_values = {canonical_json(value) for value in contradiction.incompatible_values}
            if assertion_inputs and observed_values != declared_values:
                raise ValueError("contradiction values must match referenced assertions")
        effective = effective_privacy(
            contradiction.privacy_class,
            evidence=assertion_inputs,
            dependencies=model_inputs,
        )[0]
        return replace(contradiction, effective_privacy_class=effective)

    def propose(self, log: PLog, contradiction: ContradictionRecord, actor: str) -> Event:
        if contradiction.acceptance_status != "PROPOSED":
            raise ValueError("contradiction proposal must be PROPOSED")
        contradiction = self._prepare(log, contradiction)
        return log.append("contradiction.proposed", contradiction.to_record(), actor)

    def accept(self, log: PLog, contradiction: ContradictionRecord, actor: str, proposal: Event) -> Event:
        contradiction = self._prepare(log, contradiction)
        if proposal.event_type != "contradiction.proposed" or proposal.payload != contradiction.to_record():
            raise ValueError("acceptance must reference the matching contradiction proposal")
        if actor != contradiction.subject_id:
            raise ValueError("reference-profile contradiction reviewer must be the contradiction subject")
        review_body = {
            "contradictionId": contradiction.contradiction_id,
            "proposalEventId": proposal.event_id,
            "decision": "ACCEPT",
            "reviewer": actor,
        }
        review_body["reviewId"] = sha256_urn("pwm:contradiction-review", review_body)
        review = log.append("contradiction.reviewed", review_body, actor, parents=(proposal.event_id,))
        accepted = replace(contradiction, acceptance_status="ACCEPTED")
        return log.append("contradiction.accepted", accepted.to_record(), actor, parents=(review.event_id,))

    def resolve(self, log: PLog, contradiction_id: str, resolution: ResolutionRecord, actor: str) -> Event:
        if not any(
            event.event_type == "contradiction.accepted" and event.payload.get("contradictionId") == contradiction_id
            for event in log.events.values()
        ):
            raise ValueError("only an accepted contradiction can be resolved")
        if actor != resolution.resolver:
            raise ValueError("resolution actor must match its resolver")
        if not set(resolution.provenance_refs).issubset(log.events):
            raise ValueError("resolution provenance must exist in the event closure")
        return log.append("contradiction.resolved", {
            "contradictionId": contradiction_id, "resolution": resolution.to_record()
        }, actor)
