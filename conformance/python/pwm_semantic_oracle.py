#!/usr/bin/env python3
"""Independent semantic oracle over cryptographically verified Wave01 records.

The only non-stdlib module imported here is the sibling byte-level Wave01
verifier; semantic behavior is implemented locally.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol

import pwm_oracle


PROFILE = "pwm-signed-semantics-v1"
SCHEMA_VERSION = "1.0.0"
IMPLEMENTATION = "pwm-semantic-oracle-python"
PRIVACY = ("PUBLIC", "LOW", "PERSONAL", "SENSITIVE", "HIGHLY_SENSITIVE")
KINDS = frozenset({"SELF", "OTHER", "RELATIONSHIP", "WORLD", "META", "POSSIBLE_WORLD"})
CURRENT = frozenset({"ACCEPTED", "DISPUTED"})


class SemanticError(ValueError):
    """A deterministic semantic rejection."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


class VerifiedRecordSource(Protocol):
    """Boundary which guarantees records were authenticated before exposure."""

    def records(self) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class Wave01Source:
    path: Path

    def records(self) -> list[dict[str, Any]]:
        return pwm_oracle.verify_bundle_records(self.path)


@dataclass(frozen=True)
class FixtureSource:
    """Explicit test adapter; never represents cryptographic verification."""

    events: tuple[dict[str, Any], ...]

    def records(self) -> list[dict[str, Any]]:
        return [{"semantic_event": copy.deepcopy(event)} for event in self.events]


DEFAULT_FAMILIES: dict[str, dict[str, Any]] = {
    "pwm.preference": {"allowedKinds": ["SELF", "OTHER"], "minSubjects": 1, "maxSubjects": None},
    "pwm.relationship": {"allowedKinds": ["RELATIONSHIP"], "minSubjects": 2, "maxSubjects": None},
    "pwm.physical-environment": {"allowedKinds": ["WORLD"], "minSubjects": 1, "maxSubjects": None},
    "pwm.imagination-possible-worlds": {"allowedKinds": ["POSSIBLE_WORLD"], "minSubjects": 1, "maxSubjects": None},
    "pwm.models-of-models": {"allowedKinds": ["META"], "minSubjects": 1, "maxSubjects": None},
    "fc.meta": {"allowedKinds": ["META"], "minSubjects": 1, "maxSubjects": None},
}


@dataclass
class State:
    accepted_event_ids: list[str] = field(default_factory=list)
    event_types: dict[str, str] = field(default_factory=dict)
    principals: dict[str, dict[str, Any]] = field(default_factory=dict)
    families: dict[str, dict[str, Any]] = field(default_factory=dict)
    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    policies: dict[str, dict[str, Any]] = field(default_factory=dict)
    privacy_boundaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    candidates: dict[str, dict[str, Any]] = field(default_factory=dict)
    proposal_events: dict[str, str] = field(default_factory=dict)
    reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    review_events: dict[str, str] = field(default_factory=dict)
    models: dict[str, dict[str, Any]] = field(default_factory=dict)
    derived_models: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[str, dict[str, Any]] = field(default_factory=dict)
    worlds: dict[str, dict[str, Any]] = field(default_factory=dict)
    contradiction_candidates: dict[str, dict[str, Any]] = field(default_factory=dict)
    contradiction_proposals: dict[str, str] = field(default_factory=dict)
    contradiction_reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    contradiction_review_events: dict[str, str] = field(default_factory=dict)
    contradictions: dict[str, dict[str, Any]] = field(default_factory=dict)
    predictions: dict[str, dict[str, Any]] = field(default_factory=dict)
    calibrations: dict[str, dict[str, Any]] = field(default_factory=dict)
    query_authorities: dict[str, dict[str, Any]] = field(default_factory=dict)
    projections: dict[str, dict[str, Any]] = field(default_factory=dict)
    projection_revocations: dict[str, dict[str, Any]] = field(default_factory=dict)
    hpl_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    hpl_authorizations: dict[str, dict[str, Any]] = field(default_factory=dict)
    evaluations: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_query: dict[str, Any] | None = None


def _text(value: Any, code: str) -> str:
    if type(value) is not str or not value:
        raise SemanticError(code)
    return value


def _list(value: Any, code: str) -> list[Any]:
    if type(value) is not list:
        raise SemanticError(code)
    return value


def _required(data: dict[str, Any], names: Iterable[str], code: str = "MALFORMED_PAYLOAD") -> None:
    if type(data) is not dict or any(name not in data for name in names):
        raise SemanticError(code)


def _exact(data: Any, names: Iterable[str]) -> dict[str, Any]:
    fields = set(names)
    if type(data) is not dict or set(data) != fields:
        raise SemanticError("PAYLOAD_FIELD_INVALID")
    return data


def _time(value: Any, code: str = "INVALID_TIME") -> datetime:
    if type(value) is int:
        return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc)
    if type(value) is not str:
        raise SemanticError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed
    except ValueError as error:
        raise SemanticError(code) from error


def _rank(value: Any) -> int:
    try:
        return PRIVACY.index(value)
    except ValueError as error:
        raise SemanticError("UNKNOWN_PRIVACY_CLASS") from error


def _join(values: Iterable[str]) -> str:
    return PRIVACY[max((_rank(value) for value in values), default=2)]


def _unique_texts(value: Any, code: str = "MALFORMED_PAYLOAD") -> list[str]:
    items = _list(value, code)
    if any(type(item) is not str or not item for item in items) or len(items) != len(set(items)):
        raise SemanticError(code)
    return items


def _canonical_set(value: Any) -> list[Any]:
    items = _list(value, "PAYLOAD_FIELD_INVALID")
    encoded = [pwm_oracle.encode(item) for item in items]
    if encoded != sorted(encoded) or len(encoded) != len(set(encoded)):
        raise SemanticError("PAYLOAD_FIELD_INVALID")
    return items


def _valid_interval(start: Any, end: Any) -> None:
    if type(start) is int and (end is None or type(end) is int):
        if end is not None and start >= end:
            raise SemanticError("PAYLOAD_ENVELOPE_INVALID")
        return
    if start is not None and end is not None and _time(start) >= _time(end):
        raise SemanticError("INVALID_VALIDITY_INTERVAL")
    if start is not None:
        _time(start)
    if end is not None:
        _time(end)


def _event_from_verified(record: dict[str, Any]) -> dict[str, Any]:
    if "semantic_event" in record:
        event = record["semantic_event"]
        _required(event, ("eventId", "eventType", "recordedAt", "payload"), "INVALID_EVENT_ENVELOPE")
        return copy.deepcopy(event)

    body = record.get("body")
    envelope = record.get("payload")
    if type(body) is not dict or type(envelope) is not dict:
        raise SemanticError("INVALID_SEMANTIC_ENVELOPE")
    if set(envelope) != {"profile", "schema_version", "data", "valid_from_ns", "valid_to_ns"}:
        raise SemanticError("PAYLOAD_ENVELOPE_INVALID")
    if envelope["profile"] != PROFILE:
        raise SemanticError("PAYLOAD_ENVELOPE_INVALID")
    if body.get("schema_version") != SCHEMA_VERSION or envelope["schema_version"] != SCHEMA_VERSION:
        raise SemanticError("UNSUPPORTED_SCHEMA_VERSION")
    if type(envelope["data"]) is not dict:
        raise SemanticError("PAYLOAD_ENVELOPE_INVALID")
    start, end = envelope["valid_from_ns"], envelope["valid_to_ns"]
    if type(start) is not int or (end is not None and type(end) is not int):
        raise SemanticError("PAYLOAD_ENVELOPE_INVALID")
    _valid_interval(start, end)
    event = {
        "eventId": record["body_cid"],
        "eventType": body["event_kind"],
        "recordedAt": body["event_time"],
        "payload": copy.deepcopy(envelope["data"]),
        "parents": [pwm_oracle.cid_text(parent) for parent in body["parent_event_cids"]],
        "principalScope": body["principal_scope"],
        "authorKeyId": body["author_key_id"],
        "logSequence": record["log_sequence"],
        "verified": True,
    }
    event["validFrom"] = start
    event["validTo"] = end
    return event


