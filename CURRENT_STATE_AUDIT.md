---
status: RESEARCH
audit_date: 2026-08-28
repository_version: 0.1.0
---

# Current State Audit

This document is the historical pre-reconstruction audit for repository version `0.1.0`. It is retained as migration evidence; current implementation and conformance status is recorded in `PLATFORM_STABILIZATION_STATUS.md`, `conformance/manifest.json`, and `governance/PUBLIC_CLAIM_LEDGER.json`.

## Scope and authority

This audit records the supplied public repository as observed before implementation work. It is governed by the published specifications and architectural invariants. It does not audit a production Balnce/Reasn repository because none was supplied in this workspace.

The following distinctions govern every finding:

- The PWM is the canonical semantic/materialized model; a foreign runtime receives only a purpose-bounded derivative.
- `PLog` is a small public provenance profile. It is not ordinary application logging, but it is also not the complete canonical Balnce PLOG/UOR substrate.
- SHA-256 URNs and event IDs in this repository are conventional public-reference identifiers, not UOR.
- Arranger is the signed crystallized artifact. Hyperframe is the canonical carrier and is not implemented here.
- Authority constraints are a compatibility profile for richer Covenant Atom composition, not a second authority system.
- HPL authorization does not replace machine-local or OEM safety.
- NEP means Neural Engine Protocol; UHR means Universal Host Runtime; neither is redefined here.

## Untouched baseline

| Check | Result |
|---|---|
| Repository VCS state | The supplied `public-repo/` directory is not a Git worktree. |
| Documented command | `python -m pytest -q` could not start because `python` is not installed on `PATH`. |
| Available interpreter | Python 3.14.5 via `python3`. |
| Isolated baseline | Dependencies were installed into an external temporary virtual environment; no repository package installation was required. |
| Test result | `9 passed in 0.72s`. |
| Test scope | Five reference behavior tests, three adapter tests, and one schema metaschema-validity test. |
| Important limitation | Passing tests do not establish generated-instance schema conformance, complete lifecycle enforcement, benchmark validity, production readiness, or canonical UOR/PLOG equivalence. |

## Required-path audit

| Required path | State | Consequence |
|---|---|---|
| `spec/status-taxonomy.md` | Missing | Root `STATUS.md` defines the taxonomy, but the mandated specification path does not exist. |
| `protocol/` | Missing | No protocol fixtures, wire profiles, or protocol conformance tests exist. |
| `experiments/` | Missing | Research claims are not organized as reproducible experiments. |
| `sim/` | Missing | No recipient, revocation, departure, offline, or physical-runtime simulator exists. |

## Status discipline

The repository declares itself `REFERENCE_IMPLEMENTATION + RESEARCH`. All eight present specifications are `PROPOSED`. The mathematical documents are `PROPOSED`, `RESEARCH`, or, for the bounded authority algebra, `REFERENCE_IMPLEMENTATION`. The implemented HCP, COVESA VSS, and WoT adapter READMEs are `EXPERIMENTAL`; ROS 2 and SOVD are `PROPOSED`; MHS is `RESEARCH`.

Most Python modules, schemas, tests, benchmark files, security documents, diagrams, and some research documents do not declare a taxonomy status. This conflicts with `STATUS.md`, which requires every significant module, benchmark, adapter, and claim to declare one. Code existence and a passing test suite do not justify upgrading any status.

## Executable module inventory

### `src/pwm_hpl_ref/__init__.py`

- **Purpose:** package version marker.
- **Observed status:** undeclared; repository context supports only `REFERENCE_IMPLEMENTATION`.
- **Public interface:** `__version__ = "0.1.0"`.
- **Dependencies:** none.
- **Tests:** none directly.
- **Known incompleteness:** duplicates the version in `pyproject.toml`; no explicit public export surface.
- **Specification / benchmark:** repository-level profile; no direct benchmark.

