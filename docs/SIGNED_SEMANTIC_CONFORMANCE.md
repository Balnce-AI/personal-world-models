# Signed Semantic Conformance

The provisional `pwm-signed-semantics-v1` profile connects two deliberately separate layers:

1. The unchanged, stable Wave01 layer proves canonical bytes, typed content identity, signatures, append membership, key status, causal closure, and deterministic replay.
2. The provisional semantic layer interprets the verified payload as a closed PWM/HPL command and applies it through an authenticated principal grant.

A semantic implementation must never consume an event merely because a JSON object resembles a fixture. It consumes exact payload CBOR only after the enclosing Wave01 record and receipt verify. The payload is not a replacement event envelope: `EventBody` remains exactly the eight-field structure in `public-provenance-profile-v1.md`.

## Required assets

- Normative profile: `spec/signed-semantic-conformance-v1.md`
- Payload registry: `spec/signed-semantic-payloads-v1.md`
- Principal authorization: `spec/authenticated-principals-v1.md`
- Error precedence: `spec/semantic-error-precedence-v1.md`
- Suite/source/output schemas: `conformance/schemas/signed-semantic-*.schema.json`
- Claim schema: `conformance/schemas/implementation-claim.schema.json`

## Evidence boundary

Schema validity proves transport shape only. A conforming run must additionally verify cryptography, process all records, enforce grant intervals at receipt sequence, reduce atomically, execute the declared command, normalize output, and compare it semantically. A provisional claim must identify the exact suite SHA-256 and contain no skipped cases.

Every suite case contains its source and complete expectation. Valid cases carry the full normalized expected output. Invalid cases carry one precedence-selected error and require unchanged state; only a `SOURCE_SCHEMA_INVALID` case intentionally contains a source that fails the source schema. The suite-level trust anchor is immutable and must match each well-formed source.

The profile deliberately does not update the existing conformance manifest or Wave01 vectors. A future reviewed suite can adopt these schemas without retroactively changing stable Wave01 evidence.
