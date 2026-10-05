import json
from copy import deepcopy
from pathlib import Path

import pytest

from pwm_hpl_ref.authority import AuthorityEngine, Constraint
from pwm_hpl_ref.hpl_contracts import (
    BoundAuthorityDecision,
    HPLContractError,
    HPLLifecycle,
    bind_authority,
    discover_capabilities,
    make_capability_manifest,
    make_bounded_projection,
    make_projection_request,
    make_target_profile,
    negotiate,
    request_digest,
    target_profile_digest,
)
from pwm_hpl_ref.hpl_simulation import ForeignRuntimeSimulator
from pwm_hpl_ref.schema_validation import validate_record


ROOT = Path(__file__).parents[1]
NOW = "2026-01-01T10:00:00+00:00"
EXPIRY = "2026-01-01T11:00:00+00:00"
MANIFEST_EXPIRY = "2026-01-01T12:00:00+00:00"
CAPABILITY = "robot.delivery.place"


def load_profile(name="robot"):
    return json.loads((ROOT / "profiles" / "hpl-targets" / f"{name}.json").read_text())


def manifest(profile, *, available=True, expires_at=MANIFEST_EXPIRY):
    capability = profile["capabilities"][0]
    return make_capability_manifest(
        target_id="urn:device:test-target",
        recipient=profile["recipient"],
        target_profile_id=profile["targetProfileId"],
        target_profile_digest=target_profile_digest(profile),
        capabilities=[
            {
                "capabilityId": capability["capabilityId"],
                "available": available,
                "inputFields": capability["requiredFields"] + capability["optionalFields"],
                "localSafetyControls": ["independent-stop"],
            }
        ],
        discovered_at="2026-01-01T09:00:00+00:00",
        expires_at=expires_at,
    )


def request(profile, fields=None, *, consent=(), expires_at=EXPIRY):
    capability = profile["capabilities"][0]
    return make_projection_request(
        requester="did:example:person-1",
        recipient=profile["recipient"],
        target_profile_id=profile["targetProfileId"],
        purpose=capability["purposes"][0],
        capability=capability["capabilityId"],
        requested_fields=fields if fields is not None else capability["requiredFields"],
        issued_at="2026-01-01T09:30:00+00:00",
        expires_at=expires_at,
        consent_evidence=consent,
    )


def decision_for(req, *, denied=False):
    constraints = [
        Constraint(req["requester"], "ALLOW", frozenset({req["capability"]}), "PERSONAL")
    ]
    if denied:
        constraints.append(
            Constraint("machine-safety", "DENY", frozenset({req["capability"]}), "PHYSICAL")
        )
    decision = AuthorityEngine().resolve(
        {req["capability"]}, constraints, binding_ref=request_digest(req)
    )
    return bind_authority(req, decision, ("urn:authority:test",))


def mapping(field="delivery.allowed_surface"):
    return [
        {
            "sourceField": field,
            "targetField": field,
            "transform": "identity",
            "confidence": 1.0,
            "provenanceRefs": ["urn:evidence:mapping-source"],
        }
    ]


def granted_bundle(*, fields=None, expires_at=EXPIRY):
    profile = load_profile()
    req = request(profile, fields, expires_at=expires_at)
    result = negotiate(req, profile, manifest(profile), decision_for(req), mapping(), negotiated_at=NOW)
    return profile, req, result


def test_all_target_profiles_are_illustrative_capability_first_contracts():
    profiles = sorted((ROOT / "profiles" / "hpl-targets").glob("*.json"))
    assert len(profiles) == 8
    assert {path.stem for path in profiles} == {
        "vehicle", "robot", "home", "storefront", "industrial", "accessibility", "caregiver", "shared-environment"
    }
    for path in profiles:
        profile = json.loads(path.read_text())
        validate_record("hpl-target-profile.schema.json", profile)
        assert profile["illustrative"] is True
        assert profile["canonicalV2Effect"] == "NONE"
        for capability in profile["capabilities"]:
            assert capability["deniedFields"]