### `src/pwm_hpl_ref/canonical.py`

- **Purpose:** stable JSON-byte encoding and conventional SHA-256 URN generation.
- **Observed status:** undeclared; bounded reference utility.
- **Public interface:** `canonical_json(value) -> bytes`; `sha256_urn(namespace, value) -> str`.
- **Dependencies:** Python `json` and `hashlib`.
- **Tests:** indirect through event, projection, Arranger, receipt, and tamper tests.
- **Known incompleteness:** not RFC 8785/JCS; permits non-standard floating-point values; lacks Unicode and numeric normalization; namespace is unchecked; no direct test vectors.
- **Specification / benchmark:** `spec/pwm-core.md`; `math/uor-proof-status.md`; no benchmark.

### `src/pwm_hpl_ref/plog.py`

- **Purpose:** in-memory provenance-bearing event DAG profile.
- **Observed status:** undeclared; `REFERENCE_IMPLEMENTATION`, not canonical PLOG.
- **Public interface:** `Event`; `PLog.append(...) -> Event`; `PLog.ordered(at_time=None) -> list[Event]`.
- **Dependencies:** `canonical.sha256_urn`.
- **Tests:** indirect through materialization and HPL-CONTEXT.
- **Known incompleteness:** mutable payloads after hashing; no parent validation, cycle checks, signatures, persistence, schema enforcement, authorized closure, or certificate chain; ordering is lexical chronological order rather than guaranteed DAG-topological order; malformed timestamps are accepted.
- **Specification / benchmark:** `spec/pwm-core.md`, `spec/projection-lifecycle.md`; HPL-CONTEXT indirectly.

### `src/pwm_hpl_ref/pwm.py`

- **Purpose:** materialize entity, relation, assertion, and policy state from the public PLOG profile.
- **Observed status:** undeclared; `REFERENCE_IMPLEMENTATION` within a narrow event vocabulary.
- **Public interface:** `PWMState`; `Materializer.materialize(plog, at_time=None) -> PWMState`.
- **Dependencies:** `plog.PLog`.
- **Tests:** `test_materialization_is_deterministic`; projection test and benchmark indirectly.
- **Known incompleteness:** only five event types; unknown events are silently marked applied; no valid-time evaluation, conflict profile, supersession semantics, authorized closure, schema version, checkpoint validation, relation/entity/policy revocation, or referential integrity. The determinism test repeats one in-memory fixture rather than varying insertion order or implementation.
- **Specification / benchmark:** `spec/pwm-core.md`; `math/pwm-formal-model.md`; partial HPL-CONTEXT support.

### `src/pwm_hpl_ref/authority.py`

- **Purpose:** deny-overrides and scoped-grant capability resolution.
- **Observed status:** undeclared in code; bounded `REFERENCE_IMPLEMENTATION` in `math/authority-algebra.md`.
- **Public interface:** `Constraint`; `Decision`; `AuthorityEngine.resolve(requested, constraints) -> Decision`.
- **Dependencies:** standard library only.
- **Tests:** `test_deny_overrides_grant`; projection test indirectly.
- **Known incompleteness:** `MANDATORY_CLASSES` is unused; no mandate, scope, time, jurisdiction, evidence, delegation, identity, obligation, or local-state evaluation; unknown effects are ignored; implicit no-grant denials lack reasons. This is not a Covenant Atom replacement.
- **Specification / benchmark:** `spec/multi-principal-governance.md`; `math/authority-algebra.md`; HPL-AUTH is not implemented.

### `src/pwm_hpl_ref/projection.py`

