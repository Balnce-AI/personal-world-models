# Wave 01 Conformance Bundle Profile

**Status:** `STABLE` companion to `public-provenance-profile-v1.md`

The JSON bundle is transport for conformance evidence, not the signed representation. Binary fields are lowercase hexadecimal; CIDs are canonical lowercase base32 CID text.

Required top-level members are `profile`, `appender_key_id`, `appender_public_key_hex`, `author_keys`, `schemas`, and `records`. Unknown members fail closed. Author key IDs and `(event_kind, schema_version)` registrations are unique.

## Key-Status Frontier

The canonical frontier value is an array of maps sorted lexicographically by `key_id`. Each map has exactly `key_id` (text), `public_key` (32-byte byte string), `active_from_log_sequence` (unsigned integer), and `revoked_at_log_sequence` (unsigned integer or null). It is encoded using the restricted deterministic CBOR profile and identified using the `pwm:key-status-frontier:v1\0` domain.

Bundle reconstruction inserts `author_keys` in array order. A frontier snapshot is captured after every insertion. Revocations are then applied in the same array order, with a new snapshot after every non-null revocation. Duplicate keys and revocation before activation fail closed. Receipt verification resolves exactly the frontier CID named in the signed receipt.

## Record Processing

Records are presented in append-receipt `log_sequence` order beginning at zero. Each record contains exact event-body CBOR, body CID, author signature, payload CBOR, receipt-body CBOR, receipt CID, and appender signature. Implementations verify canonical bytes, typed CIDs, schemas, keys, signatures, payload binding, principal/parent rules, sequence rules, receipt binding, and frontier validity before accepting a record.

Replay uses parent-before-child topological ordering with raw CID bytes as the ready-set tie-break. `conformance/expectations/wave01-valid.json` publishes the expected order independently of either implementation.
