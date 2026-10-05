from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .canonical import sha256_urn
from .schema_validation import validate_record


PRIVACY_CLASSES = ("PUBLIC", "LOW", "PERSONAL", "SENSITIVE", "HIGHLY_SENSITIVE")
PRIVACY_ORDER = {value: index for index, value in enumerate(PRIVACY_CLASSES)}
BOUNDARY_KINDS = frozenset({"REDACTION", "PROOF"})


def privacy_rank(value: str) -> int:
    try:
        return PRIVACY_ORDER[value]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unknown privacy class: {value}") from exc


def most_sensitive(values: Iterable[str], *, default: str = "PERSONAL") -> str:
    result = default
    privacy_rank(result)
    for value in values:
        if privacy_rank(value) > privacy_rank(result):
            result = value
    return result


@dataclass(frozen=True)
class DeclassificationBoundary:
    boundary_id: str
    boundary_kind: str
    input_privacy_class: str
    output_privacy_class: str
    source_refs: tuple[str, ...]
    policy_ref: str
    justification: str
    released_fields: tuple[str, ...] = ()
    approved: bool = False
    schema_version: str = "1.0.0"

    @classmethod
    def create(
        cls,
        boundary_kind: str,
        input_privacy_class: str,
        output_privacy_class: str,
        source_refs: tuple[str, ...],
        policy_ref: str,
        justification: str,
        *,
        released_fields: tuple[str, ...] = (),
        approved: bool = False,
    ) -> "DeclassificationBoundary":
        body = {
            "boundaryKind": boundary_kind,
            "inputPrivacyClass": input_privacy_class,
            "outputPrivacyClass": output_privacy_class,
            "sourceRefs": list(source_refs),
            "policyRef": policy_ref,
            "justification": justification,
            "releasedFields": list(released_fields),
            "approved": approved,
        }
        return cls(sha256_urn("pwm:privacy-boundary", body), boundary_kind, input_privacy_class,
                   output_privacy_class, source_refs, policy_ref, justification, released_fields, approved)

    def to_record(self) -> dict[str, Any]:
        record = {
            "boundaryId": self.boundary_id,
            "boundaryKind": self.boundary_kind,
            "inputPrivacyClass": self.input_privacy_class,
            "outputPrivacyClass": self.output_privacy_class,
            "sourceRefs": list(self.source_refs),
            "policyRef": self.policy_ref,
            "justification": self.justification,
            "releasedFields": list(self.released_fields),
            "approved": self.approved,
            "schemaVersion": self.schema_version,
        }
        validate_record("pwm-privacy-boundary.schema.json", record)
        return record


def effective_privacy(
    declared: str,
    *,
    evidence: Iterable[Mapping[str, Any]] = (),
    dependencies: Iterable[Mapping[str, Any]] = (),
    edges: Iterable[Mapping[str, Any]] = (),
    policies: Iterable[Mapping[str, Any]] = (),
    derivations: Iterable[Mapping[str, Any]] = (),
    boundaries: Iterable[Mapping[str, Any]] = (),
) -> tuple[str, bool]:
    """Return effective privacy and whether raw provenance must be suppressed."""
    classes = [declared]
    for record in (*tuple(evidence), *tuple(dependencies), *tuple(edges), *tuple(derivations)):
        classes.append(record.get("effectivePrivacyClass", record.get("privacyClass", "PERSONAL")))
    for policy in policies:
        classes.append(policy.get("privacyFloor", policy.get("privacyClass", "PERSONAL")))
    source_privacy = most_sensitive(classes)
    result = source_privacy
    redacted = False
    for boundary in boundaries:
        validate_record("pwm-privacy-boundary.schema.json", dict(boundary))
        if not boundary["approved"]:
            continue
        if privacy_rank(boundary["inputPrivacyClass"]) < privacy_rank(source_privacy):
            continue
        output = boundary["outputPrivacyClass"]
        if privacy_rank(output) < privacy_rank(result):
            result = output
            redacted = True
    return result, redacted


def validate_boundary_authority(
    boundaries: Iterable[Mapping[str, Any]], *, source_refs: Iterable[str], policies: Mapping[str, Any]
) -> None:
    required_sources = set(source_refs)
    for boundary in boundaries:
        validate_record("pwm-privacy-boundary.schema.json", dict(boundary))
        privacy_rank(boundary["inputPrivacyClass"])
        privacy_rank(boundary["outputPrivacyClass"])
        if privacy_rank(boundary["outputPrivacyClass"]) > privacy_rank(boundary["inputPrivacyClass"]):
            raise ValueError("privacy boundary output cannot be more restrictive than its input")
        if boundary["approved"] and (
            boundary["policyRef"] not in policies
            or not required_sources.issubset(boundary["sourceRefs"])
        ):
            raise ValueError("approved privacy boundary lacks policy authority or source coverage")