OPERATIONS = {
    "pwm.evidence": "EVIDENCE_CREATE",
    "pwm.policy": "POLICY_CREATE",
    "pwm.model.propose": "MODEL_PROPOSE",
    "pwm.model.review": "MODEL_REVIEW",
    "pwm.model.accept": "MODEL_ACCEPT",
    "pwm.model.update": "MODEL_UPDATE",
    "pwm.model.dispute": "MODEL_DISPUTE",
    "pwm.model.revoke": "MODEL_REVOKE",
    "pwm.privacy-boundary.approve": "PRIVACY_BOUNDARY_APPROVE",
    "pwm.privacy-boundary.revoke": "PRIVACY_BOUNDARY_REVOKE",
    "pwm.contradiction.propose": "CONTRADICTION_PROPOSE",
    "pwm.contradiction.review": "CONTRADICTION_REVIEW",
    "pwm.contradiction.accept": "CONTRADICTION_ACCEPT",
    "pwm.contradiction.resolve": "CONTRADICTION_RESOLVE",
    "pwm.topology.edge": "TOPOLOGY_EDGE_CREATE",
    "pwm.possible-world": "POSSIBLE_WORLD_CREATE",
    "pwm.query-authority": "QUERY_AUTHORITY_GRANT",
    "hpl.request": "HPL_REQUEST_CREATE",
    "hpl.authorization": "HPL_AUTHORIZE",
    "hpl.projection": "HPL_PROJECT",
    "hpl.revoke": "HPL_REVOKE",
    "pwm.conformance.evaluate": "CONFORMANCE_EVALUATE",
}


def _authenticate(state: State, event: dict[str, Any]) -> str | None:
    if not event.get("verified") or event["eventType"] == "pwm.genesis":
        return None
    operation = OPERATIONS.get(event["eventType"])
    if operation is None:
        raise SemanticError("UNSUPPORTED_EVENT_KIND")
    key, scope, sequence = event["authorKeyId"], event["principalScope"], event["logSequence"]
    key_scope = [grant for grant in state.grants.values() if grant["key_id"] == key and grant["scope_id"] == scope]
    operation_matches = [grant for grant in key_scope if operation in grant["operations"] or "*" in grant["operations"]]
    if not operation_matches:
        raise SemanticError("GRANT_NOT_FOUND")
    active = [
        grant for grant in operation_matches
        if grant["valid_from_log_sequence"] <= sequence
        and (grant["valid_to_log_sequence"] is None or sequence < grant["valid_to_log_sequence"])
    ]
    if not active:
        raise SemanticError("GRANT_NOT_ACTIVE")
    principals = {grant["principal_id"] for grant in active}
    if len(principals) != 1:
        raise SemanticError("PRINCIPAL_AMBIGUOUS")
    required_capabilities = event.get("payload", {}).get("capabilities", [])
    granted_capabilities = {capability for grant in active for capability in grant["capabilities"]}
    if any(capability not in granted_capabilities for capability in required_capabilities):
        raise SemanticError("CAPABILITY_NOT_GRANTED")
    return next(iter(principals))


def _proposal_model_id(state: State, proposal_id: str) -> str | None:
    return next((model_id for model_id, value in state.proposal_events.items() if value == proposal_id), None)


def _normalize_signed_event(state: State, event: dict[str, Any], principal: str | None) -> dict[str, Any]:
    """Translate the normative snake-case registry into reducer-local names."""
    if not event.get("verified"):
        return event
    kind, data = event["eventType"], event["payload"]
    translated = copy.deepcopy(event)
    if kind == "pwm.evidence":
        _exact(data, ("evidence_id", "evidence_kind", "subject_ids", "source_uri", "content_digest", "privacy_class", "properties"))
        translated["eventType"] = "pwm.evidence.recorded"
        translated["payload"] = {**copy.deepcopy(data), "evidenceId": data["evidence_id"], "privacyClass": data["privacy_class"]}
    elif kind == "pwm.policy":
        _exact(data, ("policy_id", "policy_profile", "content_digest", "privacy_floor", "properties"))
        translated["eventType"] = "pwm.policy.registered"
        translated["payload"] = {
            "policyId": data["policy_id"],
            "policyProfile": data["policy_profile"],
            "contentDigest": data["content_digest"],
            "privacyFloor": data["privacy_floor"],
            "properties": data["properties"],
        }
    elif kind == "pwm.model.propose":
        _exact(data, ("proposal_id", "model_id", "family", "kind", "subject_ids", "perspective_id", "world_id", "evidence_ids", "declared_privacy_class", "properties", "confidence"))
        translated["eventType"] = "pwm.model.proposed"
        translated["payload"] = {
            "modelId": data["model_id"], "familyId": data["family"], "kind": data["kind"],
            "subjectIds": data["subject_ids"], "perspective": data["perspective_id"],
            "worldId": data["world_id"], "evidenceRefs": data["evidence_ids"],
            "privacyClass": data["declared_privacy_class"], "state": data["properties"],
            "confidence": data["confidence"],
            "_proposalId": data["proposal_id"],
            "_authenticatedPrincipal": principal,
        }
    elif kind == "pwm.model.review":
        _exact(data, ("review_id", "proposal_id", "reviewer_principal_id", "decision", "reason"))
        model_id = _proposal_model_id(state, data["proposal_id"])
        translated["eventType"] = "pwm.model.reviewed"
        translated["payload"] = {"modelId": model_id, "proposalEventId": data["proposal_id"], "decision": "ACCEPT" if data["decision"] == "APPROVE" else data["decision"], "reviewer": data["reviewer_principal_id"], "reason": data["reason"], "_reviewId": data["review_id"]}
    elif kind in {"pwm.model.accept", "pwm.model.update"}:
        names = ("model_id", "proposal_id", "review_id") if kind.endswith("accept") else ("model_id", "previous_model_id", "proposal_id", "review_id")
        _exact(data, names)
        translated["eventType"] = "pwm.model.accepted" if kind.endswith("accept") else "pwm.model.updated"
        translated["payload"] = {"modelId": data["model_id"], "proposalEventId": data["proposal_id"], "reviewEventId": data["review_id"]}
        if "previous_model_id" in data:
            translated["payload"]["previousModelId"] = data["previous_model_id"]
    elif kind in {"pwm.model.dispute", "pwm.model.revoke"}:
        names = ("model_id", "reason", "evidence_ids") if kind.endswith("dispute") else ("model_id", "reason")
        _exact(data, names)
        translated["eventType"] = "pwm.model.disputed" if kind.endswith("dispute") else "pwm.model.revoked"
        translated["payload"] = {"modelId": data["model_id"], "reason": data["reason"]}
    elif kind == "pwm.topology.edge":
        _exact(data, ("edge_id", "source_model_id", "target_model_id", "edge_type", "world_id", "evidence_ids", "declared_privacy_class"))
        translated["eventType"] = "pwm.topology.edge-added"
        translated["payload"] = {"edgeId": data["edge_id"], "sourceModelId": data["source_model_id"], "targetModelId": data["target_model_id"], "edgeType": data["edge_type"], "worldId": data["world_id"], "evidenceIds": data["evidence_ids"], "privacyClass": data["declared_privacy_class"]}
    elif kind == "pwm.possible-world":
        _exact(data, ("world_id", "parent_world_id", "base_state_cid", "base_time_ns", "declared_privacy_class", "purpose"))
        translated["eventType"] = "pwm.possible-world.created"
        translated["payload"] = {"worldId": data["world_id"], "parentWorldId": data["parent_world_id"], "baseStateId": data["base_state_cid"], "baseTime": data["base_time_ns"], "privacyClass": data["declared_privacy_class"], "purpose": data["purpose"]}
    elif kind.startswith("pwm.contradiction."):
        translated["eventType"] = kind.replace(".propose", ".proposed").replace(".review", ".reviewed").replace(".accept", ".accepted").replace(".resolve", ".resolved")
        if kind == "pwm.contradiction.propose":
            _exact(data, ("proposal_id", "contradiction_id", "contradiction_type", "reference_ids", "world_id", "evidence_ids", "explanation"))
            translated["payload"] = {"contradictionId": data["contradiction_id"], "status": "OPEN", "modelIds": data["reference_ids"], "evidenceIds": data["evidence_ids"], "worldId": data["world_id"], "contradictionType": data["contradiction_type"], "explanation": data["explanation"], "_proposalId": data["proposal_id"]}
        elif kind == "pwm.contradiction.review":
            _exact(data, ("review_id", "proposal_id", "reviewer_principal_id", "decision", "reason"))
            identifier = next((key for key, value in state.contradiction_proposals.items() if value == data["proposal_id"]), None)
            translated["payload"] = {"contradictionId": identifier, "proposalEventId": data["proposal_id"], "decision": "ACCEPT" if data["decision"] == "APPROVE" else data["decision"], "reviewer": data["reviewer_principal_id"], "_reviewId": data["review_id"]}
        elif kind == "pwm.contradiction.accept":
            _exact(data, ("contradiction_id", "proposal_id", "review_id"))
            translated["payload"] = {"contradictionId": data["contradiction_id"], "proposalEventId": data["proposal_id"], "reviewEventId": data["review_id"]}
        else:
            _exact(data, ("resolution_id", "contradiction_id", "status", "resolver_principal_id", "explanation", "evidence_ids"))
            translated["payload"] = {"contradictionId": data["contradiction_id"], "status": data["status"], "resolver": data["resolver_principal_id"], "evidenceRefs": data["evidence_ids"], "resolutionId": data["resolution_id"], "explanation": data["explanation"]}
    return translated


