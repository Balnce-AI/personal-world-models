# Signed Semantic Conformance Profile v1

**Status:** `PROVISIONAL`
**Profile:** `pwm-signed-semantics-v1`
**Schema version:** `1.0.0`

## Scope

This profile composes the `STABLE` Wave01 public provenance profile with a deterministic PWM/HPL semantic reducer. It does not alter Wave01 `EventBody`, canonical CBOR, typed CID, Ed25519 signature, append receipt, key-frontier, or replay rules. A conforming implementation MUST first verify a Wave01 bundle and only then interpret each verified payload under this profile.

The profile is provisional. Only the unchanged Wave01 provenance layer is stable. Passing these suites does not claim production key custody, private PLOG/UOR compatibility, policy safety, remote deletion, or conformance to a future profile revision.

## Signed semantic payload

For every registered semantic `event_kind`, the bytes identified by `EventBody.payload_cid` MUST be restricted deterministic CBOR as defined by `public-provenance-profile-v1.md`. The decoded value MUST be a map containing exactly:

```text
profile:          "pwm-signed-semantics-v1"
schema_version:   "1.0.0"
data:             map
valid_from_ns:    signed integer
valid_to_ns:      signed integer or null
```

`valid_from_ns` is inclusive and `valid_to_ns` is exclusive. When non-null, `valid_to_ns` MUST be greater than `valid_from_ns`. They model semantic validity only. `EventBody.event_time` remains an author assertion and append/key/grant validity is determined only from the verified receipt `log_sequence`.

Maps MUST have only the members declared for their event kind. Text MUST be NFC. Identifier text MUST be non-empty and at most 256 UTF-8 bytes. Lists that represent sets MUST contain no duplicates and MUST be sorted by the canonical CBOR bytes of each item. Semantic quantities MUST be integers or normalized fixed-point values; floats are forbidden. A fixed-point value is exactly `{coefficient: signed integer, scale: unsigned integer}` with `scale <= 18`; when `coefficient` is zero, `scale` MUST be zero, and a nonzero coefficient MUST NOT be divisible by 10 when `scale > 0`.

The payload validity interval belongs to the semantic fact created by the event. Receipt-order lifecycle transitions are effective from their receipt and are not backdated by that interval. At a command frontier, a record is valid for `as_of_valid_ns` exactly when `valid_from_ns <= as_of_valid_ns` and `valid_to_ns` is null or `as_of_valid_ns < valid_to_ns`. Status is derived from transitions committed at or before `evaluation_log_sequence`; an earlier valid time does not undo a later receipt-sequence revocation. Historical status therefore requires evaluation at the earlier receipt frontier as well as the desired valid time.

The complete field registry is normative in `signed-semantic-payloads-v1.md`.

## Processing pipeline

For each source, an implementation MUST:

1. Decode and verify the complete Wave01 bundle, including canonical bytes, CIDs, author and appender signatures, key frontiers, parent closure, principal scope, author sequences, receipts, and contiguous receipt sequences.
2. Require the fixed root trust anchor declared by the suite source and verify that the unique scope genesis is signed by that key.
3. Replay verified records in Wave01 parent-before-child order with raw event-body CID bytes as the ready-set tie-break.
4. Decode and shape-check the semantic payload against the event registry.
5. Resolve the authenticated principal and grant at the record's receipt `log_sequence`.
6. Apply semantic preconditions and effects atomically. A rejected event MUST make no state mutation.
7. Execute the source command and emit the output envelope in `signed-semantic-output.schema.json`.

No implementation may use JSON member order, source record order, `event_time`, wall-clock time, or an unverified payload as a reducer tie-break or authority input.

## State model

Reducer state contains these maps keyed by their corresponding IDs: `principals`, `grants`, `evidence`, `model_candidates`, `model_reviews`, `models`, `privacy_boundaries`, `contradiction_candidates`, `contradiction_reviews`, `contradictions`, `topology_edges`, `possible_worlds`, `query_authorities`, `hpl_requests`, `hpl_authorizations`, `hpl_projections`, and `evaluations`. Revocation and supersession update status while retaining records and provenance event CIDs.

The actual world has ID `world:actual`. Genesis creates it. Every other world MUST be created by `pwm.possible-world`. References MUST resolve in the already committed replay prefix unless the event definition explicitly creates them. All effects are scoped by `EventBody.principal_scope`.

## Event registry

Only these `(event_kind, schema_version)` pairs are standard:

| Event kind | Required operation | Required capability | Atomic effect |
|---|---|---|---|
| `pwm.genesis` | root bootstrap exception | root bootstrap exception | Create scope, principals, grants, and `world:actual`. |
| `pwm.evidence` | `EVIDENCE_CREATE` | `pwm.evidence.write` | Add immutable evidence. |
| `pwm.policy` | `POLICY_CREATE` | `pwm.policy.write` | Add an immutable policy reference usable by privacy boundaries. |
| `pwm.model.propose` | `MODEL_PROPOSE` | `pwm.model.propose` | Add a complete model candidate. |
| `pwm.model.review` | `MODEL_REVIEW` | `pwm.model.review` | Add one review of an existing proposal. |
| `pwm.model.accept` | `MODEL_ACCEPT` | `pwm.model.accept` | Materialize the unchanged approved candidate. |
| `pwm.model.update` | `MODEL_UPDATE` | `pwm.model.update` | Materialize an approved successor and supersede its predecessor. |
| `pwm.model.dispute` | `MODEL_DISPUTE` | `pwm.model.dispute` | Mark an accepted model disputed without deleting it. |
| `pwm.model.revoke` | `MODEL_REVOKE` | `pwm.model.revoke` | Mark an accepted or disputed model revoked. |
| `pwm.privacy-boundary.approve` | `PRIVACY_BOUNDARY_APPROVE` | `pwm.privacy-boundary.approve` | Add an approved proof/redaction boundary. |
| `pwm.privacy-boundary.revoke` | `PRIVACY_BOUNDARY_REVOKE` | `pwm.privacy-boundary.revoke` | Revoke an existing boundary. |
| `pwm.contradiction.propose` | `CONTRADICTION_PROPOSE` | `pwm.contradiction.propose` | Add a contradiction candidate retaining all inputs. |
| `pwm.contradiction.review` | `CONTRADICTION_REVIEW` | `pwm.contradiction.review` | Add a review of the candidate. |
| `pwm.contradiction.accept` | `CONTRADICTION_ACCEPT` | `pwm.contradiction.accept` | Materialize an approved contradiction. |
| `pwm.contradiction.resolve` | `CONTRADICTION_RESOLVE` | `pwm.contradiction.resolve` | Append a resolution; retain conflict and prior resolutions. |
| `pwm.topology.edge` | `TOPOLOGY_EDGE_CREATE` | `pwm.topology.edge` | Add an edge; `DEPENDS_ON` MUST remain acyclic. |
| `pwm.possible-world` | `POSSIBLE_WORLD_CREATE` | `pwm.possible-world.create` | Create an isolated non-actual world. |
| `pwm.query-authority` | `QUERY_AUTHORITY_GRANT` | `pwm.query-authority.grant` | Add bounded query authority. |
| `hpl.request` | `HPL_REQUEST_CREATE` | `hpl.request.create` | Add a purpose- and recipient-bound request. |
| `hpl.authorization` | `HPL_AUTHORIZE` | `hpl.authorization.create` | Authorize an existing request within query authority. |
| `hpl.projection` | `HPL_PROJECT` | `hpl.projection.create` | Add a minimized projection bound to an authorization. |
| `hpl.revoke` | `HPL_REVOKE` | `hpl.revoke` | Revoke an authorization or projection. |
| `pwm.conformance.evaluate` | `CONFORMANCE_EVALUATE` | `pwm.conformance.evaluate` | Record evaluation metadata; it cannot grant conformance. |

Unknown kinds fail with `UNSUPPORTED_EVENT_KIND`. Registered kinds with any schema version other than `1.0.0` fail with `UNSUPPORTED_SCHEMA_VERSION`. Wave01 fixture-only `pwm.merge` is not a semantic event in this profile.

## Deterministic queries

A query command supplies `authority_id`, `world_id`, `as_of_valid_ns`, `recipient_id`, `purpose`, requested `model_ids`, and `include_disputed`. `evaluation_log_sequence` MUST identify an existing receipt and evaluation uses only that inclusive log prefix. Authority MUST be active at that sequence, match scope, principal, recipient, purpose, world, families, subjects, perspectives, and privacy ceiling, and cover each selected model. Selection excludes revoked and superseded models and excludes disputed models unless requested and authorized. Results sort by raw UTF-8 bytes of model ID. Edges are returned only when both endpoints are selected and edge disclosure is authorized.

Effective privacy is the maximum of declared privacy and all evidence, dependency, edge, and derivation inputs under `PUBLIC < LOW < PERSONAL < SENSITIVE < HIGHLY_SENSITIVE`. Only an active approved boundary covering every input and released field may lower a projection's output class.

## Conformance decision

A source is accepted only when every record verifies and reduces and its command completes. Outputs MUST conform to `signed-semantic-output.schema.json`. Invalid suite cases MUST name exactly one expected stable error code selected using `semantic-error-precedence-v1.md`; accepting an invalid case, returning another code, or committing its invalid transition is a failure.

The normalized output is JSON, not a signed representation. It contains profile/output versions, source and implementation identity, decision, processed-record count, last committed sequence, state digest, and exactly one of `result` or `error`. Result contains the command operation and command value. Reducer maps become JSON objects; arrays use their normative semantic order; CBOR byte strings become an object containing exactly `{"$bytes_hex":"<lowercase hex>"}`; null, booleans, text, and integers retain their value. Floating-point output is forbidden at every depth.

`state_sha256` is lowercase hexadecimal SHA-256 of `"pwm:semantic-state:v1\0" || S`, where `S` is restricted deterministic CBOR for the complete reducer state after the last committed event. State map names are those in this document; each ID-keyed map is encoded as a map keyed by ID, histories are replay-ordered arrays, and all set-like arrays retain canonical item order. Rejected output has no result and reports the post-rejection state digest; the invalid case's `state_digest_unchanged` assertion compares it with the digest immediately before the rejected transition.

The suite trust anchor is copied exactly into each well-formed source; differing values make the source invalid. `suite.sha256` in a claim is SHA-256 over the exact bytes of the suite JSON file, without newline or JSON reserialization rules beyond the bytes actually distributed. Conformance is claimed only with `implementation-claim.schema.json`, all cases in that immutable suite passing, matching suite SHA-256, no skipped cases, and a semantic diff with no differences. A claim against this provisional profile MUST itself say `PROVISIONAL`.