- **Purpose:** select assertions by requested predicate and maximum privacy class, then emit a projection manifest.
- **Observed status:** undeclared; narrow `REFERENCE_IMPLEMENTATION`.
- **Public interface:** `ProjectionRequest`; `ProjectionCompiler.compile(state, request, authority) -> dict`.
- **Dependencies:** `PWMState`, `Decision`, `sha256_urn`.
- **Tests:** `test_projection_minimizes_and_excludes_sensitive_zone`; HPL-CONTEXT.
- **Known incompleteness:** no utility threshold, representation/rung selection, field policy, recipient identity proof, environment evidence, compatibility, spatial clipping, pseudonymization, or uncertainty propagation; does not bind the authority decision to the exact request; omits field-local IDs, times, privacy, and provenance; accepts negative TTL.
- **Specification / benchmark:** `spec/hpl-core.md`, `spec/projection-lifecycle.md`, `spec/spatial-projection.md`; partial HPL-CONTEXT only.

### `src/pwm_hpl_ref/crypto.py`

- **Purpose:** Ed25519 key generation and signatures over the local JSON encoding.
- **Observed status:** undeclared; reference cryptographic utility.
- **Public interface:** `generate_keypair()`; `sign_json(private_key, value) -> str`; `verify_json(public_key, value, signature) -> bool`.
- **Dependencies:** `cryptography`; `canonical.canonical_json`.
- **Tests:** Arranger tamper test indirectly.
- **Known incompleteness:** no key identifiers, serialization, rotation, trust resolution, secure storage, algorithm metadata, domain separation, or direct vectors; verification collapses all errors to `False`.
- **Specification / benchmark:** supports Arranger and broadcast contracts; no dedicated spec or benchmark.

### `src/pwm_hpl_ref/arranger.py`

- **Purpose:** issue and signature-check a recipient/purpose-bound Arranger manifest.
- **Observed status:** undeclared; partial `REFERENCE_IMPLEMENTATION`.
- **Public interface:** `ArrangerIssuer.issue(...)`; `ArrangerIssuer.verify(public_key, artifact)`.
- **Dependencies:** `sha256_urn`, `sign_json`, `verify_json`, Ed25519 key objects.
- **Tests:** `test_arranger_signature_detects_tamper`.
- **Known incompleteness:** no Hyperframe carrier; no expiry, recipient, nonce, revocation, payload-hash, schema, or compatibility enforcement; required allowed/forbidden capabilities, runtime/model/hardware binding, and learning-return policy are absent; TTL may be negative.
- **Specification / benchmark:** `spec/arranger.md`, `spec/projection-lifecycle.md`; no lifecycle benchmark.

### `src/pwm_hpl_ref/learning.py`

- **Purpose:** construct a foreign learning candidate without mutating canonical PWM state.
- **Observed status:** undeclared; skeletal `REFERENCE_IMPLEMENTATION`.
- **Public interface:** `learning_candidate(source, claim, confidence, session_artifact, requires_review=True)`.
- **Dependencies:** `sha256_urn`.
- **Tests:** none.
- **Known incompleteness:** unsigned and unauthenticated; no schema validation, poisoning controls, deduplication, replay defense, review workflow, or reconciliation event; callers can disable review.
- **Specification / benchmark:** `spec/hpl-core.md`, lifecycle RECONCILE phase; no benchmark.

### `src/pwm_hpl_ref/departure.py`

- **Purpose:** create a receipt labeled with one of six evidence tiers.
- **Observed status:** undeclared; incomplete `REFERENCE_IMPLEMENTATION`.
- **Public interface:** `LEVELS`; `make_receipt(session_id, artifact_id, recipient, level, evidence)`.
- **Dependencies:** `sha256_urn`.
- **Tests:** `test_departure_receipt_is_bounded_claim` checks only the label.
- **Known incompleteness:** arbitrary evidence can support any level; receipts are unsigned; no recipient or attestation verification. Emitted `receiptId` is rejected by the current schema because it is undeclared while `additionalProperties` is false. `PROTOCOL_DEPARTURE` therefore does not yet meet the specification's signed-acknowledgement requirement.
- **Specification / benchmark:** `spec/departure-assurance.md`; HPL-RESIDUE is absent.