def _has_reference(state: State, reference: str) -> bool:
    return (
        reference in state.accepted_event_ids
        or reference in state.evidence
        or reference in state.models
        or reference in state.derived_models
    )


def _privacy_for_model(state: State, model: dict[str, Any]) -> tuple[str, bool, list[str]]:
    declared = model.get("privacyClass")
    _rank(declared)
    refs = [
        *_unique_texts(model.get("evidenceRefs", [])),
        *_unique_texts(model.get("dependencyRefs", [])),
        *_unique_texts(model.get("sourceModelIds", [])),
    ]
    if any(not _has_reference(state, ref) for ref in refs):
        raise SemanticError("EVIDENCE_REFERENCE_NOT_FOUND")
    classes = [declared]
    for ref in refs:
        item = state.evidence.get(ref) or state.models.get(ref) or state.derived_models.get(ref)
        if item:
            classes.append(item.get("effectivePrivacyClass", item.get("privacyClass", "PERSONAL")))
    source_class = _join(classes)
    effective = source_class
    declassified = False
    released: set[str] = set()
    for boundary in model.get("privacyBoundaries", []):
        _required(
            boundary,
            ("boundaryKind", "inputPrivacyClass", "outputPrivacyClass", "sourceRefs", "policyRef", "approved"),
        )
        boundary_refs = set(_unique_texts(boundary["sourceRefs"]))
        if boundary["boundaryKind"] not in {"PROOF", "REDACTION"}:
            raise SemanticError("INVALID_DECLASSIFICATION_BOUNDARY")
        if _rank(boundary["outputPrivacyClass"]) > _rank(boundary["inputPrivacyClass"]):
            raise SemanticError("INVALID_DECLASSIFICATION_BOUNDARY")
        if boundary["approved"] is True:
            if boundary["policyRef"] not in state.policies or not set(refs).issubset(boundary_refs):
                raise SemanticError("DECLASSIFICATION_NOT_AUTHORIZED")
            if _rank(boundary["inputPrivacyClass"]) >= _rank(source_class):
                effective = PRIVACY[min(_rank(effective), _rank(boundary["outputPrivacyClass"]))]
                declassified = True
                released.update(_unique_texts(boundary.get("releasedFields", [])))
    claimed = model.get("effectivePrivacyClass")
    if claimed is not None and claimed != effective:
        raise SemanticError("PRIVACY_EFFECTIVE_CLASS_MISMATCH")
    return effective, declassified, sorted(released)


def _family(state: State, family_id: str) -> dict[str, Any]:
    family = state.families.get(family_id)
    if family is None:
        raise SemanticError("UNKNOWN_MODEL_FAMILY")
    return family


def _validate_model(state: State, model: dict[str, Any]) -> dict[str, Any]:
    _required(model, ("modelId", "familyId", "kind", "subjectIds", "perspective", "privacyClass"))
    model_id = _text(model["modelId"], "MALFORMED_MODEL")
    kind = model["kind"]
    if kind not in KINDS:
        raise SemanticError("UNKNOWN_MODEL_KIND")
    subjects = _unique_texts(model["subjectIds"], "MODEL_CARDINALITY_VIOLATION")
    family = _family(state, _text(model["familyId"], "MALFORMED_MODEL"))
    if kind not in family["allowedKinds"]:
        raise SemanticError("FAMILY_KIND_NOT_ALLOWED")
    minimum, maximum = family.get("minSubjects", 1), family.get("maxSubjects")
    if len(subjects) < minimum or (maximum is not None and len(subjects) > maximum):
        raise SemanticError("MODEL_CARDINALITY_VIOLATION")
    perspective = model["perspective"]
    if perspective is not None:
        _text(perspective, "FAMILY_KIND_NOT_ALLOWED")
    if kind == "SELF" and perspective not in subjects:
        raise SemanticError("FAMILY_KIND_NOT_ALLOWED")
    if kind == "OTHER" and perspective in subjects:
        raise SemanticError("FAMILY_KIND_NOT_ALLOWED")
    if kind == "RELATIONSHIP" and len(subjects) < 2:
        raise SemanticError("MODEL_CARDINALITY_VIOLATION")
    if kind == "META":
        target = model.get("targetModelId") or (model.get("state") or {}).get("targetModelId")
        if not target or target not in state.models:
            raise SemanticError("META_TARGET_NOT_FOUND")
    if kind == "WORLD" and not subjects:
        raise SemanticError("MODEL_CARDINALITY_VIOLATION")
    if model.get("_authenticatedPrincipal") is not None and kind == "SELF" and subjects != [model["_authenticatedPrincipal"]]:
        raise SemanticError("FAMILY_KIND_NOT_ALLOWED")
    confidence = model.get("confidence")
    if confidence is not None:
        _exact(confidence, ("coefficient", "scale"))
        coefficient, scale = confidence["coefficient"], confidence["scale"]
        if type(coefficient) is not int or type(scale) is not int or not 0 <= scale <= 18 or coefficient < 0 or coefficient > 10**scale or (coefficient == 0 and scale != 0) or (scale and coefficient % 10 == 0):
            raise SemanticError("PAYLOAD_FIELD_INVALID")
    if kind == "POSSIBLE_WORLD":
        world = model.get("worldId") or (model.get("state") or {}).get("worldId")
        parent = model.get("parentWorldId") or (model.get("state") or {}).get("parentWorldId")
        if world in {None, "actual", "world:actual"} or world == parent or world not in state.worlds:
            raise SemanticError("POSSIBLE_WORLD_SCOPE_VIOLATION")
        if state.worlds[world]["parentWorldId"] != parent:
            raise SemanticError("POSSIBLE_WORLD_SCOPE_VIOLATION")
    effective, declassified, released = _privacy_for_model(state, model)
    result = copy.deepcopy(model)
    result["modelId"] = model_id
    result["effectivePrivacyClass"] = effective
    result["declassified"] = declassified
    result["releasedFields"] = released
    return result


def _would_cycle(edges: Iterable[dict[str, Any]], source: str, target: str) -> bool:
    graph: dict[str, set[str]] = {}
    for edge in edges:
        if edge.get("edgeType") == "DEPENDS_ON":
            graph.setdefault(edge["sourceModelId"], set()).add(edge["targetModelId"])
    graph.setdefault(source, set()).add(target)
    pending = [target]
    seen: set[str] = set()
    while pending:
        node = pending.pop()
        if node == source:
            return True
        if node not in seen:
            seen.add(node)
            pending.extend(graph.get(node, ()))
    return False


def _authority_active(authority: dict[str, Any], request: dict[str, Any]) -> None:
    for authority_name, request_name in (
        ("principalId", "principalId"),
        ("recipientId", "recipientId"),
        ("purpose", "purpose"),
    ):
        if authority.get(authority_name) != request.get(request_name):
            raise SemanticError("AUTHORITY_BINDING_MISMATCH")
    at = _time(request.get("at"))
    if authority.get("issuedAt") is not None and at < _time(authority["issuedAt"]):
        raise SemanticError("AUTHORITY_NOT_YET_VALID")
    if authority.get("expiresAt") is None or at >= _time(authority["expiresAt"]):
        raise SemanticError("AUTHORITY_EXPIRED")
    if authority.get("revoked"):
        raise SemanticError("AUTHORITY_REVOKED")


