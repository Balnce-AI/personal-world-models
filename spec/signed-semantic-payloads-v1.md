# Signed Semantic Payload Registry v1

**Status:** `PROVISIONAL`
**Profile:** `pwm-signed-semantics-v1`

This document defines the exact `data` map for each signed semantic event. Every map is closed: unlisted fields are forbidden. All IDs are NFC text. Every provenance reference ending in `_event_cid` is a canonical Wave01 event-body CID byte string. Lists named below are non-empty canonical sets unless stated otherwise.

## Common vocabularies

- Privacy: `PUBLIC`, `LOW`, `PERSONAL`, `SENSITIVE`, `HIGHLY_SENSITIVE`.
- Model kind: `SELF`, `OTHER`, `RELATIONSHIP`, `WORLD`, `META`, `POSSIBLE_WORLD`.
- Review decision: `APPROVE`, `REJECT`.
- Edge type: `DEPENDS_ON`, `CONSTRAINED_BY`, `INFORMED_BY`, `UNCERTAINTY_SOURCE`, `SUPERSEDES`.
- Contradiction type: `ASSERTION_CONFLICT`, `MODEL_CONFLICT`, `UNCERTAINTY`, `TEMPORAL_CHANGE`, `PERSPECTIVE_DISAGREEMENT`, `GENUINE_CONTRADICTION`.
- Resolution status: `OPEN`, `EXPLAINED`, `SUPERSEDED`, `RESOLVED`, `IRREDUCIBLE`, `PERSPECTIVE_DEPENDENT`.
- Boundary kind: `REDACTION`, `PROOF`.
- Grant operation is one of the operation names in the event registry, plus `PRINCIPAL_GRANT` and `PRINCIPAL_REVOKE` for genesis delegation records.
- Grant class: `ROOT`, `ADMINISTRATIVE`, `AUTHOR`, `REVIEWER`, `QUERY`, `HPL`, `EVALUATOR`.
- Capability: an NFC namespaced token matching `[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+`.
- Family: an NFC namespaced token with the same syntax as capability. Version 1 has no mutable family registry; the generic kind and subject-cardinality rules below are the only standard family/kind restrictions.

`properties` and `value` below are restricted-CBOR maps whose recursively contained values are null, boolean, integer, text, byte string, array, or map. Floats and tags are forbidden. Portable reducers compare their canonical CBOR bytes, not host-language object identity.

## Bootstrap and evidence

### `pwm.genesis`

Exactly `scope_id`, `root_principal_id`, `root_key_id`, `principals`, and `grants`.

- `scope_id` MUST equal `EventBody.principal_scope`; `root_key_id` MUST equal `EventBody.author_key_id` and the source's fixed root key ID.
- `principals` is a non-empty canonical set of `{principal_id, principal_class}`. Classes are `PERSON`, `ORGANIZATION`, `AGENT`, `SERVICE`, `EVALUATOR`.
- `grants` is a non-empty canonical set of `{grant_id, principal_id, key_id, scope_id, operations, capabilities, grant_class, valid_from_log_sequence, valid_to_log_sequence}`. `operations` and `capabilities` are canonical sets. `valid_to_log_sequence` is unsigned integer or null and, when present, is greater than `valid_from_log_sequence`.
- Genesis MUST include a `ROOT` grant for the root principal and key, valid from receipt sequence zero, covering every operation and required capability used by the bundle. Genesis is the only bootstrap exception to prior grant authorization. There MUST be exactly one genesis in a scope and its receipt sequence MUST be zero.

### `pwm.evidence`

Exactly `evidence_id`, `evidence_kind`, `subject_ids`, `source_uri`, `content_digest`, `privacy_class`, and `properties`. `content_digest` is a 32-byte SHA-256 byte string. `source_uri` may be null. Evidence is immutable and IDs are unique.

### `pwm.policy`

Exactly `policy_id`, `policy_profile`, `content_digest`, `privacy_floor`, and `properties`. `content_digest` is a 32-byte SHA-256 byte string. Policies are immutable in version 1; replacement requires a distinct ID. A privacy-boundary event MUST reference an existing policy ID.

## Model lifecycle

### `pwm.model.propose`

Exactly `proposal_id`, `model_id`, `family`, `kind`, `subject_ids`, `perspective_id`, `world_id`, `evidence_ids`, `declared_privacy_class`, `properties`, and `confidence`. `perspective_id` is text or null. `confidence` is fixed-point in `[0,1]`. References MUST exist. `RELATIONSHIP` requires at least two subjects; `SELF` requires one subject equal to the authenticated principal; `POSSIBLE_WORLD` requires a non-actual world.

### `pwm.model.review`

Exactly `review_id`, `proposal_id`, `reviewer_principal_id`, `decision`, and `reason`. Reviewer MUST equal the authenticated principal and MUST NOT be the proposal author unless its grant has capability `pwm.review.self`.

### `pwm.model.accept`

Exactly `model_id`, `proposal_id`, and `review_id`. The IDs MUST identify the same candidate, the review decision MUST be `APPROVE`, and no model with `model_id` may already be materialized. Materialized fields are copied byte-for-byte from the candidate; acceptance cannot override them.

### `pwm.model.update`

