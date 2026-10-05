"""Experimental HPL platform contracts.

This module composes the existing :class:`authority.Decision` as evidence.  It
does not define a second authority engine and none of its records can mutate
canonical V2 state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .authority import Decision
from .canonical import sha256_urn
from .schema_validation import validate_record
from .privacy import privacy_rank


NEGOTIATION_STATUSES = frozenset(
    {
        "GRANTED",
        "DENIED",
        "UNAVAILABLE",
        "REDACTED",
        "TRANSFORMED",
        "DERIVED",
        "REQUIRES_CONSENT",
    }
)
TERMINAL_STATES = frozenset({"REVOKED", "EXPIRED", "REFUSED", "DEPARTED"})
LIFECYCLE_TRANSITIONS = {
    "REQUESTED": frozenset({"NEGOTIATED", "REVOKED", "EXPIRED"}),
    "NEGOTIATED": frozenset({"ISSUED", "REVOKED", "EXPIRED"}),
    "ISSUED": frozenset({"ACTIVE", "REVOKED", "EXPIRED"}),
    "ACTIVE": frozenset({"EXECUTED", "REFUSED", "REVOKED", "EXPIRED"}),
    "EXECUTED": frozenset({"DEPARTED", "REVOKED", "EXPIRED"}),
}


class HPLContractError(ValueError):
    """A stable, fail-closed contract error suitable for protocol responses."""

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "retryable": self.retryable}


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise HPLContractError("INVALID_TIME", f"invalid RFC 3339 timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise HPLContractError("INVALID_TIME", "timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _now(value: str | None) -> datetime:
    return _parse_time(value) if value else datetime.now(timezone.utc)


def _identified(namespace: str, id_field: str, body: dict[str, Any]) -> dict[str, Any]:
    return {id_field: sha256_urn(namespace, body), **body}


def content_id_matches(record: dict[str, Any], id_field: str, namespace: str) -> bool:
    body = {key: value for key, value in record.items() if key != id_field}
    return record.get(id_field) == sha256_urn(namespace, body)


def request_digest(request: dict[str, Any]) -> str:
    """Digest every request field except its derived identifier."""

    validate_record("projection-request.schema.json", request)
    if not content_id_matches(request, "requestId", "hpl:request"):
        raise HPLContractError("REQUEST_ID_MISMATCH", "requestId is not derived from request content")
    return sha256_urn("hpl:request-digest", request)


def make_projection_request(
    *,
    requester: str,
    recipient: str,
    target_profile_id: str,
    purpose: str,
    capability: str,
    requested_fields: Iterable[str],
    issued_at: str,
    expires_at: str,
    max_privacy_class: str = "PERSONAL",
    consent_evidence: Iterable[str] = (),
) -> dict[str, Any]:
    if _parse_time(expires_at) <= _parse_time(issued_at):
        raise HPLContractError("INVALID_EXPIRY", "request expiry must follow issue time")
    privacy_rank(max_privacy_class)
    body = {
        "requester": requester,
        "recipient": recipient,
        "targetProfileId": target_profile_id,
        "purpose": purpose,
        "capability": capability,
        "requestedFields": sorted(set(requested_fields)),
        "issuedAt": issued_at,
        "expiresAt": expires_at,
        "maxPrivacyClass": max_privacy_class,
        "consentEvidence": sorted(set(consent_evidence)),
        "canonicalV2Effect": "NONE",
    }
    record = _identified("hpl:request", "requestId", body)
    validate_record("projection-request.schema.json", record)
    return record


def make_target_profile(
    *, target_class: str, recipient: str, capabilities: Iterable[dict[str, Any]], profile_version: str = "0.1.0"
) -> dict[str, Any]:
    body = {
        "profileVersion": profile_version,
        "targetClass": target_class,
        "recipient": recipient,
        "illustrative": True,
        "capabilities": list(capabilities),
        "canonicalV2Effect": "NONE",
    }
    record = _identified("hpl:target-profile", "targetProfileId", body)
    validate_record("hpl-target-profile.schema.json", record)
    return record


def target_profile_digest(target_profile: dict[str, Any]) -> str:
    validate_record("hpl-target-profile.schema.json", target_profile)
    body = {key: value for key, value in target_profile.items() if key != "targetProfileId"}
    return sha256_urn("hpl:target-profile-content", body)


def make_capability_manifest(
    *,
    target_id: str,
    recipient: str,
    target_profile_id: str,
    target_profile_digest: str,
    capabilities: Iterable[dict[str, Any]],
    discovered_at: str,
    expires_at: str,
) -> dict[str, Any]:
    if _parse_time(expires_at) <= _parse_time(discovered_at):
        raise HPLContractError("INVALID_EXPIRY", "manifest expiry must follow discovery time")
    body = {
        "targetId": target_id,
        "recipient": recipient,
        "targetProfileId": target_profile_id,
        "targetProfileDigest": target_profile_digest,
        "discoveredAt": discovered_at,
        "expiresAt": expires_at,
        "capabilities": list(capabilities),
        "canonicalV2Effect": "NONE",
    }
    record = _identified("hpl:capability-manifest", "manifestId", body)
    validate_record("capability-manifest.schema.json", record)
    return record


def discover_capabilities(
    target_profile: dict[str, Any], capability_manifest: dict[str, Any], *, at: str | None = None
) -> tuple[dict[str, Any], ...]:
    """Return advertised capabilities after validating profile identity and freshness."""

    validate_record("hpl-target-profile.schema.json", target_profile)
    validate_record("capability-manifest.schema.json", capability_manifest)
    if not content_id_matches(capability_manifest, "manifestId", "hpl:capability-manifest"):
        raise HPLContractError("MANIFEST_ID_MISMATCH", "manifestId is not derived from manifest content")
    if capability_manifest["targetProfileId"] != target_profile["targetProfileId"]:
        raise HPLContractError("PROFILE_MISMATCH", "manifest is bound to a different target profile")
    if capability_manifest["recipient"] != target_profile["recipient"]:
        raise HPLContractError("RECIPIENT_MISMATCH", "manifest recipient differs from target profile")
    expected_profile_digest = target_profile_digest(target_profile)
    if capability_manifest["targetProfileDigest"] != expected_profile_digest:
        raise HPLContractError("PROFILE_DIGEST_MISMATCH", "target profile content differs from the advertised digest")
    observation_time = _now(at)
    if _parse_time(capability_manifest["expiresAt"]) <= _parse_time(capability_manifest["discoveredAt"]):
        raise HPLContractError("INVALID_EXPIRY", "manifest expiry must follow discovery time")
    if observation_time < _parse_time(capability_manifest["discoveredAt"]):
        raise HPLContractError("MANIFEST_NOT_YET_VALID", "manifest discovery time is in the future")
    if observation_time >= _parse_time(capability_manifest["expiresAt"]):
        raise HPLContractError("MANIFEST_EXPIRED", "capability discovery manifest has expired", retryable=True)
    declared = {item["capabilityId"] for item in target_profile["capabilities"]}
    advertised = capability_manifest["capabilities"]
    if any(item["capabilityId"] not in declared for item in advertised):
        raise HPLContractError("UNDECLARED_CAPABILITY", "manifest advertises a capability absent from its profile")
    return tuple(advertised)


def _authority_evidence(decision: Decision) -> dict[str, Any]:
    return {
        "requested": sorted(decision.requested),
        "allowed": sorted(decision.allowed),
        "denied": sorted(decision.denied),
        "reasons": list(decision.reasons),
        "grantingPrincipals": list(decision.granting_principals),
        "denyingPrincipals": list(decision.denying_principals),
        "grantSources": [
            {"capability": capability, "principal": principal}
            for capability, principal in decision.grant_sources
        ],
        "denySources": [
            {"capability": capability, "principal": principal}
            for capability, principal in decision.deny_sources
        ],
    }


@dataclass(frozen=True)
class BoundAuthorityDecision:
    """An existing authority decision bound to one exact HPL request."""

    request_digest: str
    decision: Decision
    evidence_refs: tuple[str, ...] = ()


def bind_authority(
    request: dict[str, Any], decision: Decision, evidence_refs: Iterable[str] = ()
) -> BoundAuthorityDecision:
    if decision.requested != frozenset({request["capability"]}):
        raise HPLContractError(
            "AUTHORITY_BINDING_MISMATCH", "Decision is not bound to the exact capability"
        )
    digest = request_digest(request)
    if decision.binding_ref != digest:
        raise HPLContractError(
            "AUTHORITY_BINDING_MISMATCH",
            "Decision was not resolved for this request digest",
        )
    if request["capability"] in decision.allowed and (request["capability"], request["requester"]) not in decision.grant_sources:
        raise HPLContractError(
            "AUTHORITY_PRINCIPAL_MISMATCH",
            "requesting principal is not among the capability-granting principals",
        )
    return BoundAuthorityDecision(digest, decision, tuple(sorted(set(evidence_refs))))


def negotiate(
    request: dict[str, Any],
    target_profile: dict[str, Any],
    capability_manifest: dict[str, Any],
    authority: BoundAuthorityDecision,
    mapping_evidence: Iterable[dict[str, Any]],
    *,
    negotiated_at: str,
) -> dict[str, Any]:
    """Negotiate one exactly-bound capability using an existing Decision as evidence."""

    digest = request_digest(request)
    if authority.request_digest != digest:
        raise HPLContractError(
            "AUTHORITY_BINDING_MISMATCH", "authority evidence is bound to a different request"
        )
    decision = authority.decision
    if decision.binding_ref != digest:
        raise HPLContractError("AUTHORITY_BINDING_MISMATCH", "Decision binding does not match the request")
    if request["capability"] in decision.allowed and (request["capability"], request["requester"]) not in decision.grant_sources:
        raise HPLContractError(
            "AUTHORITY_PRINCIPAL_MISMATCH",
            "requesting principal is not among the capability-granting principals",
        )
    capabilities = discover_capabilities(target_profile, capability_manifest, at=negotiated_at)
    now = _parse_time(negotiated_at)
    if now < _parse_time(request["issuedAt"]) or now >= _parse_time(request["expiresAt"]):
        raise HPLContractError("REQUEST_EXPIRED", "projection request is not valid at negotiation time")
    if request["recipient"] != target_profile["recipient"]:
        raise HPLContractError("RECIPIENT_MISMATCH", "request recipient differs from target profile")
    if request["targetProfileId"] != target_profile["targetProfileId"]:
        raise HPLContractError("PROFILE_MISMATCH", "request names a different target profile")
    if decision.requested != frozenset({request["capability"]}):
        raise HPLContractError("AUTHORITY_BINDING_MISMATCH", "Decision is not bound to the exact capability")

    profile_capabilities = {item["capabilityId"]: item for item in target_profile["capabilities"]}
    manifest_capabilities = {item["capabilityId"]: item for item in capabilities}
    profile_capability = profile_capabilities.get(request["capability"])
    manifest_capability = manifest_capabilities.get(request["capability"])
    reason = "capability and fields satisfy the bounded request"
    error = None
    granted_fields: list[str] = []
    requested_fields = set(request["requestedFields"])

    if profile_capability is None or manifest_capability is None or not manifest_capability["available"]:
        status = "UNAVAILABLE"
        reason = "recipient does not currently advertise the requested capability"
        error = {"code": "CAPABILITY_UNAVAILABLE", "message": reason, "retryable": True}
    elif request["purpose"] not in profile_capability["purposes"]:
        status = "DENIED"
        reason = "purpose is outside the capability profile"
        error = {"code": "PURPOSE_NOT_SUPPORTED", "message": reason, "retryable": False}
    elif request["capability"] not in decision.allowed:
        status = "DENIED"
        reason = "existing authority Decision did not grant the exact capability"
        error = {"code": "AUTHORITY_DENIED", "message": reason, "retryable": False}
    elif profile_capability["consentRequired"] and not request["consentEvidence"]:
        status = "REQUIRES_CONSENT"
        reason = "profile requires explicit consent evidence"
        error = {"code": "CONSENT_REQUIRED", "message": reason, "retryable": True}
    else:
        allowed_fields = (
            set(profile_capability["requiredFields"])
            | set(profile_capability["optionalFields"])
        ) & set(manifest_capability["inputFields"])
        denied_fields = set(profile_capability["deniedFields"])
        granted_fields = sorted(requested_fields & allowed_fields - denied_fields)
        missing_required = set(profile_capability["requiredFields"]) - set(granted_fields)
        if missing_required:
            status = "DENIED"
            reason = f"required fields were not granted: {sorted(missing_required)}"
            error = {"code": "REQUIRED_FIELD_MISSING", "message": reason, "retryable": False}
        elif requested_fields - set(granted_fields):
            status = "REDACTED"
            reason = "request granted with fields outside profile policy redacted"
        elif profile_capability["representation"] == "TRANSFORMED":
            status = "TRANSFORMED"
            reason = "recipient receives only the declared transformed representation"
        elif profile_capability["representation"] == "DERIVED":
            status = "DERIVED"
            reason = "recipient receives only the declared derived representation"
        else:
            status = "GRANTED"

    evidence = list(mapping_evidence)
    if status in {"GRANTED", "REDACTED", "TRANSFORMED", "DERIVED"} and not evidence:
        raise HPLContractError("MAPPING_EVIDENCE_REQUIRED", "successful negotiation requires mapping evidence")
    mapped_fields = {item.get("targetField") for item in evidence}
    if status in {"GRANTED", "REDACTED", "TRANSFORMED", "DERIVED"} and set(granted_fields) - mapped_fields:
        raise HPLContractError("MAPPING_EVIDENCE_INCOMPLETE", "every granted field requires mapping evidence")
    denied_fields = sorted(requested_fields - set(granted_fields))
    body = {
        "requestId": request["requestId"],
        "requestDigest": digest,
        "recipient": request["recipient"],
        "targetProfileId": request["targetProfileId"],
        "capability": request["capability"],
        "purpose": request["purpose"],
        "maxPrivacyClass": request["maxPrivacyClass"],
        "status": status,
        "grantedFields": granted_fields,
        "deniedFields": denied_fields,
        "negotiatedAt": negotiated_at,
        "expiresAt": min(
            (request["expiresAt"], capability_manifest["expiresAt"]), key=_parse_time
        ),
        "authorityEvidence": {
            **_authority_evidence(decision),
            "requestDigest": authority.request_digest,
            "evidenceRefs": list(authority.evidence_refs),
        },
        "mappingEvidence": evidence,
        "reason": reason,
        "canonicalV2Effect": "NONE",
    }
    if error is not None:
        body["error"] = error
    record = _identified("hpl:negotiation", "negotiationId", body)
    validate_record("capability-negotiation.schema.json", record)
    return record


def make_bounded_projection(
    negotiation: dict[str, Any],
    fields: dict[str, Any],
    *,
    issued_at: str,
    field_sources: dict[str, dict[str, Any]],
    refresh_policy: str = "ON_CHANGE",
    onward_sharing: str = "PROHIBITED",
    revocation_ref: str | None = None,
) -> dict[str, Any]:
    """Create the minimum recipient-bound artifact authorized by a negotiation."""
    validate_record("capability-negotiation.schema.json", negotiation)
    if negotiation["status"] not in {"GRANTED", "REDACTED", "TRANSFORMED", "DERIVED"}:
        raise HPLContractError("NEGOTIATION_NOT_ISSUABLE", "negotiation cannot produce a projection")
    if set(fields) != set(negotiation["grantedFields"]):
        raise HPLContractError("FIELD_SET_MISMATCH", "projection fields must exactly equal the negotiated grant")
    if set(field_sources) != set(fields):
        raise HPLContractError("PRIVACY_LABEL_MISMATCH", "every projection field requires a source record")
    field_privacy = {
        field: source.get("effectivePrivacyClass", source.get("privacyClass"))
        for field, source in field_sources.items()
    }
    if any(value is None for value in field_privacy.values()):
        raise HPLContractError("PRIVACY_LABEL_MISMATCH", "source records require effective privacy")
    sensitivity = max(field_privacy.values(), key=privacy_rank) if field_privacy else "PUBLIC"
    if privacy_rank(sensitivity) > privacy_rank(negotiation["maxPrivacyClass"]):
        raise HPLContractError("PRIVACY_CEILING_EXCEEDED", "projection source exceeds the negotiated privacy ceiling")
    mapping_refs = {
        field: {
            ref for mapping in negotiation["mappingEvidence"]
            if mapping["targetField"] == field
            for ref in mapping["provenanceRefs"]
        }
        for field in fields
    }
    for field, source in field_sources.items():
        source_refs = set(source.get("provenanceRefs", ()))
        if not source_refs or not source_refs.intersection(mapping_refs[field]):
            raise HPLContractError(
                "SOURCE_PROVENANCE_MISMATCH",
                f"field {field} is not bound to negotiated mapping provenance",
            )
    if not (_parse_time(negotiation["negotiatedAt"]) <= _parse_time(issued_at) < _parse_time(negotiation["expiresAt"])):
        raise HPLContractError("INVALID_ISSUE_TIME", "projection issue time is outside negotiation validity")
    body = {
        "negotiationId": negotiation["negotiationId"],
        "requestId": negotiation["requestId"],
        "recipient": negotiation["recipient"],
        "purpose": negotiation["purpose"],
        "capability": negotiation["capability"],
        "targetProfileId": negotiation["targetProfileId"],
        "issuedAt": issued_at,
        "expiresAt": negotiation["expiresAt"],
        "refreshPolicy": refresh_policy,
        "revocationRef": revocation_ref,
        "allowedUse": negotiation["purpose"],
        "onwardSharing": onward_sharing,
        "sensitivity": sensitivity,
        "fields": fields,
        "fieldPrivacy": field_privacy,
        "provenanceRefs": sorted({
            negotiation["negotiationId"],
            *negotiation["authorityEvidence"].get("evidenceRefs", []),
            *(ref for mapping in negotiation["mappingEvidence"] for ref in mapping["provenanceRefs"]),
            *(ref for source in field_sources.values() for ref in source["provenanceRefs"]),
        }),
        "canonicalV2Effect": "NONE",
    }
    record = _identified("hpl:bounded-projection", "projectionId", body)
    validate_record("hpl-bounded-projection.schema.json", record)
    return record


def make_lifecycle_event(
    negotiation_id: str,
    event_type: str,
    from_state: str,
    to_state: str,
    at: str,
    evidence: Iterable[str] = (),
) -> dict[str, Any]:
    body = {
        "negotiationId": negotiation_id,
        "eventType": event_type,
        "fromState": from_state,
        "toState": to_state,
        "at": at,
        "evidence": sorted(set(evidence)),
        "canonicalV2Effect": "NONE",
    }
    record = _identified("hpl:lifecycle-event", "eventId", body)
    validate_record("hpl-lifecycle-event.schema.json", record)
    return record


@dataclass
class HPLLifecycle:
    """Small deterministic state machine for one negotiation."""

    negotiation: dict[str, Any]

    def __post_init__(self) -> None:
        validate_record("capability-negotiation.schema.json", self.negotiation)
        self.state = "REQUESTED"
        self.events: list[dict[str, Any]] = []
        self.transition("NEGOTIATED", self.negotiation["negotiatedAt"], [self.negotiation["negotiationId"]])

    def transition(self, to_state: str, at: str, evidence: Iterable[str] = ()) -> dict[str, Any]:
        if to_state not in LIFECYCLE_TRANSITIONS.get(self.state, frozenset()):
            raise HPLContractError(
                "INVALID_LIFECYCLE_TRANSITION", f"cannot transition from {self.state} to {to_state}"
            )
        if to_state == "ISSUED" and self.negotiation["status"] not in {
            "GRANTED", "REDACTED", "TRANSFORMED", "DERIVED"
        }:
            raise HPLContractError("NEGOTIATION_NOT_ISSUABLE", "denied or incomplete negotiation cannot be issued")
        transition_time = _parse_time(at)
        if self.events and transition_time < _parse_time(self.events[-1]["at"]):
            raise HPLContractError("NON_MONOTONIC_LIFECYCLE", "lifecycle event time moved backwards")
        if transition_time >= _parse_time(self.negotiation["expiresAt"]) and to_state != "EXPIRED":
            raise HPLContractError("NEGOTIATION_EXPIRED", "expired negotiation may only transition to EXPIRED")
        event = make_lifecycle_event(
            self.negotiation["negotiationId"], to_state, self.state, to_state, at, evidence
        )
        self.events.append(event)
        self.state = to_state
        return event

    def revoke(self, reason: str, revoked_by: str, at: str) -> dict[str, Any]:
        if self.state in TERMINAL_STATES:
            raise HPLContractError("ALREADY_TERMINAL", f"cannot revoke lifecycle in {self.state}")
        previous = self.state
        event = self.transition("REVOKED", at, [self.negotiation["requestId"]])
        body = {
            "negotiationId": self.negotiation["negotiationId"],
            "requestId": self.negotiation["requestId"],
            "revokedBy": revoked_by,
            "revokedAt": at,
            "reason": reason,
            "previousState": previous,
            "lifecycleEventId": event["eventId"],
            "canonicalV2Effect": "NONE",
        }
        record = _identified("hpl:revocation", "revocationId", body)
        validate_record("revocation-record.schema.json", record)
        return record
