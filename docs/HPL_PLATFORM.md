# Experimental HPL platform vertical slice

This vertical slice demonstrates a narrow end-to-end HPL contract path:

`target profile -> capability discovery -> bounded request -> request-bound authority evidence -> negotiation -> bounded projection -> lifecycle -> foreign local veto -> non-actuating outcome -> departure acknowledgement`

The implementation lives in `pwm_hpl_ref.hpl_contracts` and `pwm_hpl_ref.hpl_simulation`. Public records are defined by JSON Schemas under `schemas/json-schema/`. Eight illustrative capability-first profiles, eight threat-oriented fixtures, and eight recipient-domain scenarios exercise the boundary.

## Guarantees in the experiment

- Request and negotiation IDs are deterministic content hashes.
- Purpose, recipient, profile, capability, request ID, and request digest are checked exactly.
- Authority comes from the existing `authority.Decision`; `bind_authority` binds that evidence to the exact request digest before HPL can use it.
- Discovery manifests and negotiated grants expire and fail closed.
- Field allow/deny policy supports direct, transformed, derived, and redacted results.
- Successful mapping is provenance-bearing.
- Revocation is explicit and lifecycle-bound.
- A foreign runtime has no PWM/PLog object or mutation API.
- Local safety remains an independent veto.
- Every runtime-produced object is schema validated.
- Outcomes describe only `WOULD_DISPATCH` or `REFUSED`; no actuator is called.
- Canonical V2 effect is `NONE`.

## Non-claims

This is not a production protocol, universal authority engine, canonical PLog/UOR implementation, hardware integration, proof of deletion, device trust system, or safety certification. The profiles are illustrative. A capability advertisement is not authorization, and an HPL grant is not a local safety approval.

## Capability discovery

Create a target profile with `make_target_profile`, then a short-lived advertisement with `make_capability_manifest`. `target_profile_digest` binds that advertisement to the complete profile content. `discover_capabilities` validates both schemas, exact profile digest and recipient binding, declared capability membership, and the discovery interval. Stable `HPLContractError` codes distinguish expiry, future manifests, identity mismatches, undeclared capabilities, and malformed time.

## Negotiation and simulation

`make_projection_request` creates the bounded request. `negotiate` consumes the request, profile, fresh manifest, request-bound existing `Decision`, and mapping evidence. The returned status is one of `GRANTED`, `DENIED`, `UNAVAILABLE`, `REDACTED`, `TRANSFORMED`, `DERIVED`, or `REQUIRES_CONSENT`.

`make_bounded_projection` then emits only the exact negotiated fields. The artifact binds recipient, purpose, capability, target profile, issue/expiry interval, sensitivity, refresh policy, allowed use, onward sharing, revocation reference, and provenance. `execute_projection` recomputes its content ID and checks every binding before local safety evaluation. This artifact is unsigned in the experimental slice; production transport still requires a signed provenance/Arranger profile.

`ForeignRuntimeSimulator.execute_projection` verifies all bindings again, checks revocation and local expiry even when offline, limits payload keys to granted fields, applies a local safety policy, and emits a local decision plus execution outcome. Refusal degrades to no actuation while retaining local control; a compromised runtime's report is not treated as proof of compliance. `acknowledge_departure` emits bounded cleanup evidence with an explicit opaque-copy caveat.

See `spec/hpl-negotiation.md` for normative experimental behavior and `examples/physical-ai-simulator/` for scenario expectations.