### `src/pwm_hpl_ref/web0.py`

- **Purpose:** issue and signature-check typed machine broadcasts.
- **Observed status:** undeclared; skeletal `REFERENCE_IMPLEMENTATION`.
- **Public interface:** `KINDS`; `issue_broadcast(...)`; `verify_broadcast(...)`.
- **Dependencies:** `sha256_urn`, Ed25519 JSON signing.
- **Tests:** none.
- **Known incompleteness:** verification checks signature only; no ID recomputation, expiry, replay, identity/key resolution, revocation, discovery, network protocol, or payload validation. A capability broadcast is evidence, not authorization.
- **Specification / benchmark:** public interface profile; no benchmark.

### `src/pwm_hpl_ref/demo.py`

- **Purpose:** compose the current event-to-projection-to-artifact demonstration.
- **Observed status:** repository example declares `REFERENCE_IMPLEMENTATION`.
- **Public interface:** `build_fixture()`; CLI `main()` via `pwm-hpl-demo`.
- **Dependencies:** all reference modules except adapter modules.
- **Tests:** fixture functions support reference tests; `main()` is not tested end to end.
- **Known incompleteness:** no Hyperframe transport, foreign runtime consumer, local safety decision, revocation/expiry, signed departure, or learning reconciliation; generated output is nondeterministic and is not schema-validated; fixture assertions omit schema-required `recordTime`.
- **Specification / benchmark:** integrates the core specifications; HPL-CONTEXT only.

## Adapter inventory

| Adapter | Declared status | Public interface | Tests | Dependencies and incompleteness | Governing evidence |
|---|---|---|---|---|---|
| `adapters/hcp/adapter.py` | `EXPERIMENTAL` in README | `projection_to_preference_records(projection)` | `test_hcp_mapping_is_scoped` | No pinned HCP version/schema, validation, transport, identity, or conflict semantics; projection-wide provenance is copied to every record. | `standards/hcp-mapping.md`. |
| `adapters/covesa-vss/adapter.py` | `EXPERIMENTAL` in README | `DEFAULT_MAP`; `map_signal(vss_path, value, mapping=None)` | `test_vss_unknown_fails_semantically_closed` | Three paths only; no VSS version, units, types, VISS transport, timestamp, or conversion; unknown semantics correctly remain unknown. | `standards/covesa-mapping.md`. |
| `adapters/wot/adapter.py` | `EXPERIMENTAL` in README | `thing_description_capabilities(td)` | `test_wot_affordances_are_evidence_not_authority` | No TD validation, JSON-LD context, forms, operations, security definitions, versions, or protocol binding. | `standards/wot-mapping.md`. |
| `adapters/ros2/` | `PROPOSED` | Documentation only | None | No actions/services/messages, QoS, node identity, safety integration, or runtime fixture. | `standards/ros2-mapping.md`. |
| `adapters/sovd/` | `PROPOSED` | Documentation only | None | No normative version, parser, endpoint profile, authorization, transport, or fixture. | Vehicle support example. |
| `adapters/mhs/` | `RESEARCH` | Documentation only | None | Normative artifacts are unavailable/unreviewed; compatibility claims are correctly withheld. | `standards/mhs-mapping.md`. |

## Public schema inventory

All JSON Schemas are structurally valid Draft 2020-12 schemas under the current test, but none declares repository maturity or profile version, all use `example.org` identifiers, and no generated instance is validated in tests.

