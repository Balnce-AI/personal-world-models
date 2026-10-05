---
status: EXPERIMENTAL
version: 0.1.0
---
# HPL capability negotiation

## Scope

This profile defines a bounded experiment for discovering and negotiating one foreign-runtime capability. It reuses the existing authority `Decision` as evidence. It does not define a universal authority engine, replace Covenant semantics, implement canonical UOR/PLog, or alter canonical V2 state. Every public record in this profile has `canonicalV2Effect: NONE`.

## Discovery

A target profile declares capability policy. A separately refreshed capability manifest states what one recipient currently advertises, its input vocabulary, local controls, target-profile content digest, and expiry. Discovery is descriptive, not permission. Implementations MUST reject an expired manifest, a profile digest or recipient mismatch, and capabilities not declared by the profile.

Profiles are capability-first: target class is descriptive and never grants access. The examples for vehicle, robot, home, storefront, industrial, accessibility, caregiver, and shared environment are illustrative and extensible, not normative policy.

## Request and binding

A projection request binds exactly one purpose, recipient, target-profile ID, and capability. Its `requestId` and `requestDigest` cover the complete request, including fields, consent evidence, and validity interval. A negotiation repeats all four bindings and the digest. A recipient MUST refuse any mismatch rather than infer intent.

The authority evidence MUST come from an existing `Decision` whose requested set is exactly the requested capability and MUST be bound to the complete request digest before negotiation. A granted capability MUST identify the requester as a granting principal for that same capability; an unrelated grant by the requester does not satisfy this rule. The negotiation records its requested, allowed, denied, granting and denying principals, capability-level sources, reasons, evidence references, and request digest without expanding authority.

## Statuses

| Status | Meaning |
|---|---|
| `GRANTED` | Capability and all requested fields are directly usable. |
| `DENIED` | Authority, purpose policy, or a required field prevents issuance. |
| `UNAVAILABLE` | The target does not currently advertise the capability. |
| `REDACTED` | A useful request remains after prohibited or unsupported fields are removed. |
| `TRANSFORMED` | Only the declared transformed representation may be issued. |
| `DERIVED` | Only a declared derived fact or constraint may be issued. |
| `REQUIRES_CONSENT` | Explicit consent evidence is absent and negotiation may be retried. |

Only `GRANTED`, `REDACTED`, `TRANSFORMED`, and `DERIVED` are issuable. Successful negotiation requires mapping evidence with source field, target field, transform, confidence, and provenance references.

In this experimental profile, `consentEvidence` contains references whose existence is checked by the integrating authority boundary; the HPL reference does not verify signatures, scope, expiry, or revocation of those referenced consent records. A non-empty string alone MUST NOT be treated as production consent.

## Bounded projection

An issuable negotiation produces a separate bounded projection whose fields MUST exactly equal the negotiated grant. The artifact binds request, negotiation, recipient, purpose, capability, target profile, issue/expiry interval, refresh policy, revocation reference, allowed use, onward-sharing rule, sensitivity, and provenance. Recipients MUST recompute its content identifier and reject altered, expired, or mismatched artifacts. This experimental record is not a substitute for a signed transport or Arranger profile.

## Errors

Contract failures use stable `code`, human-readable `message`, and `retryable` fields. Binding and undeclared-capability errors are fail-closed. Expired discovery and missing consent may be retryable. A status-level error is carried in denied, unavailable, and consent-required negotiations; malformed inputs and binding violations raise a contract error before a negotiation exists.

## Lifecycle

The experimental state sequence is:

`REQUESTED -> NEGOTIATED -> ISSUED -> ACTIVE -> EXECUTED -> DEPARTED`

`REVOKED` and `EXPIRED` may terminate any pre-departure active state; `REFUSED` may terminate `ACTIVE`. Every transition emits a deterministic lifecycle event. Revocation names the actor, reason, previous state, request, negotiation, and lifecycle event. Expiry is enforced using the earlier request or discovery-manifest expiry, including while offline.

## Execution boundary

The foreign runtime receives contracts and bounded payload only. It has no PWM or PLog handle. It independently evaluates local safety after HPL checks and may veto an authorized action. Simulation outputs are only `WOULD_DISPATCH` or `REFUSED`, and `actuationPerformed` is always false. Refusal degrades to `NO_ACTUATION_RETAIN_CONTROL`; it does not invent a weaker autonomous action. This profile makes no safety certification claim. Under a compromised-device assumption, the refusal record is expected protocol evidence, not proof that compromised hardware complied.

Departure acknowledgement proves only the stated protocol action. It does not prove universal deletion or absence of opaque copies. Execution outcomes are provenance-bearing observations and never silently update canonical PWM state.
