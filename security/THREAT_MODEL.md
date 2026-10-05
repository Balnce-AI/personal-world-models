# Threat Model

Status: `PROPOSED` security baseline for an `EXPERIMENTAL`/`REFERENCE_IMPLEMENTATION` repository.

## Protected assets

- event closure, materialized world-model state and cryptographic keys;
- projection eligibility, privacy segments and policy;
- derived artifacts, behavioral models and possible-world separation;
- authority, delegation, revocation and consent state;
- identity, relationship, spatial and multimodal privacy;
- learning-return, model-lifecycle and provenance integrity;
- recipient/runtime identity, receipts and dependency metadata.

Trust boundaries include every adapter role, model/provider, device/actuator, external media substrate, transport peer, partial replica, package/build system and recipient. Capability discovery and attestation are evidence, not authority.

## Threats and controls

| Threat | Failure | Required controls |
|---|---|---|
| Malicious adapter | Over-collects, reinterprets fields or writes state | Narrow role protocol; exact versioned semantics; lifecycle/resource bounds; event-only writes; deny unknowns; sandbox where available |
| Compromised device | Forges observations or commands | Device identity/proof checks; source provenance; freshness; plausibility checks; local safety veto |
| Prompt/content injection | Evidence or media instructs a model/tool to bypass policy | Treat content as data; least-disclosure context; tool allowlist; output validation; authorization after inference |
| Evidence/model poisoning | Crafted input corrupts learned models | Provenance closure; source reliability; candidate/review lifecycle; contradiction and rollback paths; negative controls |
| Inference/model inversion | Output reveals withheld or training data | Projection minimization; privacy budgets/limits; output filtering; red-team extraction tests; no secret-bearing prompts |
| Dependency leakage | SDK, provider, telemetry, logs or exceptions export context | Dependency inventory; egress controls; redaction; local alternatives; no sensitive diagnostics; custody documentation |
| Stale authorization/revocation | Offline node acts after rights change | Expiry; revocation cursor; freshness policy; deny when stale; reconnect reconciliation |
| Replay | Valid old event, projection, window or command is reused | Nonce/sequence; causal parent checks; recipient/purpose/TTL binding; idempotency and replay cache |
| Malicious provider | Cloud/model/storage provider reads, alters or withholds data | Minimize/encrypt; digest/signature verification; replaceable provider; export/exit path; bounded availability claims |
| Unsafe actuator/tool | Authorized-looking output causes physical/digital harm | Separate effect authorization; argument constraints; confirmation; rate/energy limits; local interlock and safety veto |
| Schema/semantic confusion | Version or extension field changes meaning | Strict validation; namespace/version pinning; reject unknown semantics; migration ADR and conformance vectors |
| Supply-chain compromise | Package, build, model or fixture is substituted | Lockfiles/digests; provenance/SBOM; minimal dependencies; isolated build; review generated artifacts |
| Partial-replica inference | Omitted segments or metadata reveal sensitive facts | Segment encryption; cover/minimized metadata where needed; explicit omission; access-pattern analysis |
| Cross-world contamination | Hypothetical assumptions enter canonical state | Deeply isolated branches; explicit promotion/review; provenance label; no direct state mutation |
| External media attack | Parser exploit, oversized blob or swapped content | Reference digest; media/type/size limits; sandboxed decoder; fetch authorization; decompression bounds |
| Federation peer abuse | Peer floods, equivocates or requests excess data | Peer identity; quotas; causal validation; least-disclosure projection; quarantine; auditable receipts |
| Departure overclaim | Receipt implies unverifiable remote erasure | Bounded assurance vocabulary; evidence attached; distinguish protocol acknowledgement from verified deletion |

## Security invariants

- No adapter, model, foreign peer or simulation directly mutates canonical PWM state.
- No capability descriptor grants permission, trust or standards compliance.
- Authority is operation-, principal-, recipient-, purpose-, scope- and time-bound and deny-overrides.
- Durable stream promotion is distinct from observation and requires authorization plus provenance.
- Missing causal parents, unsupported semantics, stale revocation state and ambiguous identity fail closed.
- Physical actuation terminates behind independent local safety enforcement.

## Residual risks and proof obligations

The in-memory adapter is process-local and offers no encryption, durable recovery, multi-writer isolation or side-channel defense. Sync/federation is design-only. Provider deletion, remote execution and hardware attestation cannot prove more than their evidence. Production use requires deployment-specific abuse analysis, key management, parser sandboxing, limits, incident response, recovery tests and independent security review.
