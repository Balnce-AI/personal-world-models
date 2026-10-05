# Authenticated Principals Profile v1

**Status:** `PROVISIONAL`

## Trust anchor and bootstrap

Each conformance suite declares exactly one immutable trust anchor `{key_id, public_key_hex}`, copied into every well-formed source. It is fixed before bundle processing, is part of the suite digest, and MUST NOT be learned from the bundle. The unique `pwm.genesis` EventBody for the source scope MUST name that `key_id`, verify with that public key, have no parents, have author sequence zero, and receive log sequence zero. A bundle cannot rotate or replace this trust anchor.

Genesis payload data creates the principal and grant registries. Its root grant is authorized by the trust-anchor signature itself. All subsequent authority is explicit; possession of an accepted Wave01 author key alone does not grant semantic authority.

## Grant tuple

A grant is the tuple:

```text
(grant_id, principal_id, key_id, scope_id, operations,
 capabilities, grant_class, valid_from_log_sequence,
 valid_to_log_sequence)
```

The tuple is immutable. Each registered non-genesis event has exactly one required operation and one required capability in `signed-semantic-conformance-v1.md`. An implementation MUST bind an event to exactly one authenticated principal by selecting grants where:

- `key_id == EventBody.author_key_id`;
- `scope_id == EventBody.principal_scope`;
- the required operation is in `operations`;
- every capability required by the payload is in `capabilities`;
- `valid_from_log_sequence <= receipt.log_sequence`; and
- `valid_to_log_sequence` is null or `receipt.log_sequence < valid_to_log_sequence`.

Zero matches yields `GRANT_NOT_FOUND`; matches for multiple different principals yield `PRINCIPAL_AMBIGUOUS`. Multiple matching grants for the same principal combine by union only for that event; they do not create a new persistent grant.

Grant class is an audit classification, not implied authority. Operations and capabilities are deny-by-default. Scope never widens through parentage, model references, HPL requests, or query authority.

## Grant changes

Version 1 permits grant creation only in genesis. A genesis may predeclare future grants by setting `valid_from_log_sequence` greater than zero and may predeclare expiry with `valid_to_log_sequence`. `PRINCIPAL_GRANT` and `PRINCIPAL_REVOKE` are reserved operation names but no post-genesis grant event kind is registered in this provisional version. Implementations MUST NOT invent one.

Wave01 key validity and semantic grant validity are independent and both are required. A key active in the verified key frontier but outside its grant interval fails `GRANT_NOT_ACTIVE`. A semantically active grant whose key is revoked in the receipt frontier fails at the earlier cryptographic key-status stage. Backdating `event_time` or `valid_from_ns` cannot restore either validity.

## Delegation and review separation

No transitive delegation is inferred. A principal can act only through a key named by a direct grant. Review separation is payload-specific: model and contradiction reviewers MUST differ from proposal authors unless the reviewer's matching grant contains `pwm.review.self`.

Query authority and HPL authorization are semantic records, not key grants. They narrow an already authenticated principal's operation and never substitute for a matching operation grant.