| Contract | File | Implementation correspondence | Material gap |
|---|---|---|---|
| PWM Entity | `schemas/json-schema/pwm-entity.schema.json` | `PWMState.entities` | No runtime validation or typed serializer. |
| PWM Relation | `schemas/json-schema/pwm-relation.schema.json` | `PWMState.relations` | No runtime validation or referential integrity. |
| PWM Assertion | `schemas/json-schema/pwm-assertion.schema.json` | `PWMState.assertions` | Demo omits required `recordTime`; valid-time shape is weak. |
| PLOG Event | `schemas/json-schema/plog-event.schema.json` | `plog.Event` | CamelCase/snake_case mismatch; no serializer. |
| Projection Manifest | `schemas/json-schema/projection-manifest.schema.json` | `ProjectionCompiler` output | No instance conformance tests; weak field typing. |
| Arranger Manifest | `schemas/json-schema/arranger-manifest.schema.json` | `ArrangerIssuer` output | Proposed required bindings are absent or optional. |
| Authority Constraint | `schemas/json-schema/authority-constraint.schema.json` | `authority.Constraint` | Python omits time, jurisdiction, and evidence. |
| Learning Candidate | `schemas/json-schema/learning-candidate.schema.json` | `learning_candidate` output | No signature/source-integrity contract. |
| Departure Receipt | `schemas/json-schema/departure-receipt.schema.json` | `make_receipt` output | Current output fails schema due to `receiptId`. |
| Machine Broadcast | `schemas/json-schema/machine-broadcast.schema.json` | `web0` output | No enforced key/algorithm/expiry/replay contract. |
| TypeScript profile | `schemas/typescript/index.ts` | Four selected interfaces | Missing most advertised public objects; confidence differs from JSON Schema. |

The `PROPOSED` public interface also promises Projection Request and Capability Mapping Record, but neither has a JSON Schema or TypeScript interface. NormativeObject, IntentionalObject, ProvenanceReference, ProjectionReference, compatibility binding, learning-return policy, revocation operations, and departure proof profiles are likewise not machine-readable.

## Test and benchmark inventory

| Evidence module | Status | What it establishes | What it does not establish |
|---|---|---|---|
| `tests/test_reference.py` | Undeclared | Basic repeated materialization, privacy exclusion, deny-overrides, Arranger tamper detection, and departure-level labeling. | DAG validity, temporal semantics, schema conformance, expiry, replay, revocation, local safety, learning reconciliation, or full end-to-end behavior. |
| `tests/test_adapters.py` | Undeclared | Three narrow adapter invariants. | Upstream standards conformance, malformed inputs, positive/negative profile breadth, packaging behavior, ROS 2/SOVD/MHS. |
| `tests/test_schemas.py` | Undeclared | Every JSON Schema is a valid Draft 2020-12 schema. | Any implementation output conforms to a schema. |
| `benchmarks/hpl-context/run.py` | Undeclared; experimental evidence | Counts two disclosed assertions from three fixture assertions. | Task utility, a baseline, pass/fail threshold, uncertainty, adversarial leakage, repeatability, or minimality. |
| `benchmarks/results/hpl-context-smoke.txt` | Undeclared evidence artifact | Captures a disclosure ratio of 2/3. | Versioned/reproducible benchmark provenance. |
| HPL-AUTH/SPATIAL/RESIDUE/LEAKAGE/DRIFT/HANDOFF/OFFLINE | Planned | Names research obligations. | No harnesses or results exist. |

The README claim that initial harnesses cover disclosure minimization, authority, residue, and portability exceeds the repository evidence. Only the disclosure-count smoke harness exists; authority and departure have unit tests, not benchmark harnesses.

## Specification, mathematics, security, and standards evidence