def _query(state: State, query: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    request = {
        "principalId": query.get("principalId"),
        "recipientId": query.get("recipientId"),
        "purpose": query.get("purpose"),
        "at": query.get("at"),
    }
    _authority_active(authority, request)
    subjects = set(_unique_texts(query.get("subjectIds", [])))
    allowed_subjects = set(authority.get("subjectIds", []))
    if subjects and not subjects.issubset(allowed_subjects):
        raise SemanticError("QUERY_AUTHORITY_MISMATCH")
    families = set(_unique_texts(query.get("familyIds", [])))
    allowed_families = set(authority.get("familyIds", []))
    if families and allowed_families and not families.issubset(allowed_families):
        raise SemanticError("QUERY_AUTHORITY_MISMATCH")
    world = query.get("worldId", "world:actual")
    if world != authority.get("worldId", "world:actual"):
        raise SemanticError("QUERY_AUTHORITY_MISMATCH")
    ceiling = query.get("maximumPrivacyClass", authority.get("maximumPrivacyClass", "PERSONAL"))
    if _rank(ceiling) > _rank(authority.get("maximumPrivacyClass", "PERSONAL")):
        raise SemanticError("QUERY_AUTHORITY_MISMATCH")
    include_disputed = query.get("includeDisputed", False) is True
    at = query.get("asOfValidTime")
    selected: list[str] = []
    for model_id, model in state.models.items():
        status = model["lifecycleStatus"]
        if status != "ACCEPTED" and not (include_disputed and status == "DISPUTED"):
            continue
        model_subjects = set(model.get("subjectIds", []))
        if subjects and not model_subjects.intersection(subjects):
            continue
        if model_subjects and not model_subjects.issubset(allowed_subjects):
            continue
        if families and model["familyId"] not in families:
            continue
        model_world = model.get("worldId", "world:actual")
        if model_world != world:
            continue
        if _rank(model["effectivePrivacyClass"]) > _rank(ceiling):
            continue
        if at is not None:
            point = _time(at)
            if model.get("validFrom") is not None and point < _time(model["validFrom"]):
                continue
            if model.get("validTo") is not None and point >= _time(model["validTo"]):
                continue
        selected.append(model_id)
    return {"modelIds": sorted(selected), "worldId": world}


def _project(state: State, data: dict[str, Any]) -> dict[str, Any]:
    _required(data, ("authorityId", "principalId", "recipientId", "purpose", "requestedFields", "at"))
    authority = state.query_authorities.get(data["authorityId"]) or state.grants.get(data["authorityId"])
    if authority is None:
        raise SemanticError("AUTHORITY_NOT_FOUND")
    _authority_active(authority, data)
    requested = _unique_texts(data["requestedFields"])
    allowed = set(_unique_texts(authority.get("allowedFields", [])))
    fields: dict[str, Any] = {}
    provenance: list[str] = []
    ceiling = authority.get("maximumPrivacyClass", "PERSONAL")
    for model_id in sorted(state.models):
        model = state.models[model_id]
        field_name = model.get("field")
        if field_name not in requested or field_name not in allowed:
            continue
        if model.get("lifecycleStatus") != "ACCEPTED" or _rank(model["effectivePrivacyClass"]) > _rank(ceiling):
            continue
        fields[field_name] = copy.deepcopy(model.get("value"))
        if not model.get("declassified"):
            provenance.extend(model.get("evidenceRefs", []))
    return {
        "authorityId": data["authorityId"],
        "principalId": data["principalId"],
        "recipientId": data["recipientId"],
        "purpose": data["purpose"],
        "expiresAt": authority["expiresAt"],
        "fields": fields,
        "provenanceRefs": sorted(set(provenance)),
    }


def _apply(state: State, event: dict[str, Any]) -> None:
    authenticated_principal = _authenticate(state, event)
    if authenticated_principal is not None:
        event["authenticatedPrincipal"] = authenticated_principal
    event = _normalize_signed_event(state, event, authenticated_principal)
    _required(event, ("eventId", "eventType", "recordedAt", "payload"), "INVALID_EVENT_ENVELOPE")
    event_id = _text(event["eventId"], "INVALID_EVENT_ENVELOPE")
    event_type = _text(event["eventType"], "INVALID_EVENT_ENVELOPE")
    _time(event["recordedAt"])
    data = event["payload"]
    if type(data) is not dict or event_id in state.event_types:
        raise SemanticError("DUPLICATE_EVENT_ID" if event_id in state.event_types else "MALFORMED_PAYLOAD")
    for parent in _unique_texts(event.get("parents", []), "INVALID_CAUSAL_ORDER"):
        if parent not in state.event_types:
            raise SemanticError("INVALID_CAUSAL_ORDER")
    _valid_interval(event.get("validFrom"), event.get("validTo"))

    if event_type == "pwm.genesis":
        if state.accepted_event_ids:
            raise SemanticError("INVALID_GENESIS")
        if event.get("verified"):
            _exact(data, ("scope_id", "root_principal_id", "root_key_id", "principals", "grants"))
            if data["scope_id"] != event["principalScope"] or data["root_key_id"] != event["authorKeyId"] or event["logSequence"] != 0:
                raise SemanticError("ROOT_TRUST_MISMATCH")
            principals = _canonical_set(data["principals"])
            grants = _canonical_set(data["grants"])
            for principal in principals:
                _exact(principal, ("principal_id", "principal_class"))
                state.principals[_text(principal["principal_id"], "PAYLOAD_FIELD_INVALID")] = copy.deepcopy(principal)
            for grant in grants:
                _exact(grant, ("grant_id", "principal_id", "key_id", "scope_id", "operations", "capabilities", "grant_class", "valid_from_log_sequence", "valid_to_log_sequence"))
                if grant["principal_id"] not in state.principals or grant["scope_id"] != data["scope_id"]:
                    raise SemanticError("PAYLOAD_FIELD_INVALID")
                _canonical_set(grant["operations"])
                _canonical_set(grant["capabilities"])
                start, end = grant["valid_from_log_sequence"], grant["valid_to_log_sequence"]
                if type(start) is not int or start < 0 or (end is not None and (type(end) is not int or end <= start)):
                    raise SemanticError("PAYLOAD_FIELD_INVALID")
                state.grants[grant["grant_id"]] = copy.deepcopy(grant)
            roots = [grant for grant in state.grants.values() if grant["grant_class"] == "ROOT" and grant["principal_id"] == data["root_principal_id"] and grant["key_id"] == data["root_key_id"] and grant["valid_from_log_sequence"] == 0]
            if not roots:
                raise SemanticError("ROOT_TRUST_MISMATCH")
            state.worlds["world:actual"] = {"worldId": "world:actual", "parentWorldId": None}
        state.families.update(copy.deepcopy(DEFAULT_FAMILIES))
    elif event_type == "pwm.family.registered":
        _required(data, ("familyId", "allowedKinds"))
        family_id = _text(data["familyId"], "MALFORMED_PAYLOAD")
        kinds = _unique_texts(data["allowedKinds"])
        if not kinds or any(kind not in KINDS for kind in kinds):
            raise SemanticError("UNKNOWN_MODEL_KIND")
        definition = {
            "allowedKinds": kinds,
            "minSubjects": data.get("minSubjects", 1),
            "maxSubjects": data.get("maxSubjects"),
            "stability": data.get("stability", "EXPERIMENTAL"),
        }
        if family_id in state.families and state.families[family_id] != definition:
            raise SemanticError("FAMILY_ALREADY_REGISTERED")
        state.families[family_id] = definition
    elif event_type in {"pwm.principal.granted", "pwm.principal.grant"}:
        _required(data, ("grantId", "principalId", "recipientId", "purpose", "capabilities", "expiresAt"))
        grant_id = _text(data["grantId"], "MALFORMED_PAYLOAD")
        _unique_texts(data["capabilities"])
        if grant_id in state.grants:
            raise SemanticError("GRANT_ALREADY_EXISTS")
        grant = copy.deepcopy(data)
        grant.setdefault("issuedAt", event["recordedAt"])
        grant["revoked"] = False
        _valid_interval(grant["issuedAt"], grant["expiresAt"])
        state.grants[grant_id] = grant
    elif event_type in {"pwm.principal.revoked", "pwm.principal.grant-revoked"}:
        _required(data, ("grantId",))
        if data["grantId"] not in state.grants:
            raise SemanticError("AUTHORITY_NOT_FOUND")
        state.grants[data["grantId"]]["revoked"] = True
    elif event_type in {"pwm.evidence.recorded", "pwm.evidence"}:
        _required(data, ("evidenceId", "privacyClass"))
        evidence_id = _text(data["evidenceId"], "MALFORMED_PAYLOAD")
        _rank(data["privacyClass"])
        if evidence_id in state.evidence:
            raise SemanticError("EVIDENCE_ALREADY_EXISTS")
        state.evidence[evidence_id] = copy.deepcopy(data)
        state.evidence[evidence_id]["effectivePrivacyClass"] = data["privacyClass"]
    elif event_type == "pwm.policy.registered":
        _required(data, ("policyId", "privacyFloor"))
        _rank(data["privacyFloor"])
        state.policies[_text(data["policyId"], "MALFORMED_PAYLOAD")] = copy.deepcopy(data)
    elif event_type == "pwm.possible-world.created":
        _required(data, ("worldId", "parentWorldId", "baseStateId", "baseTime"))
        world_id = _text(data["worldId"], "POSSIBLE_WORLD_SCOPE_VIOLATION")
        if world_id in {"actual", "world:actual"} or world_id == data["parentWorldId"] or world_id in state.worlds:
            raise SemanticError("POSSIBLE_WORLD_SCOPE_VIOLATION")
        _time(data["baseTime"])
        state.worlds[world_id] = copy.deepcopy(data)
    elif event_type == "pwm.model.proposed":
        model = _validate_model(state, data)
        model_id = model["modelId"]
        if model_id in state.models or model_id in state.candidates:
            raise SemanticError("MODEL_ALREADY_EXISTS")
        state.candidates[model_id] = model
        if authenticated_principal is not None:
            state.candidates[model_id]["_authorPrincipal"] = authenticated_principal
        state.proposal_events[model_id] = data.get("_proposalId", event_id)
    elif event_type == "pwm.model.reviewed":
        _required(data, ("modelId", "proposalEventId", "decision", "reviewer"))
        model_id = data["modelId"]
        if model_id not in state.candidates or data["proposalEventId"] != state.proposal_events.get(model_id):
            raise SemanticError("LIFECYCLE_PRECONDITION_MISSING")
        if data["decision"] not in {"ACCEPT", "REJECT"}:
            raise SemanticError("INVALID_REVIEW_DECISION")
        if authenticated_principal is not None and data["reviewer"] != authenticated_principal:
            raise SemanticError("REVIEW_AUTHORITY_MISMATCH")
        if authenticated_principal is None and data["reviewer"] != state.candidates[model_id]["perspective"]:
            raise SemanticError("REVIEW_AUTHORITY_MISMATCH")
        if authenticated_principal is not None and state.candidates[model_id].get("_authorPrincipal") == authenticated_principal:
            capabilities = {
                capability
                for grant in state.grants.values()
                if grant["principal_id"] == authenticated_principal
                and grant["key_id"] == event["authorKeyId"]
                for capability in grant["capabilities"]
            }
            if "pwm.review.self" not in capabilities:
                raise SemanticError("REVIEW_SEPARATION_VIOLATION")
        state.reviews[model_id] = copy.deepcopy(data)
        state.review_events[model_id] = data.get("_reviewId", event_id)
    elif event_type in {"pwm.model.accepted", "pwm.model.updated"}:
        _required(data, ("modelId", "proposalEventId", "reviewEventId"))
        model_id = data["modelId"]
        candidate = state.candidates.get(model_id)
        review = state.reviews.get(model_id)
        if (
            candidate is None
            or review is None
            or review["decision"] != "ACCEPT"
            or data["proposalEventId"] != state.proposal_events.get(model_id)
            or data["reviewEventId"] != state.review_events.get(model_id)
        ):
            raise SemanticError("LIFECYCLE_PRECONDITION_MISSING")
        previous = data.get("previousModelId") or candidate.get("previousModelId")
        if event_type == "pwm.model.updated":
            if previous not in state.models or state.models[previous]["lifecycleStatus"] not in CURRENT:
                raise SemanticError("LIFECYCLE_PRECONDITION_MISSING")
            predecessor = state.models[previous]
            if previous == model_id or any(candidate.get(name) != predecessor.get(name) for name in ("familyId", "kind", "subjectIds", "perspective", "worldId")):
                raise SemanticError("LIFECYCLE_PRECONDITION_MISSING")
            state.models[previous]["lifecycleStatus"] = "SUPERSEDED"
        elif previous is not None:
            raise SemanticError("LIFECYCLE_PRECONDITION_MISSING")
        accepted = copy.deepcopy(candidate)
        accepted["lifecycleStatus"] = "ACCEPTED"
        accepted["proposalEventId"] = data["proposalEventId"]
        accepted["reviewEventId"] = data["reviewEventId"]
        accepted["validFrom"] = event.get("validFrom")
        accepted["validTo"] = event.get("validTo")
        state.models[model_id] = accepted
        del state.candidates[model_id]
        del state.reviews[model_id]
    elif event_type in {"pwm.model.disputed", "pwm.model.revoked", "pwm.model.superseded"}:
        _required(data, ("modelId", "reason"))
        if data["modelId"] not in state.models:
            raise SemanticError("MODEL_NOT_FOUND")
        state.models[data["modelId"]]["lifecycleStatus"] = event_type.rsplit(".", 1)[1].upper()
        state.models[data["modelId"]]["statusReason"] = data["reason"]
    elif event_type == "pwm.model.derived":
        _required(data, ("modelId", "familyId", "kind", "sourceModelIds", "privacyClass"))
        family = _family(state, data["familyId"])
        if data["kind"] not in family["allowedKinds"]:
            raise SemanticError("FAMILY_KIND_NOT_ALLOWED")
        sources = _unique_texts(data["sourceModelIds"])
        if any(not _has_reference(state, source) for source in sources):
            raise SemanticError("EVIDENCE_REFERENCE_NOT_FOUND")
        derived = copy.deepcopy(data)
        derived["effectivePrivacyClass"] = _join([
            data["privacyClass"],
            *(state.models.get(source, state.derived_models.get(source, {})).get("effectivePrivacyClass", "PERSONAL") for source in sources),
        ])
        state.derived_models[data["modelId"]] = derived
    elif event_type == "pwm.topology.edge-added":
        _required(data, ("edgeId", "sourceModelId", "edgeType", "targetModelId"))
        source, target = data["sourceModelId"], data["targetModelId"]
        if source not in state.models or target not in state.models:
            raise SemanticError("TOPOLOGY_ENDPOINT_NOT_FOUND")
        if data["edgeId"] in state.edges:
            raise SemanticError("TOPOLOGY_EDGE_ALREADY_EXISTS")
        if data["edgeType"] == "DEPENDS_ON" and _would_cycle(state.edges.values(), source, target):
            raise SemanticError("DEPENDENCY_CYCLE")
        edge = copy.deepcopy(data)
        edge["effectivePrivacyClass"] = _join([
            data.get("privacyClass", "PERSONAL"),
            state.models[source]["effectivePrivacyClass"],
            state.models[target]["effectivePrivacyClass"],
        ])
        state.edges[data["edgeId"]] = edge
    elif event_type == "pwm.contradiction.proposed":
        _required(data, ("contradictionId", "status"))
        refs = [*_unique_texts(data.get("modelIds", [])), *_unique_texts(data.get("evidenceIds", []))]
        if len(refs) < 2 or any(not _has_reference(state, ref) for ref in refs):
            raise SemanticError("CONTRADICTION_INPUT_NOT_FOUND")
        identifier = data["contradictionId"]
        state.contradiction_candidates[identifier] = copy.deepcopy(data)
        state.contradiction_proposals[identifier] = data.get("_proposalId", event_id)
    elif event_type == "pwm.contradiction.reviewed":
        _required(data, ("contradictionId", "proposalEventId", "decision", "reviewer"))
        identifier = data["contradictionId"]
        if identifier not in state.contradiction_candidates or data["proposalEventId"] != state.contradiction_proposals.get(identifier):
            raise SemanticError("LIFECYCLE_PRECONDITION_MISSING")
        if data["decision"] not in {"ACCEPT", "REJECT"}:
            raise SemanticError("INVALID_REVIEW_DECISION")
        state.contradiction_reviews[identifier] = copy.deepcopy(data)
        state.contradiction_review_events[identifier] = data.get("_reviewId", event_id)
    elif event_type == "pwm.contradiction.accepted":
        _required(data, ("contradictionId", "proposalEventId", "reviewEventId"))
        identifier = data["contradictionId"]
        review = state.contradiction_reviews.get(identifier)
        if (
            identifier not in state.contradiction_candidates
            or review is None
            or review["decision"] != "ACCEPT"
            or data["proposalEventId"] != state.contradiction_proposals.get(identifier)
            or data["reviewEventId"] != state.contradiction_review_events.get(identifier)
        ):
            raise SemanticError("LIFECYCLE_PRECONDITION_MISSING")
        contradiction = copy.deepcopy(state.contradiction_candidates.pop(identifier))
        contradiction["acceptanceStatus"] = "ACCEPTED"
        contradiction["resolutions"] = []
        state.contradictions[identifier] = contradiction
    elif event_type == "pwm.contradiction.resolved":
        _required(data, ("contradictionId", "status", "resolver", "evidenceRefs"))
        contradiction = state.contradictions.get(data["contradictionId"])
        if contradiction is None or data["status"] not in {"EXPLAINED", "SUPERSEDED", "RESOLVED", "IRREDUCIBLE", "PERSPECTIVE_DEPENDENT"}:
            raise SemanticError("CONTRADICTION_NOT_FOUND")
        if any(not _has_reference(state, ref) for ref in _unique_texts(data["evidenceRefs"])):
            raise SemanticError("EVIDENCE_REFERENCE_NOT_FOUND")
        contradiction["status"] = data["status"]
        contradiction["resolutions"].append(copy.deepcopy(data))
    elif event_type == "pwm.prediction.recorded":
        _required(data, ("predictionId", "modelId", "evaluatorId"))
        if data["modelId"] not in state.models and data["modelId"] not in state.derived_models:
            raise SemanticError("MODEL_NOT_FOUND")
        state.predictions[data["predictionId"]] = copy.deepcopy(data)
    elif event_type == "pwm.calibration.recorded":
        _required(data, ("predictionId", "evaluatorId", "scorePpm"))
        prediction = state.predictions.get(data["predictionId"])
        if prediction is None or prediction["evaluatorId"] != data["evaluatorId"]:
            raise SemanticError("CALIBRATION_SCOPE_MISMATCH")
        if type(data["scorePpm"]) is not int or not 0 <= data["scorePpm"] <= 1_000_000:
            raise SemanticError("CALIBRATION_SCORE_INVALID")
        state.calibrations[event_id] = copy.deepcopy(data)
    elif event_type == "pwm.query.authority-granted":
        _required(data, ("authorityId", "principalId", "recipientId", "purpose", "expiresAt"))
        authority = copy.deepcopy(data)
        authority.setdefault("issuedAt", event["recordedAt"])
        authority.setdefault("worldId", "world:actual")
        authority.setdefault("maximumPrivacyClass", "PERSONAL")
        authority["revoked"] = False
        _rank(authority["maximumPrivacyClass"])
        _valid_interval(authority["issuedAt"], authority["expiresAt"])
        state.query_authorities[data["authorityId"]] = authority
    elif event_type == "pwm.query-authority":
        _exact(data, ("authority_id", "principal_id", "recipient_id", "purpose", "world_ids", "subject_ids", "perspective_ids", "families", "privacy_ceiling", "allow_disputed", "valid_from_log_sequence", "valid_to_log_sequence"))
        for name in ("world_ids", "subject_ids", "perspective_ids", "families"):
            _canonical_set(data[name])
        _rank(data["privacy_ceiling"])
        _valid_interval(data["valid_from_log_sequence"], data["valid_to_log_sequence"])
        if data["principal_id"] != authenticated_principal:
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        if not data["world_ids"] or any(world not in state.worlds for world in data["world_ids"]):
            raise SemanticError("WORLD_SCOPE_VIOLATION")
        if data["authority_id"] in state.query_authorities:
            raise SemanticError("IDENTIFIER_CONFLICT")
        state.query_authorities[data["authority_id"]] = copy.deepcopy(data)
    elif event_type == "pwm.query.executed":
        _required(data, ("authorityId", "query"))
        authority = state.query_authorities.get(data["authorityId"])
        if authority is None:
            raise SemanticError("AUTHORITY_NOT_FOUND")
        state.last_query = _query(state, data["query"], authority)
    elif event_type == "hpl.projection.issued":
        _required(data, ("projectionId", "authorityId", "principalId", "recipientId", "purpose", "requestedFields", "at"))
        projection = _project(state, data)
        projection["projectionId"] = data["projectionId"]
        state.projections[data["projectionId"]] = projection
    elif event_type == "hpl.projection.revoked":
        _required(data, ("projectionId", "revocationId", "reason"))
        if data["projectionId"] not in state.projections:
            raise SemanticError("PROJECTION_NOT_FOUND")
        state.projection_revocations[data["revocationId"]] = copy.deepcopy(data)
        state.projections[data["projectionId"]]["revoked"] = True
    elif event_type == "hpl.request":
        _exact(data, ("request_id", "requester_principal_id", "recipient_id", "purpose", "world_id", "model_ids", "requested_fields", "maximum_privacy_class", "retention_until_ns", "capabilities"))
        _canonical_set(data["model_ids"]); _canonical_set(data["requested_fields"]); _canonical_set(data["capabilities"])
        _rank(data["maximum_privacy_class"])
        if data["requester_principal_id"] != authenticated_principal:
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        if data["world_id"] not in state.worlds or any(model_id not in state.models for model_id in data["model_ids"]):
            raise SemanticError("REFERENCE_NOT_FOUND")
        state.hpl_requests[data["request_id"]] = copy.deepcopy(data)
    elif event_type == "hpl.authorization":
        _exact(data, ("authorization_id", "request_id", "query_authority_id", "authorizer_principal_id", "allowed_model_ids", "allowed_fields", "privacy_ceiling", "valid_to_log_sequence"))
        request = state.hpl_requests.get(data["request_id"])
        authority = state.query_authorities.get(data["query_authority_id"])
        if request is None or authority is None:
            raise SemanticError("REFERENCE_NOT_FOUND")
        if data["authorizer_principal_id"] != authenticated_principal:
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        if not set(data["allowed_model_ids"]).issubset(request["model_ids"]) or not set(data["allowed_model_ids"]).issubset(authority.get("model_ids", data["allowed_model_ids"])):
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        if request["recipient_id"] != authority["recipient_id"] or request["purpose"] != authority["purpose"] or request["world_id"] not in authority["world_ids"]:
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        authorization = copy.deepcopy(data); authorization["status"] = "ACTIVE"
        state.hpl_authorizations[data["authorization_id"]] = authorization
    elif event_type == "hpl.projection":
        _exact(data, ("projection_id", "authorization_id", "recipient_id", "purpose", "world_id", "model_ids", "released_fields", "effective_privacy_class", "boundary_ids", "content_digest", "expires_at_ns"))
        if data["projection_id"] in state.projections:
            raise SemanticError("IDENTIFIER_CONFLICT")
        authorization = state.hpl_authorizations.get(data["authorization_id"])
        if authorization is None:
            raise SemanticError("REFERENCE_NOT_FOUND")
        request = state.hpl_requests[authorization["request_id"]]
        if authorization["status"] != "ACTIVE" or event["logSequence"] >= authorization["valid_to_log_sequence"]:
            raise SemanticError("AUTHORITY_EXPIRED")
        if (data["recipient_id"], data["purpose"], data["world_id"]) != (request["recipient_id"], request["purpose"], request["world_id"]):
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        if not set(data["model_ids"]).issubset(authorization["allowed_model_ids"]) or not set(data["released_fields"]).issubset(authorization["allowed_fields"]):
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        classes = [state.models[model_id]["effectivePrivacyClass"] for model_id in data["model_ids"] if model_id in state.models]
        if len(classes) != len(data["model_ids"]):
            raise SemanticError("REFERENCE_NOT_FOUND")
        effective = _join(classes)
        active_boundaries = [state.privacy_boundaries.get(identifier) for identifier in data["boundary_ids"]]
        if any(boundary is None or boundary.get("status") != "ACTIVE" for boundary in active_boundaries):
            raise SemanticError("REFERENCE_NOT_FOUND")
        for boundary in active_boundaries:
            if set(data["model_ids"]).issubset(boundary["source_ids"]) and set(data["released_fields"]).issubset(boundary["released_fields"]):
                effective = PRIVACY[min(_rank(effective), _rank(boundary["output_privacy_class"]))]
        if data["effective_privacy_class"] != effective:
            raise SemanticError("PRIVACY_EFFECTIVE_CLASS_MISMATCH")
        projection = copy.deepcopy(data); projection["status"] = "ACTIVE"
        state.projections[data["projection_id"]] = projection
    elif event_type == "hpl.revoke":
        _exact(data, ("target_type", "target_id", "reason"))
        targets = state.hpl_authorizations if data["target_type"] == "AUTHORIZATION" else state.projections if data["target_type"] == "PROJECTION" else None
        if targets is None or data["target_id"] not in targets:
            raise SemanticError("REFERENCE_NOT_FOUND")
        targets[data["target_id"]]["status"] = "REVOKED"
        targets[data["target_id"]]["revoked_at_log_sequence"] = event["logSequence"]
    elif event_type == "pwm.privacy-boundary.approve":
        _exact(data, ("boundary_id", "boundary_kind", "policy_id", "source_ids", "input_privacy_class", "output_privacy_class", "released_fields", "approver_principal_id", "expires_at_log_sequence"))
        if data["approver_principal_id"] != authenticated_principal:
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        if any(not _has_reference(state, ref) for ref in data["source_ids"]):
            raise SemanticError("REFERENCE_NOT_FOUND")
        if data["policy_id"] not in state.policies:
            raise SemanticError("REFERENCE_NOT_FOUND")
        if _rank(data["output_privacy_class"]) > _rank(data["input_privacy_class"]):
            raise SemanticError("PRIVACY_EFFECTIVE_CLASS_MISMATCH")
        boundary = copy.deepcopy(data); boundary["status"] = "ACTIVE"
        state.privacy_boundaries[data["boundary_id"]] = boundary
    elif event_type == "pwm.privacy-boundary.revoke":
        _exact(data, ("boundary_id", "reason"))
        if data["boundary_id"] not in state.privacy_boundaries:
            raise SemanticError("REFERENCE_NOT_FOUND")
        state.privacy_boundaries[data["boundary_id"]]["status"] = "REVOKED"
    elif event_type == "pwm.conformance.evaluate":
        _exact(data, ("evaluation_id", "suite_id", "suite_version", "suite_sha256", "implementation_id", "implementation_version", "passed_case_ids", "failed_case_ids", "evaluated_at_ns"))
        if set(data["passed_case_ids"]).intersection(data["failed_case_ids"]):
            raise SemanticError("PAYLOAD_FIELD_INVALID")
        state.evaluations[data["evaluation_id"]] = copy.deepcopy(data)
    else:
        raise SemanticError("UNSUPPORTED_EVENT_TYPE")

    state.accepted_event_ids.append(event_id)
    state.event_types[event_id] = event_type


def _state_output(state: State) -> dict[str, Any]:
    excluded_model_fields = {
        "_authenticatedPrincipal", "_authorPrincipal", "_proposalId",
        "declassified", "releasedFields", "statusReason",
    }
    models = {
        key: {
            field: copy.deepcopy(value)
            for field, value in state.models[key].items()
            if field not in excluded_model_fields
        }
        for key in sorted(state.models)
    }
    current = sorted(key for key, value in models.items() if value.get("lifecycleStatus") in CURRENT)
    historical = sorted(key for key, value in models.items() if value.get("lifecycleStatus") not in CURRENT)
    worlds = {
        world: sorted(key for key, model in models.items() if model.get("worldId") == world)
        for world in sorted(state.worlds)
    }
    return {
        "acceptedEventIds": list(state.accepted_event_ids),
        "principals": {key: state.principals[key] for key in sorted(state.principals)},
        "families": {key: state.families[key] for key in sorted(state.families)},
        "grants": {key: state.grants[key] for key in sorted(state.grants)},
        "evidence": {key: state.evidence[key] for key in sorted(state.evidence)},
        "policies": {
            key: {
                "policy_id": state.policies[key]["policyId"],
                "policy_profile": state.policies[key].get("policyProfile", "fixture-policy"),
                "content_digest": state.policies[key].get("contentDigest", b""),
                "privacy_floor": state.policies[key]["privacyFloor"],
                "properties": state.policies[key].get("properties", {}),
            }
            for key in sorted(state.policies)
        },
        "models": models,
        "currentModelIds": current,
        "historicalModelIds": historical,
        "candidateModelIds": sorted(state.candidates),
        "derivedModels": {key: state.derived_models[key] for key in sorted(state.derived_models)},
        "edges": {key: state.edges[key] for key in sorted(state.edges)},
        "possibleWorlds": worlds,
        "contradictions": {
            key: {
                field: copy.deepcopy(value)
                for field, value in state.contradictions[key].items()
                if field not in {"_proposalId", "acceptanceStatus"}
            }
            for key in sorted(state.contradictions)
        },
        "contradictionCandidateIds": sorted(state.contradiction_candidates),
        "predictions": {key: state.predictions[key] for key in sorted(state.predictions)},
        "calibrations": {key: state.calibrations[key] for key in sorted(state.calibrations)},
        "queryAuthorities": {key: state.query_authorities[key] for key in sorted(state.query_authorities)},
        "projections": {key: state.projections[key] for key in sorted(state.projections)},
        "projectionRevocations": {key: state.projection_revocations[key] for key in sorted(state.projection_revocations)},
        "privacyBoundaries": {key: state.privacy_boundaries[key] for key in sorted(state.privacy_boundaries)},
        "hplRequests": {key: state.hpl_requests[key] for key in sorted(state.hpl_requests)},
        "hplAuthorizations": {key: state.hpl_authorizations[key] for key in sorted(state.hpl_authorizations)},
        "evaluations": {key: state.evaluations[key] for key in sorted(state.evaluations)},
        "query": state.last_query,
    }


def evaluate_records(records: Iterable[dict[str, Any]], initial_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reduce records atomically and return state at the accepted prefix."""
    state = State()
    if initial_state:
        for model in initial_state.get("models", []):
            item = copy.deepcopy(model)
            _rank(item.get("privacyClass"))
            item.setdefault("effectivePrivacyClass", item["privacyClass"])
            if item["effectivePrivacyClass"] != _join([
                item["privacyClass"],
                *(next((candidate.get("effectivePrivacyClass", candidate.get("privacyClass", "PERSONAL")) for candidate in initial_state.get("models", []) if candidate.get("modelId") == ref), "PERSONAL") for ref in item.get("inputModelIds", [])),
            ]):
                return {"decision": "REJECT", "error": {"code": "PRIVACY_EFFECTIVE_CLASS_MISMATCH", "eventIndex": -1}, "state": _state_output(state)}
            item.setdefault("lifecycleStatus", "ACCEPTED")
            state.models[item["modelId"]] = item
    for index, record in enumerate(records):
        try:
            event = _event_from_verified(record)
            candidate = copy.deepcopy(state)
            _apply(candidate, event)
            state = candidate
        except SemanticError as error:
            return {
                "decision": "REJECT",
                "error": {"code": error.code, "eventId": record.get("body_cid") or (record.get("semantic_event") or {}).get("eventId"), "eventIndex": index},
                "state": _state_output(state),
            }
        except (KeyError, TypeError, OverflowError):
            return {
                "decision": "REJECT",
                "error": {"code": "PAYLOAD_FIELD_INVALID", "eventId": record.get("body_cid") or (record.get("semantic_event") or {}).get("eventId"), "eventIndex": index},
                "state": _state_output(state),
            }
    return {"decision": "ACCEPT", "state": _state_output(state)}


def evaluate_source(source: VerifiedRecordSource) -> dict[str, Any]:
    """Read the complete verified source before performing any semantic work."""
    return evaluate_records(source.records())


ERROR_ALIASES = {
    "MALFORMED_PAYLOAD": "PAYLOAD_FIELD_INVALID",
    "INVALID_EVENT_ENVELOPE": "PAYLOAD_ENVELOPE_INVALID",
    "INVALID_VALIDITY_INTERVAL": "PAYLOAD_ENVELOPE_INVALID",
    "DUPLICATE_EVENT_ID": "IDENTIFIER_CONFLICT",
    "EVIDENCE_ALREADY_EXISTS": "IDENTIFIER_CONFLICT",
    "MODEL_ALREADY_EXISTS": "IDENTIFIER_CONFLICT",
    "EVIDENCE_REFERENCE_NOT_FOUND": "REFERENCE_NOT_FOUND",
    "MODEL_NOT_FOUND": "REFERENCE_NOT_FOUND",
    "CONTRADICTION_NOT_FOUND": "REFERENCE_NOT_FOUND",
    "CONTRADICTION_INPUT_NOT_FOUND": "REFERENCE_NOT_FOUND",
    "TOPOLOGY_ENDPOINT_NOT_FOUND": "REFERENCE_NOT_FOUND",
    "DEPENDENCY_CYCLE": "TOPOLOGY_CYCLE",
    "POSSIBLE_WORLD_SCOPE_VIOLATION": "WORLD_SCOPE_VIOLATION",
    "MODEL_CARDINALITY_VIOLATION": "FAMILY_KIND_NOT_ALLOWED",
    "UNKNOWN_MODEL_FAMILY": "FAMILY_KIND_NOT_ALLOWED",
    "UNKNOWN_MODEL_KIND": "FAMILY_KIND_NOT_ALLOWED",
    "QUERY_AUTHORITY_MISMATCH": "AUTHORITY_SCOPE_VIOLATION",
    "AUTHORITY_BINDING_MISMATCH": "AUTHORITY_SCOPE_VIOLATION",
    "REVIEW_AUTHORITY_MISMATCH": "AUTHORITY_SCOPE_VIOLATION",
}


def _normalized_error(code: str) -> str:
    return ERROR_ALIASES.get(code, code)


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"$bytes_hex": value.hex()}
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _state_digest(state: dict[str, Any]) -> str:
    return hashlib.sha256(b"pwm:semantic-state:v1\0" + pwm_oracle.encode(state)).hexdigest()


def _validate_source(source: Any) -> dict[str, Any]:
    _exact(source, ("source_version", "source_id", "profile", "trust_anchor", "bundle", "command"))
    if source["source_version"] != SCHEMA_VERSION or source["profile"] != PROFILE:
        raise SemanticError("SOURCE_SCHEMA_INVALID")
    _exact(source["trust_anchor"], ("key_id", "public_key_hex"))
    if type(source["bundle"]) is not dict or type(source["command"]) is not dict:
        raise SemanticError("SOURCE_SCHEMA_INVALID")
    if type(source["source_id"]) is not str or not 1 <= len(source["source_id"].encode("utf-8")) <= 256:
        raise SemanticError("SOURCE_SCHEMA_INVALID")
    try:
        anchor_key = bytes.fromhex(source["trust_anchor"]["public_key_hex"])
    except (TypeError, ValueError) as error:
        raise SemanticError("SOURCE_SCHEMA_INVALID") from error
    if len(anchor_key) != 32 or source["trust_anchor"]["public_key_hex"] != anchor_key.hex():
        raise SemanticError("SOURCE_SCHEMA_INVALID")
    bundle = source["bundle"]
    _exact(bundle, ("profile", "appender_key_id", "appender_public_key_hex", "author_keys", "schemas", "records"))
    if bundle["profile"] != "pwm-public-provenance-v1" or not all(type(bundle[name]) is list and bundle[name] for name in ("author_keys", "schemas", "records")):
        raise SemanticError("SOURCE_SCHEMA_INVALID")
    for key in bundle["author_keys"]:
        _exact(key, ("key_id", "public_key_hex", "active_from_log_sequence", "revoked_at_log_sequence"))
        try:
            public_key = bytes.fromhex(key["public_key_hex"])
        except (TypeError, ValueError) as error:
            raise SemanticError("SOURCE_SCHEMA_INVALID") from error
        if len(public_key) != 32 or key["public_key_hex"] != public_key.hex() or type(key["active_from_log_sequence"]) is not int or key["active_from_log_sequence"] < 0:
            raise SemanticError("SOURCE_SCHEMA_INVALID")
        if key["revoked_at_log_sequence"] is not None and (type(key["revoked_at_log_sequence"]) is not int or key["revoked_at_log_sequence"] < 0):
            raise SemanticError("SOURCE_SCHEMA_INVALID")
    for registration in bundle["schemas"]:
        _exact(registration, ("event_kind", "schema_version"))
        if not all(type(registration[name]) is str and registration[name] for name in registration):
            raise SemanticError("SOURCE_SCHEMA_INVALID")
    for record in bundle["records"]:
        _exact(record, ("body_cbor_hex", "body_cid", "event_signature_hex", "payload_cbor_hex", "receipt_body_cbor_hex", "receipt_cid", "receipt_signature_hex"))
        if any(type(value) is not str or not value for value in record.values()):
            raise SemanticError("SOURCE_SCHEMA_INVALID")
    operation = source["command"].get("operation")
    required = {"operation", "evaluation_log_sequence"}
    optional = {"query", "projection_id", "evaluation_id"}
    if set(source["command"]) - required - optional or not required.issubset(source["command"]):
        raise SemanticError("SOURCE_SCHEMA_INVALID")
    if operation not in {"REDUCE", "QUERY", "PROJECT", "EVALUATE"} or type(source["command"]["evaluation_log_sequence"]) is not int or source["command"]["evaluation_log_sequence"] < 0:
        raise SemanticError("SOURCE_SCHEMA_INVALID")
    expected_extra = {"QUERY": "query", "PROJECT": "projection_id", "EVALUATE": "evaluation_id"}.get(operation)
    actual_extra = set(source["command"]).intersection(optional)
    if actual_extra != ({expected_extra} if expected_extra else set()):
        raise SemanticError("SOURCE_SCHEMA_INVALID")
    return source


def _command_value(state: dict[str, Any], command: dict[str, Any]) -> Any:
    operation = command["operation"]
    if operation == "REDUCE":
        return _json_safe(state)
    if operation == "PROJECT":
        projection = state["projections"].get(command["projection_id"])
        if projection is None:
            raise SemanticError("REFERENCE_NOT_FOUND")
        return _json_safe(projection)
    if operation == "EVALUATE":
        evaluation = state["evaluations"].get(command["evaluation_id"])
        if evaluation is None:
            raise SemanticError("REFERENCE_NOT_FOUND")
        return _json_safe(evaluation)
    query = command["query"]
    _exact(query, ("authority_id", "world_id", "as_of_valid_ns", "recipient_id", "purpose", "model_ids", "include_disputed"))
    authority = state["queryAuthorities"].get(query["authority_id"])
    if authority is None:
        raise SemanticError("REFERENCE_NOT_FOUND")
    sequence = command["evaluation_log_sequence"]
    if not authority["valid_from_log_sequence"] <= sequence or (authority["valid_to_log_sequence"] is not None and sequence >= authority["valid_to_log_sequence"]):
        raise SemanticError("AUTHORITY_EXPIRED")
    if query["recipient_id"] != authority["recipient_id"] or query["purpose"] != authority["purpose"] or query["world_id"] not in authority["world_ids"]:
        raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
    selected = []
    for model_id in sorted(query["model_ids"], key=lambda item: item.encode("utf-8")):
        model = state["models"].get(model_id)
        if model is None:
            raise SemanticError("REFERENCE_NOT_FOUND")
        if model.get("worldId", "world:actual") != query["world_id"]:
            raise SemanticError("WORLD_SCOPE_VIOLATION")
        if model["lifecycleStatus"] == "DISPUTED" and not (query["include_disputed"] and authority["allow_disputed"]):
            continue
        if model["lifecycleStatus"] != "ACCEPTED" and model["lifecycleStatus"] != "DISPUTED":
            continue
        if not set(model.get("subjectIds", [])).issubset(authority["subject_ids"]) or model["familyId"] not in authority["families"] or model.get("perspective") not in authority["perspective_ids"]:
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        if not (model.get("validFrom") is None or model["validFrom"] <= query["as_of_valid_ns"]) or not (model.get("validTo") is None or query["as_of_valid_ns"] < model["validTo"]):
            continue
        if _rank(model["effectivePrivacyClass"]) > _rank(authority["privacy_ceiling"]):
            raise SemanticError("AUTHORITY_SCOPE_VIOLATION")
        selected.append(model_id)
    selected_set = set(selected)
    edge_ids = sorted(key for key, edge in state["edges"].items() if {edge["sourceModelId"], edge["targetModelId"]}.issubset(selected_set))
    return {"model_ids": selected, "edge_ids": edge_ids}


def _output(source_id: str, result: dict[str, Any], records: list[dict[str, Any]], command: dict[str, Any]) -> dict[str, Any]:
    accepted = len(result["state"]["acceptedEventIds"])
    output: dict[str, Any] = {
        "output_version": SCHEMA_VERSION,
        "profile": PROFILE,
        "source_id": source_id,
        "implementation": {"id": IMPLEMENTATION, "version": "1.0.0", "adapter_version": "1.0.0"},
        "decision": result["decision"],
        "processed_records": accepted,
        "last_committed_log_sequence": records[accepted - 1]["log_sequence"] if accepted else None,
        "state_sha256": _state_digest(result["state"]),
    }
    if result["decision"] == "REJECT":
        error = {"code": _normalized_error(result["error"]["code"])}
        index = result["error"].get("eventIndex")
        if type(index) is int and 0 <= index < len(records):
            error["at_event_body_cid"] = records[index]["body_cid"]
        output["error"] = error
        return output
    try:
        value = _command_value(result["state"], command)
    except SemanticError as error:
        output["decision"] = "REJECT"
        output["error"] = {"code": _normalized_error(error.code)}
        return output
    output["result"] = {"operation": command["operation"], "state_sha256": _state_digest(result["state"]), "value": value}
    return output


def evaluate_bundle(path: Path | str) -> dict[str, Any]:
    try:
        source = _validate_source(json.loads(Path(path).read_text(encoding="utf-8")))
    except Exception:
        return _output("invalid-source", {"decision": "REJECT", "error": {"code": "SOURCE_SCHEMA_INVALID"}, "state": _state_output(State())}, [], {"operation": "REDUCE", "evaluation_log_sequence": 0})
    try:
        records = pwm_oracle.verify_bundle_object(source["bundle"])
    except Exception as error:
        message = str(error).lower()
        code = (
            "SIGNATURE_INVALID" if "signature" in message
            else "AUTHOR_SEQUENCE_INVALID" if "author predecessor" in message or "author sequence" in message
            else "PARENT_INVALID" if "parent" in message or "genesis" in message
            else "CID_MISMATCH" if "mismatch" in message
            else "CBOR_INVALID"
        )
        return _output(source["source_id"], {"decision": "REJECT", "error": {"code": code}, "state": _state_output(State())}, [], source["command"])
    anchor = source["trust_anchor"]
    keys = {item["key_id"]: item["public_key_hex"] for item in source["bundle"].get("author_keys", [])}
    if keys.get(anchor["key_id"]) != anchor["public_key_hex"] or not records or records[0]["body"].get("event_kind") != "pwm.genesis" or records[0]["body"].get("author_key_id") != anchor["key_id"]:
        return _output(source["source_id"], {"decision": "REJECT", "error": {"code": "ROOT_TRUST_MISMATCH", "eventIndex": 0}, "state": _state_output(State())}, records, source["command"])
    frontier = source["command"]["evaluation_log_sequence"]
    selected = [record for record in records if record["log_sequence"] <= frontier]
    return _output(source["source_id"], evaluate_records(selected), selected, source["command"])


def canonical_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False)


def identify() -> dict[str, Any]:
    return {
        "implementation": IMPLEMENTATION,
        "profiles": ["pwm-public-provenance-v1", PROFILE],
        "protocolVersion": "1.0.0",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = commands.add_parser("evaluate")
    evaluate_parser.add_argument("--bundle", required=True, type=Path)
    commands.add_parser("identify")
    arguments = parser.parse_args(argv)
    if arguments.command == "identify":
        print(canonical_json(identify()))
        return 0
    result = evaluate_bundle(arguments.bundle)
    print(canonical_json(result))
    return 0 if result["decision"] == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
