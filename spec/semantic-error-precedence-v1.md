# Semantic Error Codes and Precedence v1

**Status:** `PROVISIONAL`

An implementation MUST expose exactly one stable code for a rejected conformance case. It MAY retain implementation-local diagnostics, but diagnostics MUST NOT change the selected code. Validation stops at the first failing precedence class below. Within a class, use the listed order; for repeated records, inspect receipt `log_sequence` order, then field paths by UTF-8 byte order.

## Normative precedence

| Order | Stable code | Condition |
|---:|---|---|
| 1 | `SOURCE_SCHEMA_INVALID` | Suite source JSON does not conform to its schema. |
| 2 | `CBOR_INVALID` | CBOR is malformed or outside the restricted value space. |
| 3 | `CBOR_NON_CANONICAL` | Decodes but violates deterministic encoding or exact re-encoding. |
| 4 | `CID_INVALID` | CID text/binary/type is malformed or non-canonical. |
| 5 | `CID_MISMATCH` | Recomputed typed CID differs. |
| 6 | `PUBLIC_KEY_INVALID` | Key bytes are malformed, non-canonical, or weak. |
| 7 | `SIGNATURE_INVALID` | Author or appender signature does not verify. |
| 8 | `KEY_FRONTIER_INVALID` | Frontier construction, activation, revocation, or receipt binding is invalid. |
| 9 | `RECEIPT_INVALID` | Receipt body, appender binding, retry, or log sequence is invalid. |
| 10 | `PARENT_INVALID` | Missing, duplicate, unsorted, cross-scope, or otherwise invalid parent. |
| 11 | `AUTHOR_SEQUENCE_INVALID` | Author sequence is non-contiguous or prior event is not ancestral. |
| 12 | `REPLAY_CYCLE` | Verified parent graph contains a cycle. |
| 13 | `ROOT_TRUST_MISMATCH` | Genesis is absent, duplicated, not first, or not signed by fixed anchor. |
| 14 | `UNSUPPORTED_EVENT_KIND` | Event kind is not in the signed semantic registry. |
| 15 | `UNSUPPORTED_SCHEMA_VERSION` | Event or payload version is unsupported. |
| 16 | `PAYLOAD_ENVELOPE_INVALID` | Payload is not the exact semantic envelope or has invalid validity bounds. |
| 17 | `PAYLOAD_FIELD_INVALID` | Event data has missing, extra, ill-typed, unsorted, duplicate, floating, or non-normalized fields. |
| 18 | `GRANT_NOT_FOUND` | No grant binds key, scope, and required operation. |
| 19 | `GRANT_NOT_ACTIVE` | A matching grant exists but receipt sequence is outside its interval. |
| 20 | `PRINCIPAL_AMBIGUOUS` | Matching grants authenticate different principals. |
| 21 | `CAPABILITY_NOT_GRANTED` | Operation grant exists but a required capability does not. |
| 22 | `REFERENCE_NOT_FOUND` | A semantic reference does not resolve in committed prefix state. |
| 23 | `IDENTIFIER_CONFLICT` | A created identifier already exists or linked IDs disagree. |
| 24 | `LIFECYCLE_PRECONDITION_MISSING` | Required proposal, approval, current status, or predecessor is absent. |
| 25 | `REVIEW_SEPARATION_VIOLATION` | Unauthorized self-review is attempted. |
| 26 | `FAMILY_KIND_NOT_ALLOWED` | Model family/kind/subject cardinality is invalid. |
| 27 | `WORLD_SCOPE_VIOLATION` | Actual and possible-world state is mixed or base/world binding is invalid. |
| 28 | `TOPOLOGY_CYCLE` | A `DEPENDS_ON` edge would create a cycle. |
| 29 | `PRIVACY_EFFECTIVE_CLASS_MISMATCH` | Claimed effective class differs from required join/boundary result. |
| 30 | `AUTHORITY_SCOPE_VIOLATION` | Query or HPL authority does not cover scope, principal, recipient, purpose, world, subjects, perspective, family, models, or fields. |
| 31 | `AUTHORITY_EXPIRED` | Otherwise matching query/HPL authority is outside receipt/evaluation validity. |
| 32 | `COMMAND_UNSUPPORTED` | Adapter command is not registered. |
| 33 | `OUTPUT_SCHEMA_INVALID` | Adapter cannot produce a conforming normalized output. |
| 34 | `INTERNAL_ERROR` | No preceding public class represents an unexpected failure. This code never satisfies an invalid-case expectation for another code. |

Cryptographic and provenance failures therefore always precede semantic failures. Implementations MUST NOT decode semantic meaning to replace a cryptographic error with a later semantic code. Shape/version checks precede authorization so malformed content does not become an authority oracle; authorization precedes state-dependent semantic effects.