def test_contract_factories_have_deterministic_ids_and_discovery_is_not_authority():
    profile = make_target_profile(
        target_class="ROBOT",
        recipient="did:example:r",
        capabilities=[load_profile()["capabilities"][0]],
    )
    assert profile == make_target_profile(
        target_class="ROBOT", recipient="did:example:r", capabilities=[load_profile()["capabilities"][0]]
    )
    cap_manifest = manifest(profile)
    assert cap_manifest == manifest(profile)
    assert discover_capabilities(profile, cap_manifest, at=NOW)[0]["available"] is True
    req = request(profile)
    assert req == request(profile)
    assert request_digest(req).startswith("urn:hpl:request-digest:sha256:")
    tampered_profile = deepcopy(profile)
    tampered_profile["capabilities"][0]["deniedFields"] = []
    with pytest.raises(HPLContractError) as error:
        discover_capabilities(tampered_profile, cap_manifest, at=NOW)
    assert error.value.code == "PROFILE_DIGEST_MISMATCH"


def test_exact_binding_and_mapping_evidence_fail_closed():
    profile = load_profile()
    req = request(profile)
    wrong_decision = AuthorityEngine().resolve(
        {"different.capability"},
        [Constraint("person", "ALLOW", frozenset({"different.capability"}), "PERSONAL")],
        binding_ref=request_digest(req),
    )
    with pytest.raises(HPLContractError, match="exact capability") as error:
        bind_authority(req, wrong_decision)
    assert error.value.code == "AUTHORITY_BINDING_MISMATCH"
    with pytest.raises(HPLContractError) as missing_mapping:
        negotiate(req, profile, manifest(profile), decision_for(req), [], negotiated_at=NOW)
    assert missing_mapping.value.code == "MAPPING_EVIDENCE_REQUIRED"
    other_principal = AuthorityEngine().resolve(
        {req["capability"]},
        [Constraint("did:example:other", "ALLOW", frozenset({req["capability"]}), "PERSONAL")],
        binding_ref=request_digest(req),
    )
    with pytest.raises(HPLContractError) as principal_error:
        bind_authority(req, other_principal)
    assert principal_error.value.code == "AUTHORITY_PRINCIPAL_MISMATCH"
    cross_capability = AuthorityEngine().resolve(
        {req["capability"], "unrelated"},
        [
            Constraint(req["requester"], "ALLOW", frozenset({"unrelated"}), "PERSONAL"),
            Constraint("did:example:other", "ALLOW", frozenset({req["capability"]}), "PERSONAL"),
        ],
        binding_ref=request_digest(req),
    )
    narrowed = type(cross_capability)(
        frozenset({req["capability"]}), frozenset({req["capability"]}), frozenset(), (),
        request_digest(req), cross_capability.granting_principals, (),
        cross_capability.grant_sources, (),
    )
    with pytest.raises(HPLContractError) as borrowed:
        bind_authority(req, narrowed)
    assert borrowed.value.code == "AUTHORITY_PRINCIPAL_MISMATCH"
    forged = BoundAuthorityDecision(request_digest(req), AuthorityEngine().resolve(
        {req["capability"]},
        [Constraint(req["requester"], "ALLOW", frozenset({req["capability"]}), "PERSONAL")],
        binding_ref="different-request",
    ))
    with pytest.raises(HPLContractError) as rebound:
        negotiate(req, profile, manifest(profile), forged, mapping(), negotiated_at=NOW)
    assert rebound.value.code == "AUTHORITY_BINDING_MISMATCH"


def test_all_negotiation_statuses_are_representable():
    robot = load_profile()
    redacted_req = request(robot, ["delivery.allowed_surface", "home.private_zone"])
    redacted = negotiate(redacted_req, robot, manifest(robot), decision_for(redacted_req), mapping(), negotiated_at=NOW)
    assert redacted["status"] == "REDACTED"

    denied_req = request(robot)
    denied = negotiate(denied_req, robot, manifest(robot), decision_for(denied_req, denied=True), [], negotiated_at=NOW)
    assert denied["status"] == "DENIED"
    unavailable = negotiate(denied_req, robot, manifest(robot, available=False), decision_for(denied_req), [], negotiated_at=NOW)
    assert unavailable["status"] == "UNAVAILABLE"

    caregiver = load_profile("caregiver")
    consent_req = request(caregiver)
    consent = negotiate(consent_req, caregiver, manifest(caregiver), decision_for(consent_req), [], negotiated_at=NOW)
    assert consent["status"] == "REQUIRES_CONSENT"

    for name, expected in (("home", "TRANSFORMED"), ("vehicle", "DERIVED")):
        profile = load_profile(name)
        req = request(profile, consent=["urn:consent:1"])
        evidence = mapping(profile["capabilities"][0]["requiredFields"][0])
        result = negotiate(req, profile, manifest(profile), decision_for(req), evidence, negotiated_at=NOW)
        assert result["status"] == expected

    _, _, granted = granted_bundle()
    assert granted["status"] == "GRANTED"