Exactly `model_id`, `previous_model_id`, `proposal_id`, and `review_id`. It has acceptance preconditions, requires a current predecessor in the same family, kind, subjects, perspective, and world, creates a distinct model ID, and marks the predecessor `SUPERSEDED`.

### `pwm.model.dispute`

Exactly `model_id`, `reason`, and `evidence_ids`. The target MUST be current and accepted. It becomes `DISPUTED` and remains historical/queryable only when explicitly included.

### `pwm.model.revoke`

Exactly `model_id` and `reason`. The target MUST be `ACCEPTED` or `DISPUTED`; it becomes `REVOKED`.

## Privacy boundary

### `pwm.privacy-boundary.approve`

Exactly `boundary_id`, `boundary_kind`, `policy_id`, `source_ids`, `input_privacy_class`, `output_privacy_class`, `released_fields`, `approver_principal_id`, and `expires_at_log_sequence`. The approver MUST be authenticated. Sources and policy MUST resolve. The input class MUST cover the join of all sources; output MUST be no higher than input; fields are canonical JSON-pointer-like paths beginning `/`; expiry is unsigned integer or null.

### `pwm.privacy-boundary.revoke`

Exactly `boundary_id` and `reason`. The active boundary becomes `REVOKED` and cannot authorize later projections.

## Contradictions

### `pwm.contradiction.propose`

Exactly `proposal_id`, `contradiction_id`, `contradiction_type`, `reference_ids`, `world_id`, `evidence_ids`, and `explanation`. At least two distinct references MUST resolve in the same world. Creation does not affect accepted contradiction state.

### `pwm.contradiction.review`

Exactly `review_id`, `proposal_id`, `reviewer_principal_id`, `decision`, and `reason`, with the same reviewer rules as model review.

### `pwm.contradiction.accept`

Exactly `contradiction_id`, `proposal_id`, and `review_id`. IDs MUST agree and review MUST approve. Materialization copies the candidate and sets status `OPEN`.

### `pwm.contradiction.resolve`

Exactly `resolution_id`, `contradiction_id`, `status`, `resolver_principal_id`, `explanation`, and `evidence_ids`. Resolver MUST be authenticated; status MUST not be `OPEN`; source references and prior resolutions remain unchanged.

## Topology, worlds, and query authority

### `pwm.topology.edge`

Exactly `edge_id`, `source_model_id`, `target_model_id`, `edge_type`, `world_id`, `evidence_ids`, and `declared_privacy_class`. Endpoints MUST exist in the named world and be distinct. Duplicate IDs fail. Adding `DEPENDS_ON` MUST not create a directed cycle.

### `pwm.possible-world`

Exactly `world_id`, `parent_world_id`, `base_state_cid`, `base_time_ns`, `declared_privacy_class`, and `purpose`. `world_id` MUST not be `world:actual`, parent MUST exist, and `base_state_cid` is a 32-byte semantic state SHA-256 digest. Creation deep-copies the parent's visible state at the referenced base and future mutations remain world-local.

### `pwm.query-authority`

Exactly `authority_id`, `principal_id`, `recipient_id`, `purpose`, `world_ids`, `subject_ids`, `perspective_ids`, `families`, `privacy_ceiling`, `allow_disputed`, `valid_from_log_sequence`, and `valid_to_log_sequence`. Scope is inherited from `EventBody`. Empty `perspective_ids`, `families`, or `subject_ids` means none, not wildcard. `world_ids` is non-empty. Validity uses receipt sequence and the upper bound is exclusive.

## HPL lifecycle

### `hpl.request`

Exactly `request_id`, `requester_principal_id`, `recipient_id`, `purpose`, `world_id`, `model_ids`, `requested_fields`, `maximum_privacy_class`, `retention_until_ns`, and `capabilities`. Requester MUST be authenticated; models and world MUST resolve.

### `hpl.authorization`

Exactly `authorization_id`, `request_id`, `query_authority_id`, `authorizer_principal_id`, `allowed_model_ids`, `allowed_fields`, `privacy_ceiling`, and `valid_to_log_sequence`. Request, authority, recipient, purpose, and world MUST agree. Allowed sets MUST be subsets of the request and authority. Authorizer MUST be authenticated.

### `hpl.projection`

Exactly `projection_id`, `authorization_id`, `recipient_id`, `purpose`, `world_id`, `model_ids`, `released_fields`, `effective_privacy_class`, `boundary_ids`, `content_digest`, and `expires_at_ns`. Authorization MUST be active at receipt sequence. Recipient, purpose, world, models, and fields MUST be authorized. `content_digest` is 32 bytes. Effective privacy MUST equal the computed join after active boundaries. Projection data itself is not embedded in this event.

### `hpl.revoke`

Exactly `target_type`, `target_id`, and `reason`; `target_type` is `AUTHORIZATION` or `PROJECTION`. The active target becomes `REVOKED`; descendants cannot be newly issued.

## Conformance evaluation

### `pwm.conformance.evaluate`

Exactly `evaluation_id`, `suite_id`, `suite_version`, `suite_sha256`, `implementation_id`, `implementation_version`, `passed_case_ids`, `failed_case_ids`, and `evaluated_at_ns`. Digest is 32 bytes and case ID sets are canonical and disjoint. This is evidence metadata only. It MUST NOT mutate grants or convert a provisional profile into stable status.