| Area | Files/status | Current evidence | Primary incompleteness |
|---|---|---|---|
| Core specifications | Seven present requested specs plus `public-interface-profile.md`, all `PROPOSED` | Clear definitions and invariants. | `spec/status-taxonomy.md` missing; schemas and code do not satisfy all proposed requirements. |
| Formal PWM | `math/pwm-formal-model.md`, `confidence-and-time.md`, `PROPOSED` | Defines interfaces and rejects universal confidence decay. | No executable temporal/conflict model or calibration experiment. |
| Projection objective | `math/projection-operator.md`, `RESEARCH` | Defines leakage/persistence/dependency objective under constraints. | Metrics and utility are not operationalized. |
| Authority algebra | `math/authority-algebra.md`, `REFERENCE_IMPLEMENTATION` | Bounded scoped grant minus denial algebra. | Not general legal/contractual composition. |
| UOR proof status | `math/uor-proof-status.md`, `RESEARCH` | Separates a proved finite-ring identity from restricted propositions, conjectures, and counterexamples. | No executable proof/counterexample suite; no public implementation of canonical UOR. |
| Threat model | `security/THREAT_MODEL.md`, undeclared | Identifies assets, adversaries, and required controls. | Most lifecycle controls are fields only, not enforced. |
| Trust assumptions | `security/TRUST_ASSUMPTIONS.md`, undeclared | Correctly bounds opaque deletion, signatures, attestation, safety, and root compromise. | No recovery or assurance implementation. |
| Standards mappings | HCP/ROS/COVESA/WoT `PROPOSED`; MHS `RESEARCH` | Correct adapter boundary posture. | No pinned upstream versions, hashes, licenses, normative URLs, or conformance suites. |
| Public claim evidence | README, papers, and release documents, mixed/undeclared | Major claims identify broad evidence categories and caveats. | No public claim index consistently records sources, reviewers, dates, and falsifiers. |
| Papers | Two `PROPOSED` outlines | PWM paper includes a falsifier. | No experiments, datasets, results, bibliography, or HPL-level falsifier. |

## Examples and demonstrations

| Example | Declared status | Execution evidence | Gap |
|---|---|---|---|
| Robot kitchen delivery | `REFERENCE_IMPLEMENTATION` | Uses `pwm_hpl_ref.demo`; component tests cover selected pass conditions. | No foreign runtime, local safety, transport, revocation, cleanup, or reconciliation simulation. |
| Vehicle service support | `PROPOSED` | Documentation only; can reference Web0 and VSS primitives. | No SOVD flow, multi-party authorization, runtime, or outcome test. |
| Fleet authority conflict | `PROPOSED` | One generic deny-overrides unit test overlaps the idea. | The README says a test exists, but no complete fleet scenario test exists. |
| Generated demo output | Undeclared evidence artifact | Shows projection, Arranger, candidate, receipt, and broadcast shapes. | Nondeterministic, not schema-tested, and contains the invalid departure-receipt field. |

## Security control matrix

| Control | Present | Enforced |
|---|---|---|
| Ed25519 Arranger and broadcast signatures | Yes | Signature validity only. |
| Recipient and purpose fields | Yes | Not cryptographically resolved or policy-checked during verification. |
| TTL fields | Yes | No expiry enforcement. |
| Nonce | Arranger only | No replay cache or consumption. |
| Revocation handle | Arranger only | No registry or revocation operation. |
| Payload hash | Arranger only | Not recomputed against supplied payload. |
| Privacy/predicate minimization | Basic | Predicate and class threshold only. |
| Deny-by-default capability result | Basic | No temporal/jurisdiction/evidence enforcement. |
| Learning-return quarantine | Candidate construction | No authenticated review/reconciliation path. |
| Departure assurance | Tier vocabulary | No evidence-profile or signature verification. |
| Local safety veto | Documented | No executable foreign-runtime interface. |

## Current-state conclusion

The repository is a coherent, small public reference demonstration with careful conceptual boundaries. It can materialize a limited state from provenance-profile events, filter a projection, resolve a conservative capability set, sign an Arranger-shaped artifact, and produce candidate/receipt/broadcast records. The untouched tests pass.

It does not yet satisfy the stated first milestone end to end: no schema-conformant provenance-to-state contract, foreign reference runtime, Hyperframe-compatible carrier boundary, enforced artifact lifecycle, authenticated departure evidence, or accepted learning reconciliation exists. The largest risk is assurance mismatch: security-bearing fields and public claims are broader than their enforcement and benchmark evidence.