def test_lifecycle_revocation_and_departure_are_schema_validated():
    profile, req, result = granted_bundle()
    lifecycle = HPLLifecycle(result)
    lifecycle.transition("ISSUED", "2026-01-01T10:01:00+00:00")
    lifecycle.transition("ACTIVE", "2026-01-01T10:02:00+00:00")
    revocation = lifecycle.revoke("person withdrew grant", "did:example:person-1", "2026-01-01T10:03:00+00:00")
    validate_record("revocation-record.schema.json", revocation)
    assert lifecycle.state == "REVOKED"
    with pytest.raises(HPLContractError) as error:
        lifecycle.transition("ACTIVE", "2026-01-01T10:04:00+00:00")
    assert error.value.code == "INVALID_LIFECYCLE_TRANSITION"

    runtime = ForeignRuntimeSimulator(profile["recipient"])
    acknowledgement = runtime.acknowledge_departure(result, at="2026-01-01T10:05:00+00:00")
    validate_record("departure-acknowledgement.schema.json", acknowledgement)
    assert "not disproven" in acknowledgement["statement"]

    expired_lifecycle = HPLLifecycle(result)
    with pytest.raises(HPLContractError) as expired:
        expired_lifecycle.transition("ISSUED", result["expiresAt"])
    assert expired.value.code == "NEGOTIATION_EXPIRED"


def test_eight_physical_ai_scenario_fixtures_execute_expected_boundaries():
    fixtures = sorted((ROOT / "examples" / "physical-ai-simulator").glob("*.json"))
    assert len(fixtures) == 8
    observed = {}
    for fixture_path in fixtures:
        scenario = json.loads(fixture_path.read_text())
        scenario_id = scenario["scenarioId"]
        profile = load_profile()

        if scenario_id == "stale-state":
            stale = manifest(profile, expires_at="2026-01-01T09:30:00+00:00")
            with pytest.raises(HPLContractError) as error:
                discover_capabilities(profile, stale, at=NOW)
            assert error.value.code == scenario["expectedErrorCode"]
            observed[scenario_id] = "REFUSED"
            continue

        fields = scenario.get("requestedFields")
        req = request(profile, fields)
        authority = decision_for(req, denied=scenario_id == "conflicting-principals")
        evidence = [] if scenario_id == "conflicting-principals" else mapping()
        result = negotiate(req, profile, manifest(profile), authority, evidence, negotiated_at=NOW)
        if "expectedNegotiationStatus" in scenario:
            assert result["status"] == scenario["expectedNegotiationStatus"]
        if "expectedErrorCode" in scenario:
            assert result["error"]["code"] == scenario["expectedErrorCode"]

        safety_policy = (
            (lambda _capability, _payload: (False, "obstacle in local path"))
            if scenario_id == "safety-veto"
            else None
        )
        runtime = ForeignRuntimeSimulator(profile["recipient"], safety_policy)
        if result["status"] not in {"GRANTED", "REDACTED", "TRANSFORMED", "DERIVED"}:
            observed[scenario_id] = "REFUSED"
            continue
        projection = make_bounded_projection(
            result,
            {field: "bounded-value" for field in result["grantedFields"]},
            issued_at="2026-01-01T10:01:00+00:00",
            field_sources={field: {"effectivePrivacyClass": "PERSONAL", "provenanceRefs": ["urn:evidence:mapping-source"]} for field in result["grantedFields"]},
        )
        lifecycle = HPLLifecycle(result)
        lifecycle.transition("ISSUED", "2026-01-01T10:01:01+00:00")
        lifecycle.transition("ACTIVE", "2026-01-01T10:01:02+00:00")
        if scenario_id == "revocation":
            runtime.apply_revocation(
                lifecycle.revoke("manual stop", "did:example:person-1", "2026-01-01T10:03:00+00:00")
            )
            observed[scenario_id] = "REFUSED"
            continue

        execution_at = "2026-01-01T11:01:00+00:00" if scenario_id == "offline-expiry" else "2026-01-01T10:05:00+00:00"
        payload = {field: "bounded-value" for field in result["grantedFields"]}
        safety, outcome = runtime.execute_projection(
            req, result, projection, lifecycle,
            at=execution_at,
            online=not scenario.get("runtimeOnline") is False,
            compromised_device_assumed=scenario.get("compromisedDeviceAssumed", False),
        )
        validate_record("local-safety-decision.schema.json", safety)
        validate_record("execution-outcome.schema.json", outcome)
        assert outcome["disposition"] == scenario["expectedDisposition"]
        assert outcome["actuationPerformed"] is False
        assert outcome["canonicalV2Effect"] == "NONE"
        if "expectedReasonCode" in scenario:
            assert scenario["expectedReasonCode"] in outcome["reasonCodes"]
        if "expectedReasonCodes" in scenario:
            assert set(scenario["expectedReasonCodes"]) <= set(outcome["reasonCodes"])
        if scenario_id == "minimum-disclosure":
            assert result["grantedFields"] == scenario["expectedGrantedFields"]
            assert "home.private_zone" not in payload
        if scenario_id == "provenance":
            assert "urn:evidence:mapping-source" in outcome["provenanceRefs"]
            assert result["negotiationId"] in outcome["provenanceRefs"]
            assert safety["decisionId"] in outcome["provenanceRefs"]
        if scenario_id == "compromised-device-graceful-degradation":
            assert outcome["gracefulDegradation"] == scenario["fallback"]
        observed[scenario_id] = outcome["disposition"]

    assert set(observed) == {
        "minimum-disclosure", "conflicting-principals", "stale-state", "revocation", "safety-veto",
        "offline-expiry", "provenance", "compromised-device-graceful-degradation"
    }


