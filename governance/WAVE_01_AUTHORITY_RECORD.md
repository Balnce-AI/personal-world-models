# Wave 01 Authority Record

**Decision date:** 2026-08-29
**Authority bundle SHA-256:** `5b317b8d3345cdd7f3d5a405ba19143d347e680a620bec5ab433937b34741b2b`

## Verification

The Wave 01 source-authority bundle was acquired outside this public repository. All 13 files matched both the bundle verification manifest and Package One's independently supplied source manifest by exact byte count and SHA-256. The source documents were read in precedence order. Their content is not redistributed here.

## Founder decision

The founder approved the public V2 interoperability profile implemented in Wave 01:

- restricted deterministic CBOR;
- integer nanosecond time and no floating point in signed records;
- non-NFC rejection;
- domain-separated typed CIDv1 raw SHA-256 identifiers;
- raw Ed25519 author signatures and signed append receipts;
- signed causal DAG verification and deterministic replay;
- independent cross-language vectors and verification.

This authorization does not publish or resolve private UOR identity, UOR-to-Atom/PLOG/PWM identity, the private production PLOG, the private serialization/hash suite, production identity or key custody, Guardian policy, Edge routing, recovery, anti-abuse, or deployment topology.

## Reconciliation

No conflict was found between Package One, the founder decision, and the supplied source-authority corpus for the bounded public profile. Lower-precedence open UOR proposals were not adopted. The implementation stops at the provenance spine and does not enter metagraph, materialization, phenomenology, HPL, NEP, or safety semantics.
