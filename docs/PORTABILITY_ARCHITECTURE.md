# Portability architecture

Status: `PROPOSED` design; no production portability claim.

## Dependency classes

| Class | Requirement | Examples |
|---|---|---|
| Core-semantic | Must preserve meaning or fail migration | event types, provenance links, lifecycle states, privacy class |
| Policy-local | Must be re-authorized at destination | grants, recipient/purpose bindings, actuator permission |
| Replaceable service | May change behind a role protocol | storage engine, model provider, identity resolver, transport |
| Hardware-affine | Export description/evidence, not assumptions | sensor calibration, accelerator format, secure-element proof |
| Ephemeral | Must not be treated as durable state | stream buffers, caches, open sessions, possible-world branches |
| External substrate | Requires explicit custody and availability contract | object store, KMS, cloud queue, model API |

An export must inventory all six classes, versions, unresolved semantics, revocations and unavailable dependencies. Missing core semantics fail closed; policy is never copied as authority merely because it serialized successfully.

## Footprints

| Profile | Intended capacity | Required invariant |
|---|---|---|
| Micro | Event capture, bounded verification, references | No hidden canonical cloud dependency |
| Edge | Partial materialization, policy enforcement, offline queue | Privacy-segment and revocation enforcement |
| Full | Complete authorized replica, research and model lifecycle | Provenance closure and deterministic reconstruction |

Profiles describe resource envelopes, not CPU architecture, vendor, operating system or accelerator. Conformance is behavioral. Hardware-specific optimizations remain replaceable dependencies and must publish fallback or explicit incompatibility.

## Portability test

A useful benchmark exports a synthetic event closure, imports it into a different adapter stack, rematerializes at fixed times, compares canonical public outputs, verifies withheld segments remain absent, and confirms policy requires fresh authorization. See `templates/benchmark/`.