def test_foreign_runtime_exposes_no_pwm_or_plog_handle_and_rejects_tampering():
    profile, req, result = granted_bundle()
    runtime = ForeignRuntimeSimulator(profile["recipient"])
    assert not hasattr(runtime, "pwm")
    assert not hasattr(runtime, "plog")
    tampered = deepcopy(result)
    tampered["purpose"] = "different-purpose"
    _, outcome = runtime._evaluate_unbound(req, tampered, {"delivery.allowed_surface": "entry-table"}, at=NOW)
    assert outcome["disposition"] == "REFUSED"
    assert "PURPOSE_MISMATCH" in outcome["reasonCodes"]
    tampered_request = deepcopy(req)
    tampered_request["purpose"] = "tampered-purpose"
    _, request_outcome = runtime._evaluate_unbound(
        tampered_request, result, {"delivery.allowed_surface": "entry-table"}, at=NOW
    )
    assert request_outcome["disposition"] == "REFUSED"
    assert "REQUEST_ID_MISMATCH" in request_outcome["reasonCodes"]


def test_bounded_projection_is_exactly_negotiated_and_runtime_verified():
    profile, req, result = granted_bundle()
    projection = make_bounded_projection(
        result,
        {"delivery.allowed_surface": "entry-table"},
        issued_at="2026-01-01T10:01:00+00:00",
        field_sources={"delivery.allowed_surface": {"effectivePrivacyClass": "PERSONAL", "provenanceRefs": ["urn:evidence:mapping-source"]}},
    )
    validate_record("hpl-bounded-projection.schema.json", projection)
    assert projection["sensitivity"] == "PERSONAL"
    with pytest.raises(HPLContractError) as incomplete:
        make_bounded_projection(
            result, {}, issued_at="2026-01-01T10:01:00+00:00", field_sources={}
        )
    assert incomplete.value.code == "FIELD_SET_MISMATCH"
    with pytest.raises(HPLContractError) as overclassified:
        make_bounded_projection(
            result,
            {"delivery.allowed_surface": "entry-table"},
            issued_at="2026-01-01T10:01:00+00:00",
            field_sources={"delivery.allowed_surface": {"effectivePrivacyClass": "SENSITIVE", "provenanceRefs": ["urn:evidence:mapping-source"]}},
        )
    assert overclassified.value.code == "PRIVACY_CEILING_EXCEEDED"
    runtime = ForeignRuntimeSimulator(profile["recipient"])
    lifecycle = HPLLifecycle(result)
    lifecycle.transition("ISSUED", "2026-01-01T10:01:01+00:00")
    lifecycle.transition("ACTIVE", "2026-01-01T10:01:02+00:00")
    _, outcome = runtime.execute_projection(req, result, projection, lifecycle, at="2026-01-01T10:02:00+00:00")
    assert outcome["disposition"] == "WOULD_DISPATCH"
    tampered = deepcopy(projection)
    tampered["fields"]["home.private_zone"] = "bedroom"
    tampered_lifecycle = HPLLifecycle(result)
    tampered_lifecycle.transition("ISSUED", "2026-01-01T10:01:01+00:00")
    tampered_lifecycle.transition("ACTIVE", "2026-01-01T10:01:02+00:00")
    with pytest.raises(HPLContractError) as error:
        runtime.execute_projection(req, result, tampered, tampered_lifecycle, at="2026-01-01T10:02:00+00:00")
    assert error.value.code == "PROJECTION_ID_MISMATCH"
    future_lifecycle = HPLLifecycle(result)
    future_lifecycle.transition("ISSUED", "2026-01-01T10:01:01+00:00")
    future_lifecycle.transition("ACTIVE", "2026-01-01T10:01:02+00:00")
    future = make_bounded_projection(
        result,
        {"delivery.allowed_surface": "entry-table"},
        issued_at="2026-01-01T10:30:00+00:00",
        field_sources={"delivery.allowed_surface": {"effectivePrivacyClass": "PERSONAL", "provenanceRefs": ["urn:evidence:mapping-source"]}},
    )
    with pytest.raises(HPLContractError) as not_yet_valid:
        runtime.execute_projection(req, result, future, future_lifecycle, at="2026-01-01T10:05:00+00:00")
    assert not_yet_valid.value.code == "PROJECTION_NOT_YET_VALID"


