import json
from pathlib import Path

from pwm import (
    AuthorityEngine,
    Constraint,
    bind_authority,
    make_bounded_projection,
    make_capability_manifest,
    make_projection_request,
    negotiate,
    request_digest,
    target_profile_digest,
)

root = Path(__file__).resolve().parents[2]
profile = json.loads((root / "profiles/hpl-targets/robot.json").read_text())
capability = profile["capabilities"][0]
request = make_projection_request(
    requester="did:example:alice", recipient=profile["recipient"],
    target_profile_id=profile["targetProfileId"], purpose=capability["purposes"][0],
    capability=capability["capabilityId"], requested_fields=capability["requiredFields"],
    issued_at="2026-01-01T09:00:00+00:00", expires_at="2026-01-01T11:00:00+00:00",
)
decision = AuthorityEngine().resolve(
    {request["capability"]},
    [Constraint("did:example:alice", "ALLOW", frozenset({request["capability"]}), "PERSONAL")],
    binding_ref=request_digest(request),
)
manifest = make_capability_manifest(
    target_id="robot:7", recipient=profile["recipient"], target_profile_id=profile["targetProfileId"],
    target_profile_digest=target_profile_digest(profile),
    capabilities=[{"capabilityId": request["capability"], "available": True, "inputFields": capability["requiredFields"], "localSafetyControls": ["independent-stop"]}],
    discovered_at="2026-01-01T08:00:00+00:00", expires_at="2026-01-01T12:00:00+00:00",
)
mapping = [{"sourceField": field, "targetField": field, "transform": "identity", "confidence": 1.0, "provenanceRefs": ["mapping:fixture"]} for field in capability["requiredFields"]]
negotiation = negotiate(request, profile, manifest, bind_authority(request, decision), mapping, negotiated_at="2026-01-01T10:00:00+00:00")
projection = make_bounded_projection(
    negotiation, {field: "bounded-value" for field in negotiation["grantedFields"]},
    issued_at="2026-01-01T10:01:00+00:00",
    field_sources={field: {"effectivePrivacyClass": "PERSONAL", "provenanceRefs": ["mapping:fixture"]} for field in negotiation["grantedFields"]},
)
print(projection)
