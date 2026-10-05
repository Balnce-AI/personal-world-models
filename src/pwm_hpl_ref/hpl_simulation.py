"""Non-actuating foreign-runtime simulator for experimental HPL contracts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .canonical import sha256_urn
from .hpl_contracts import HPLContractError, content_id_matches, request_digest
from .schema_validation import validate_record


SafetyPolicy = Callable[[str, dict[str, Any]], tuple[bool, str]]


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise HPLContractError("INVALID_TIME", "timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _identified(namespace: str, id_field: str, body: dict[str, Any]) -> dict[str, Any]:
    return {id_field: sha256_urn(namespace, body), **body}


class ForeignRuntimeSimulator:
    """A recipient with no PWM/PLog handles and an independent local veto."""

    def __init__(self, recipient: str, safety_policy: SafetyPolicy | None = None):
        self.recipient = recipient
        self._safety_policy = safety_policy or (lambda _capability, _payload: (True, "local checks passed"))
        self._revoked: set[str] = set()

    def apply_revocation(self, revocation: dict[str, Any]) -> None:
        validate_record("revocation-record.schema.json", revocation)
        if not content_id_matches(revocation, "revocationId", "hpl:revocation"):
            raise HPLContractError("REVOCATION_ID_MISMATCH", "revocation record content does not match its ID")
        self._revoked.add(revocation["negotiationId"])

    def evaluate_safety(
        self, negotiation: dict[str, Any], payload: dict[str, Any], *, at: str
    ) -> dict[str, Any]:
        permitted, reason = self._safety_policy(negotiation["capability"], payload)
        body = {
            "negotiationId": negotiation["negotiationId"],
            "recipient": self.recipient,
            "capability": negotiation["capability"],
            "decision": "ALLOW" if permitted else "VETO",
            "reason": reason,
            "decidedAt": at,
            "independentLocalAuthority": True,
            "safetyCertification": "NOT_CLAIMED",
            "canonicalV2Effect": "NONE",
        }
        record = _identified("hpl:local-safety", "decisionId", body)
        validate_record("local-safety-decision.schema.json", record)
        return record

    def _evaluate_unbound(
        self,
        request: dict[str, Any],
        negotiation: dict[str, Any],
        payload: dict[str, Any],
        *,
        at: str,
        online: bool = True,
        compromised_device_assumed: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Evaluate dispatch without actuating; all failures become REFUSED records."""

        validate_record("projection-request.schema.json", request)
        validate_record("capability-negotiation.schema.json", negotiation)
        reasons: list[str] = []
        try:
            digest = request_digest(request)
        except HPLContractError as error:
            digest = None
            reasons.append(error.code)
        if not content_id_matches(negotiation, "negotiationId", "hpl:negotiation"):
            reasons.append("NEGOTIATION_ID_MISMATCH")
        if negotiation["recipient"] != self.recipient or request["recipient"] != self.recipient:
            reasons.append("RECIPIENT_MISMATCH")
        if negotiation["requestId"] != request["requestId"] or negotiation["requestDigest"] != digest:
            reasons.append("REQUEST_BINDING_MISMATCH")
        for key in ("targetProfileId", "capability", "purpose"):
            if negotiation[key] != request[key]:
                reasons.append(f"{key.upper()}_MISMATCH")
        if negotiation["status"] not in {"GRANTED", "REDACTED", "TRANSFORMED", "DERIVED"}:
            reasons.append(f"NEGOTIATION_{negotiation['status']}")
        if negotiation["negotiationId"] in self._revoked:
            reasons.append("REVOKED")
        if _time(at) >= _time(negotiation["expiresAt"]):
            reasons.append("EXPIRED")
        if not online and _time(at) >= _time(negotiation["expiresAt"]):
            reasons.append("OFFLINE_EXPIRY_FAIL_CLOSED")
        unknown_fields = set(payload) - set(negotiation["grantedFields"])
        if unknown_fields:
            reasons.append("FIELD_NOT_GRANTED")
        if compromised_device_assumed:
            reasons.append("COMPROMISED_DEVICE_ASSUMPTION")

        if reasons:
            safety = self._refusal_safety(negotiation, at, ", ".join(sorted(set(reasons))))
        else:
            safety = self.evaluate_safety(negotiation, payload, at=at)
            if safety["decision"] == "VETO":
                reasons.append("LOCAL_SAFETY_VETO")

        disposition = "WOULD_DISPATCH" if not reasons else "REFUSED"
        mapping_refs = {
            ref
            for mapping in negotiation["mappingEvidence"]
            for ref in mapping["provenanceRefs"]
        }
        outcome_body = {
            "negotiationId": negotiation["negotiationId"],
            "requestId": request["requestId"],
            "recipient": self.recipient,
            "capability": negotiation["capability"],
            "disposition": disposition,
            "reasonCodes": sorted(set(reasons)),
            "observedAt": at,
            "localSafetyDecisionId": safety["decisionId"],
            "provenanceRefs": sorted({negotiation["negotiationId"], safety["decisionId"], *mapping_refs}),
            "actuationPerformed": False,
            "gracefulDegradation": (
                "NOT_REQUIRED" if disposition == "WOULD_DISPATCH" else "NO_ACTUATION_RETAIN_CONTROL"
            ),
            "canonicalV2Effect": "NONE",
        }
        outcome = _identified("hpl:execution-outcome", "outcomeId", outcome_body)
        validate_record("execution-outcome.schema.json", outcome)
        return safety, outcome

    def execute_projection(
        self,
        request: dict[str, Any],
        negotiation: dict[str, Any],
        projection: dict[str, Any],
        lifecycle: Any,
        *,
        at: str,
        online: bool = True,
        compromised_device_assumed: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        validate_record("hpl-bounded-projection.schema.json", projection)
        if lifecycle.negotiation["negotiationId"] != negotiation["negotiationId"] or lifecycle.state != "ACTIVE":
            raise HPLContractError("LIFECYCLE_NOT_ACTIVE", "projection execution requires its ACTIVE lifecycle")
        if not content_id_matches(projection, "projectionId", "hpl:bounded-projection"):
            raise HPLContractError("PROJECTION_ID_MISMATCH", "projection content does not match its ID")
        for field in ("negotiationId", "requestId", "recipient", "purpose", "capability", "targetProfileId"):
            expected = negotiation[field] if field in negotiation else request[field]
            if projection[field] != expected:
                raise HPLContractError("PROJECTION_BINDING_MISMATCH", f"projection {field} mismatch")
        if set(projection["fields"]) != set(negotiation["grantedFields"]):
            raise HPLContractError("FIELD_SET_MISMATCH", "projection fields differ from the negotiated grant")
        if set(projection["fieldPrivacy"]) != set(projection["fields"]):
            raise HPLContractError("PRIVACY_LABEL_MISMATCH", "projection field privacy is incomplete")
        if projection["expiresAt"] != negotiation["expiresAt"]:
            raise HPLContractError("PROJECTION_BINDING_MISMATCH", "projection expiry differs from negotiation")
        if _time(at) < _time(projection["issuedAt"]):
            raise HPLContractError("PROJECTION_NOT_YET_VALID", "projection has not reached its issue time")
        safety, outcome = self._evaluate_unbound(
            request,
            negotiation,
            dict(projection["fields"]),
            at=at,
            online=online,
            compromised_device_assumed=compromised_device_assumed,
        )
        next_state = (
            "EXECUTED" if outcome["disposition"] == "WOULD_DISPATCH"
            else "EXPIRED" if "EXPIRED" in outcome["reasonCodes"]
            else "REFUSED"
        )
        lifecycle.transition(
            next_state,
            at,
            (projection["projectionId"], outcome["outcomeId"]),
        )
        return safety, outcome

    def _refusal_safety(self, negotiation: dict[str, Any], at: str, reason: str) -> dict[str, Any]:
        body = {
            "negotiationId": negotiation["negotiationId"],
            "recipient": self.recipient,
            "capability": negotiation["capability"],
            "decision": "VETO",
            "reason": reason,
            "decidedAt": at,
            "independentLocalAuthority": True,
            "safetyCertification": "NOT_CLAIMED",
            "canonicalV2Effect": "NONE",
        }
        record = _identified("hpl:local-safety", "decisionId", body)
        validate_record("local-safety-decision.schema.json", record)
        return record

    def acknowledge_departure(
        self, negotiation: dict[str, Any], *, at: str, assurance: str = "PROTOCOL_ACKNOWLEDGED"
    ) -> dict[str, Any]:
        validate_record("capability-negotiation.schema.json", negotiation)
        if negotiation["recipient"] != self.recipient:
            raise HPLContractError("RECIPIENT_MISMATCH", "cannot acknowledge another recipient's departure")
        body = {
            "negotiationId": negotiation["negotiationId"],
            "recipient": self.recipient,
            "acknowledgedAt": at,
            "assurance": assurance,
            "statement": "Runtime would unload the bounded projection; opaque copies are not disproven.",
            "canonicalV2Effect": "NONE",
        }
        record = _identified("hpl:departure-ack", "acknowledgementId", body)
        validate_record("departure-acknowledgement.schema.json", record)
        return record
