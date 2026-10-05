from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any

from .canonical import sha256_urn
from .pwm import PWMState
from .privacy import most_sensitive
from .schema_validation import validate_record


@dataclass(frozen=True)
class PossibleWorld:
    world_id: str
    label: str
    assumptions: tuple[dict[str, Any], ...]
    provenance_refs: tuple[str, ...]
    parent_world_id: str = "world:actual"
    base_state_id: str | None = None
    base_time: str | None = None
    privacy_class: str = "PERSONAL"
    effective_privacy_class: str | None = None
    schema_version: str = "1.0.0"

    @classmethod
    def create(cls, label: str, assumptions: tuple[dict[str, Any], ...], provenance_refs: tuple[str, ...], **kwargs: Any) -> "PossibleWorld":
        identity = {"label": label, "assumptions": list(assumptions), "provenanceRefs": list(provenance_refs), **kwargs}
        return cls(sha256_urn("pwm:possible-world", identity), label, assumptions, provenance_refs, **kwargs)

    @staticmethod
    def _state_id(state: PWMState) -> str:
        return sha256_urn("pwm:world-base", {
            "worldId": state.world_id, "entities": state.entities, "relations": state.relations,
            "assertions": state.assertions, "policies": state.policies, "models": state.models,
            "modelEdges": state.model_edges, "predictions": state.predictions,
            "predictionOutcomes": state.prediction_outcomes,
            "calibrationRecords": state.calibration_records,
            "contradictions": state.contradictions, "appliedEvents": state.applied_events,
        })

    def _bound_world_id(self) -> str:
        return sha256_urn("pwm:possible-world", {
            "label": self.label, "parentWorldId": self.parent_world_id,
            "baseStateId": self.base_state_id, "baseTime": self.base_time,
            "assumptions": list(self.assumptions), "provenanceRefs": list(self.provenance_refs),
            "privacyClass": self.privacy_class,
            "effectivePrivacyClass": self.effective_privacy_class or self.privacy_class,
        })

    def bind(self, state: PWMState, base_time: str) -> "PossibleWorld":
        if state.world_id != self.parent_world_id:
            raise ValueError("possible-world parent does not match the base state")
        missing = set(self.provenance_refs) - state.applied_event_payloads.keys()
        if missing:
            raise ValueError(f"possible-world provenance is outside the base closure: {sorted(missing)}")
        provenance_privacy = tuple(
            state.applied_event_payloads[ref].get("effectivePrivacyClass", state.applied_event_payloads[ref].get("privacyClass", "PERSONAL"))
            for ref in self.provenance_refs if ref in state.applied_event_payloads
        )
        effective = most_sensitive((
            self.privacy_class,
            *(assumption.get("privacyClass", "PERSONAL") for assumption in self.assumptions),
            *provenance_privacy,
        ))
        base_state_id = self._state_id(state)
        bound = replace(self, base_state_id=base_state_id, base_time=base_time, effective_privacy_class=effective)
        return replace(bound, world_id=bound._bound_world_id())

    def to_record(self) -> dict[str, Any]:
        if not self.base_state_id or not self.base_time:
            raise ValueError("possible world must be bound to a base state and time")
        if self.world_id == self.parent_world_id or self.world_id == "world:actual":
            raise ValueError("possible world must be distinct from its parent and actual world")
        if self.world_id != self._bound_world_id():
            raise ValueError("possible-world identifier does not match its bound content")
        record = {
            "worldId": self.world_id, "label": self.label, "parentWorldId": self.parent_world_id,
            "baseStateId": self.base_state_id, "baseTime": self.base_time,
            "assumptions": list(self.assumptions), "provenanceRefs": list(self.provenance_refs),
            "privacyClass": self.privacy_class,
            "effectivePrivacyClass": self.effective_privacy_class or self.privacy_class,
            "schemaVersion": self.schema_version,
        }
        validate_record("pwm-possible-world.schema.json", record)
        return record

    def branch(self, canonical_state: PWMState) -> PWMState:
        """Return an isolated hypothetical state; the canonical input is never mutated."""
        if canonical_state.world_id != self.parent_world_id:
            raise ValueError("possible-world parent does not match the base state")
        if not self.base_state_id or not self.base_time:
            raise ValueError("possible world must be bound before branching")
        if self.world_id == self.parent_world_id or self.world_id == "world:actual":
            raise ValueError("possible world must be distinct from its parent and actual world")
        if self.world_id != self._bound_world_id():
            raise ValueError("possible-world identifier does not match its bound content")
        if self.base_state_id and self.base_state_id != self._state_id(canonical_state):
            raise ValueError("possible-world base state has changed")
        most_sensitive((self.privacy_class, *(item.get("privacyClass", "PERSONAL") for item in self.assumptions)))
        state = deepcopy(canonical_state)
        state.world_id = self.world_id
        state.parent_world_id = self.parent_world_id
        state.base_state_id = self.base_state_id or self._state_id(canonical_state)
        state.base_time = self.base_time
        for index, assumption in enumerate(self.assumptions):
            assertion = deepcopy(assumption)
            assertion_id = assertion.setdefault("id", f"{self.world_id}:assumption:{index}")
            assertion["epistemicStatus"] = "PREDICTED"
            assertion["possibleWorldId"] = self.world_id
            state.assertions[assertion_id] = assertion
        return state