def test_all_eight_physical_domains_negotiate_and_simulate_without_actuation():
    matrix = json.loads((ROOT / "examples/physical-ai-simulator/domains/scenarios.json").read_text())
    validate_record("hpl-physical-scenarios.schema.json", matrix)
    required = {
        "minimum-disclosure", "authority", "conflicting-humans", "stale-state", "revocation",
        "safety", "offline", "provenance", "device-compromise", "graceful-degradation",
    }
    for scenario in matrix["scenarios"]:
        assert set(scenario["requirements"]) == required
        profile = load_profile(scenario["targetProfile"])
        capability = profile["capabilities"][0]
        req = request(profile, consent=("urn:consent:fixture",))
        mapped = [
            {
                "sourceField": field,
                "targetField": field,
                "transform": "identity",
                "confidence": 1.0,
                "provenanceRefs": ["urn:evidence:mapping-source"],
            }
            for field in capability["requiredFields"]
        ]
        result = negotiate(req, profile, manifest(profile), decision_for(req), mapped, negotiated_at=NOW)
        assert result["status"] in {"GRANTED", "TRANSFORMED", "DERIVED"}
        projection = make_bounded_projection(
            result,
            {field: "bounded-value" for field in result["grantedFields"]},
            issued_at="2026-01-01T10:01:00+00:00",
            field_sources={field: {"effectivePrivacyClass": "PERSONAL", "provenanceRefs": ["urn:evidence:mapping-source"]} for field in result["grantedFields"]},
        )
        lifecycle = HPLLifecycle(result)
        lifecycle.transition("ISSUED", "2026-01-01T10:01:01+00:00")
        lifecycle.transition("ACTIVE", "2026-01-01T10:01:02+00:00")
        _, outcome = ForeignRuntimeSimulator(profile["recipient"]).execute_projection(
            req, result, projection, lifecycle, at="2026-01-01T10:02:00+00:00"
        )
        assert outcome["disposition"] == "WOULD_DISPATCH"
        assert outcome["actuationPerformed"] is False
