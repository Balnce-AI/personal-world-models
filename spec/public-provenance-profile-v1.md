# Public Provenance Profile v1

**Truth plane:** `IMPLEMENTED`
**Evidence:** `REAL`
**Publication:** `PUBLIC_FULL`
**Assurance:** `CONFORMANCE_PASS`
**Release disposition:** `RELEASABLE`

## Scope

This specification defines the public V2 interoperability profile for deterministic bytes, typed content identifiers, Ed25519 signatures, append receipts, and causal event replay. It is a safe public provenance profile. It is not UOR, the private production PLOG, a world-model materializer, key custody, recovery, Guardian policy, or deployment topology.

## Restricted deterministic CBOR

The profile follows RFC 8949 core deterministic encoding with a deliberately small value space:

- null and booleans;
- unsigned 64-bit integers and negative integers no smaller than `i64::MIN`;
- definite-length byte strings and NFC text strings;
- definite-length arrays;
- maps with unique NFC text keys.

Integers and lengths use the shortest encoding. Map entries sort by the bytewise order of each complete encoded key. Decoders reject floats, tags, indefinite lengths, unsupported simple values, non-text map keys, duplicate keys, non-NFC text, invalid UTF-8, non-shortest forms, incorrect map order, trailing bytes, nesting beyond 64 levels, aggregate collections beyond 1,000,000 items, and byte/text values beyond 16 MiB. Decoding succeeds only when re-encoding produces the exact input bytes.

Time values in signed records are integer nanoseconds. Floating-point values are forbidden in hashed or signed records.

## Typed CIDs

Each type has a distinct domain ending in a NUL byte:

| Type | Domain |
|---|---|
| Event body | `pwm:event-body:v1\0` |
| Payload | `pwm:payload:v1\0` |
| Append receipt body | `pwm:append-receipt-body:v1\0` |
| Key-status frontier | `pwm:key-status-frontier:v1\0` |

For canonical bytes `B` and domain `D`:

```text
digest = SHA-256(D || B)
cid = CIDv1(raw=0x55, sha2-256=0x12, digest)
```

The binary CID is exactly `01 55 12 20 <32-byte digest>`. Text is lowercase base32 with the `b` multibase prefix. Parsers reject other CID versions, codecs, hash algorithms, digest lengths, multibase prefixes, uppercase or padded text, and non-canonical encodings. These identifiers are public typed CIDs, not UOR identifiers.

## Signatures

The only algorithm in version 1 is raw Ed25519. Event authors sign:

```text
"pwm:event-signature:v1\0" || event_body_cid.multihash_bytes
```

Append authorities sign:

```text
"pwm:append-receipt-signature:v1\0" || receipt_body_cid.multihash_bytes
```

Verifiers reject malformed, non-canonical, or weak Ed25519 public keys. This profile specifies public verification only. It does not specify production key generation, custody, recovery, incident response, or trust routing.

## Event body

`EventBody` contains exactly:

```text
schema_version: text
event_kind: text
author_key_id: text
principal_scope: text
parent_event_cids: array<EventBodyCid>
author_sequence: unsigned integer
event_time: signed integer nanoseconds
payload_cid: PayloadCid
```

Parents are unique and sorted by raw CID bytes. A genesis has kind `pwm.genesis`, no parents, and author sequence zero. A non-genesis event has at least one existing parent in the same principal scope. Each `(principal_scope, author_key_id)` sequence is contiguous and its prior event must be in causal ancestry.

`event_time` is an author assertion. It does not establish causal order, append order, freshness, or key validity.

## Append receipt

An accepted event receives a separately signed `AppendReceiptBody`:

```text
body_cid: EventBodyCid
ingestion_time: signed integer nanoseconds
key_status_frontier_cid: KeyStatusFrontierCid
log_sequence: unsigned integer
appender_key_id: text
```

The append authority validates payload bytes and CID, schema binding, current key status, body CID, author signature, parent closure, scope, genesis shape, and author sequence before issuing a receipt. A retry of an accepted event CID returns its original receipt. Rejections are errors, not membership proofs.

Historical verification resolves the author key from the receipt's verified key-status frontier. A key revoked before append cannot regain validity by backdating `event_time`. Previously accepted records remain verifiable after rotation or revocation.

## Storage and replay

The reference durable store uses SQLite with foreign keys, WAL, `synchronous=FULL`, strict tables, and one transaction for event bytes, payload bytes, receipt bytes, edges, and log sequence. Startup re-decodes and re-verifies every present record in receipt order and compares stored edges to signed parents. Mutation of a present record or edge inconsistency fails closed. Detecting deletion of a valid suffix or rollback to an older internally valid database requires an externally protected expected head and is outside this reference profile.

Replay applies only to fully verified records. Kahn topological sorting uses raw CID bytes as the ready-set tie-break. Missing parents or cycles reject the complete replay; records are never silently omitted.

## Conformance

- `conformance/vectors/wave01-valid.json` contains exact CBOR hex, typed CIDs, public keys, signatures, branch/merge records, and receipts.
- `conformance/vectors/wave01-invalid.json` contains malformed CBOR cases.
- `conformance/python/pwm_oracle.py` is an independent Python verifier and replay oracle.
- `pwm vectors emit`, `pwm event verify`, and `pwm event replay` expose the Rust implementation.

The checked-in valid vector file must be byte-identical to regenerated Rust output. Rust and Python must verify it and emit identical replay order. Both must reject mutated signed content.

## Failure semantics

Public errors distinguish canonical encoding, typed identifier, signature, parent, scope, genesis, cycle, author sequence, key status, schema, and corruption classes. Durable storage errors expose a stable generic message rather than payload, key, SQL, or topology details.

## Limits

- This profile does not materialize PWM state or define metagraph semantics.
- It does not define general multi-principal authority.
- It does not make remote deletion, safety, or production-readiness claims.
- The benchmark is synthetic and does not model concurrent production traffic.
- The in-memory and SQLite implementations are public references, not the private production PLOG.

## Commands

```bash
cargo test --workspace
cargo run -q -p pwm-cli -- vectors emit --output /tmp/wave01.json
cargo run -q -p pwm-cli -- event verify --bundle conformance/vectors/wave01-valid.json
cargo run -q -p pwm-cli -- event replay --bundle conformance/vectors/wave01-valid.json
python3 conformance/python/pwm_oracle.py conformance/vectors/wave01-valid.json
cargo run --release -p pwm-event --example dag_benchmark
```
