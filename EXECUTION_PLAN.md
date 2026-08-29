---
status: PROPOSED
plan_date: 2026-08-28
repository_version: 0.1.0
---

# PWM/HPL Reference Milestone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a reproducible public Personal World Model that is materialized from provenance-bearing events, queried at a point in time, minimally projected under bounded authority, packaged as a lifecycle-enforced Arranger artifact, consumed by a non-authoritative foreign runtime, and returned or revoked with evidence.

**Architecture:** Harden the existing center-out reference path rather than adding parallel primitives. Conventional public identifiers remain explicitly non-UOR; the public PLOG profile remains provenance rather than generic logging; Arranger remains an artifact rather than a carrier; authority remains Covenant-compatible; foreign execution and local safety remain outside canonical PWM authority.

**Tech Stack:** Python 3.11+, pytest, JSON Schema Draft 2020-12, TypeScript declarations, Ed25519 via `cryptography`, Markdown specifications, deterministic JSON fixtures.

---

## Execution rules

- Do not start a task until every predecessor in `IMPLEMENTATION_GRAPH.md` passes.
- Use test-driven development for behavior changes: failing test, minimal implementation, focused pass, full-suite pass.
- Keep statuses unchanged unless evidence satisfies the exact taxonomy definition.
- Validate every generated public object against its JSON Schema.
- Treat SHA-256 URNs as public reference identifiers, never UOR.
- Never introduce a public substitute for Hyperframe, Covenant Atom, Guardian, NEP, UHR, Edge Twin, A2A, PLOG, or UOR.
- Stop and propose an ADR on any ambiguity listed in `GAP_ANALYSIS.md` under “ADR and stop-condition assessment.”
- Assign each execution task exactly one task-level classification; capability-specific dispositions remain authoritative in `GAP_ANALYSIS.md`.
- The supplied directory is not a Git worktree. Commit steps are planned gates and may execute only after the repository is restored with its history or explicitly initialized by its owner.
- Production fold-in remains blocked until live Balnce/Reasn repositories are supplied and `CURRENT_STATE_LEDGER.md` plus `INTEGRATION_DECISIONS.md` can be created from direct evidence.

## Verification commands

Use a Python 3.11-3.13 environment unless Python 3.14 is explicitly added to the support matrix. The observed baseline passed under Python 3.14.5, but that does not change the declared lower-bound-only support policy.

```bash
python3 -m pytest -q
python3 -m pytest tests/test_schema_instances.py -q
python3 -m pytest tests/conformance -q
python3 -m pwm_hpl_ref.demo
```

Every benchmark task must also emit a machine-readable result containing repository revision, environment, fixture version, parameters, baseline, metric, threshold, result, and limitations.

## Wave 0: canon and evidence lock

### Task 1: Make status and claim evidence enforceable

- **Purpose:** Eliminate maturity ambiguity before extending behavior.
- **Current code evidence:** `STATUS.md` defines six statuses; most source/schema/test/benchmark files are undeclared; major public claims are not mechanically linked to evidence or falsifiers.
- **Canonical invariant:** Code existence is not a status upgrade; claims must name evidence or a falsifier.
- **Classification:** `COMPLETE_EXISTING`.
- **Files/modules:** create `spec/status-taxonomy.md`, `schemas/json-schema/evidence-record.schema.json`, `docs/EVIDENCE_INDEX.md`, `tests/test_status_taxonomy.py`, and `tests/test_evidence_index.py`; modify relevant module headers/adjacent manifests and overbroad README claims.
- **Interface contracts:** one declared taxonomy value per significant artifact; evidence records require claim ID, exact claim, domain, source/version, source class, evidence status, implementation consequence, review date, reviewer, and falsifier/re-check trigger.
- **Data migration:** register each existing public claim without discarding its text; keep internal source material outside the public repository.
- **Security/privacy impact:** evidence records must not expose proprietary implementation details or private source content.
- **Observability:** lint output lists every unclassified file and malformed evidence record.
- **Tests:** add failures for an unknown status, missing status, missing source, missing review date, and missing falsifier; test all current records.
- **Acceptance criteria:** zero unclassified significant artifacts; the public evidence index validates; README benchmark language matches actual harnesses.
- **Feature flag/rollout:** documentation/tooling-only; enforce in CI after the repository is clean.
- **Rollback:** revert lint enforcement and the public evidence index together; do not restore inaccurate claims.
- **Public-repo synchronization:** this task is public-only; production claims remain external references, not copied internals.
- **Commit:** `docs: enforce status and evidence taxonomy`.

- [ ] Write failing taxonomy and public-evidence-index tests.
- [ ] Add the status spec and evidence schema.
- [ ] Register public claims and annotate significant artifacts without upgrading maturity.
- [ ] Run focused tests, then the full suite.
- [ ] Commit only the status and public-evidence files.

### Task 2: Establish reproducible conformance infrastructure

- **Purpose:** Make public interfaces executable and expose existing schema drift.
- **Current code evidence:** `tests/test_schemas.py` validates schemas as schemas only; generated receipts and demo assertions violate published contracts.
- **Canonical invariant:** Public schemas are boundary profiles, not complete private UOR/PLOG schemas.
- **Classification:** `HARDEN_EXISTING`.
- **Files/modules:** create `tests/test_schema_instances.py`, `tests/fixtures/valid/`, `tests/fixtures/invalid/`, `schemas/json-schema/projection-request.schema.json`, `schemas/json-schema/capability-mapping-record.schema.json`; modify `schemas/typescript/index.ts`, `pyproject.toml`, and `.github/workflows/test.yml` only as required.
- **Interface contracts:** each advertised public object has a valid and invalid fixture; generated Python objects use one documented camelCase serialization boundary.
- **Data migration:** update checked-in `examples/generated/demo-output.json` only after deterministic regeneration; preserve a changelog note for incompatible schema changes.
- **Security/privacy impact:** negative fixtures cover unexpected fields, malformed times, weak nonces, and unsupported enums.
- **Observability:** conformance failures identify schema URI, instance path, and violated keyword.
- **Tests:** validate all valid fixtures, reject all invalid fixtures, assert exact schema inventory, and validate demo-produced objects.
- **Acceptance criteria:** the current receipt mismatch and missing `recordTime` fail before implementation correction, then all public outputs validate.
- **Feature flag/rollout:** CI gate; no runtime flag.
- **Rollback:** schemas and serializers revert as one compatibility unit.
- **Public-repo synchronization:** production adapters must map to these profiles rather than expose private schemas.
- **Commit:** `test: add public profile conformance fixtures`.

- [ ] Write failing generated-instance tests for every existing object.
- [ ] Add missing Projection Request and Capability Mapping Record contracts.
- [ ] Complete TypeScript coverage and resolve JSON/TypeScript disagreements.
- [ ] Correct fixtures and serializers minimally.
- [ ] Run all schema and reference tests.
- [ ] Commit the conformance unit.

## Wave 1: provenance and PWM core

### Task 3: Harden the public provenance DAG

- **Purpose:** Make event replay defensible without claiming canonical UOR/PLOG equivalence.
- **Current code evidence:** `PLog` accepts missing parents, mutable payloads, malformed times, and non-topological ordering.
- **Canonical invariant:** PLOG is provenance; public hashes are not UOR; materialization explanation remains reconstructible.
- **Classification:** `HARDEN_EXISTING`.
- **Files/modules:** modify `src/pwm_hpl_ref/canonical.py`, `src/pwm_hpl_ref/plog.py`; create `tests/test_plog.py`, `tests/fixtures/plog/`; modify PLOG schema and `spec/public-interface-profile.md` if conformance requires clarification.
- **Interface contracts:** immutable event content; normalized RFC 3339 UTC record time; existing-parent validation; deterministic topological order with stable tie-break; hash recomputation; explicit unsupported-value errors.
- **Data migration:** provide a fixture migration command only if public serialized events change; never relabel old hashes as UOR.
- **Security/privacy impact:** reject tampered bodies, unknown parents, cycles, duplicate collisions, and non-finite JSON numbers.
- **Observability:** typed validation exceptions include event ID and failing rule without logging private payloads.
- **Tests:** hash vectors, mutation resistance, missing parent, cycle attempt, shuffled insertion, parent-before-child, malformed time, time-zone normalization, tampered event, and historical cutoff.
- **Acceptance criteria:** independent insertion orders replay identically; all accepted events verify; invalid DAGs fail closed.
- **Feature flag/rollout:** schema-version the hardened profile; old fixtures remain readable only if migration evidence exists.
- **Rollback:** retain old fixtures and migration script until the new profile is released.
- **Public-repo synchronization:** production mapping is deferred; document the future adapter seam.
- **Commit:** `feat: harden public provenance event profile`.

- [ ] Write failing PLOG contract tests.
- [ ] Implement minimal immutable validation and topological ordering.
- [ ] Add migration/version notes and fixtures.
- [ ] Run PLOG, schema, and full tests.
- [ ] Commit the provenance unit.

### Task 4: Complete temporal and epistemic materialization

- **Purpose:** Reconstruct current or point-in-time PWM state while preserving history, evidence, and interpretation.
- **Current code evidence:** `Materializer` handles only puts and assertion revocation; `at_time` filters record-time strings.
- **Canonical invariant:** history differs from current state; observations, assertions, facts, beliefs, inferences, predictions, disputes, preferences, policies, intents, commitments, capabilities, and events do not collapse into one type.
- **Classification:** `COMPLETE_EXISTING`.
- **Files/modules:** modify `src/pwm_hpl_ref/pwm.py`; create `src/pwm_hpl_ref/materialization_profile.py`, `tests/test_materialization_temporal.py`, `tests/fixtures/materialization/`; update PWM schemas only where the proposed profile requires it.
- **Interface contracts:** pinned schema/materialization/conflict profile; record-time and valid-time query; explicit event handlers; preserved provenance; explicit unknown-event failure or quarantine; deterministic dispute/supersession result.
- **Data migration:** version event vocabulary and retain replay of version `0.1.0` fixtures.
- **Security/privacy impact:** materialize only the supplied authorized event closure; do not treat absent access as false state.
- **Observability:** result reports applied, rejected, quarantined, and unresolved event IDs.
- **Tests:** correction without provenance deletion, revocation-before-assertion, supersession, concurrent contradiction, disputed prediction, valid-time versus record-time, unknown event, unauthorized closure exclusion, and shuffled replay.
- **Acceptance criteria:** fixture state is byte-stable for a pinned profile; point-in-time answers differ correctly; all source events remain attributable.
- **Feature flag/rollout:** select profile version explicitly; preserve current profile until fixtures migrate.
- **Rollback:** switch profile version without deleting provenance.
- **Public-repo synchronization:** map production materialization only after live PWM/metagraph discovery.
- **Commit:** `feat: add temporal epistemic materialization profile`.

- [ ] Write failing temporal/conflict tests.
- [ ] Define the versioned materialization profile.
- [ ] Implement the minimum event handlers and decision trace.
- [ ] Run focused replay tests, then full conformance.
- [ ] Commit the materialization unit.

### Task 5: Add complete PWM public object coverage

- **Purpose:** Represent the minimal object classes required by `spec/pwm-core.md` without binding the PWM to a storage engine.
- **Current code evidence:** entity, relation, assertion, and policy dictionaries exist; normative, intentional, provenance-reference, and projection-reference contracts do not.
- **Canonical invariant:** object classes preserve semantic distinctions and remain provenance-bearing.
- **Classification:** `CREATE_FROM_SPEC`.
- **Files/modules:** create missing JSON Schemas, TypeScript interfaces, Python dataclasses/serializers under `src/pwm_hpl_ref/model.py`, and `tests/test_pwm_objects.py`.
- **Interface contracts:** exact classes listed in PWM core; explicit version, privacy, time, epistemic, and provenance fields; extension fields cannot silently redefine base meanings.
- **Data migration:** translate current dictionary fixtures through explicit serializers; no destructive history rewrite.
- **Security/privacy impact:** privacy class and provenance are mandatory where the profile requires them; logs show IDs, not sensitive values.
- **Observability:** validation errors identify object class and path.
- **Tests:** round-trip every object across Python, JSON, and TypeScript fixture shape; reject semantic type collapse and missing provenance.
- **Acceptance criteria:** all minimal object classes have schema, Python representation, TypeScript representation, and fixtures.
- **Feature flag/rollout:** introduce as profile `0.2.0`; retain explicit `0.1.0` reader during fixture migration only.
- **Rollback:** preserve old reader and fixtures until release cutoff.
- **Public-repo synchronization:** no production storage schema is implied.
- **Commit:** `feat: complete public PWM object profile`.

- [ ] Write cross-representation contract tests.
- [ ] Add schemas and types.
- [ ] Add serializers and migrate fixtures.
- [ ] Run object, schema, replay, and full tests.
- [ ] Commit the object-profile unit.

## Wave 2: authorized minimum projection

### Task 6: Complete explainable authority composition

- **Purpose:** Produce a provenance-bearing bounded capability decision from typed principal constraints.
- **Current code evidence:** current set algebra supports scoped grants and deny-overrides only.
- **Canonical invariant:** capability is not authorization; the user does not automatically override other legitimate principals; public logic must remain compatible with Covenant Atom.
- **Classification:** `COMPLETE_EXISTING`.
- **Files/modules:** modify `src/pwm_hpl_ref/authority.py`; add `src/pwm_hpl_ref/authority_trace.py`, `tests/test_authority_profiles.py`, and authority fixtures; align the authority schema and TypeScript type.
- **Interface contracts:** validate principal, mandate reference, scope, time, jurisdiction, class, effect, and evidence; output allowed, denied, conditions, and per-capability reasons.
- **Data migration:** adapt existing `Constraint` fixtures with explicit scope/time/evidence defaults documented by profile version.
- **Security/privacy impact:** fail closed on invalid/unknown effects, expired evidence, and ungrounded mandatory constraints; do not log private evidence bodies.
- **Observability:** deterministic decision trace names applicable constraint IDs and precedence rules.
- **Tests:** no-grant denial reason, temporal expiry, jurisdiction mismatch, PHYSICAL and LEGAL veto, advisory non-veto, scoped grant, conflicting principals, and exact request binding.
- **Acceptance criteria:** every requested capability has an explainable result and provenance; no parallel permission primitive is introduced.
- **Feature flag/rollout:** version authority profile; compare old/new decisions on fixtures before defaulting.
- **Rollback:** select prior authority profile while retaining traces.
- **Public-repo synchronization:** production task must compose live Covenant Atom and Guardian, not port this engine as authority.
- **Commit:** `feat: complete explainable authority profile`.

- [ ] Write failing typed-constraint and trace tests.
- [ ] Align schemas and types.
- [ ] Implement minimal validation and deterministic decision trace.
- [ ] Run authority and full conformance tests.
- [ ] Commit the authority unit.

### Task 7: Bind and minimize projection requests

- **Purpose:** Compile only fields authorized for an exact recipient, purpose, capability set, and time window.
- **Current code evidence:** predicate/privacy filtering exists but is not cryptographically or structurally bound to the supplied decision.
- **Canonical invariant:** the canonical PWM is never exported; least disclosure and least persistence govern projection.
- **Classification:** `HARDEN_EXISTING`.
- **Files/modules:** modify `src/pwm_hpl_ref/projection.py`; add `src/pwm_hpl_ref/projection_trace.py`, `tests/test_projection_contract.py`, and projection fixtures.
- **Interface contracts:** schema-conformant Projection Request; decision request digest; recipient/purpose/environment binding; positive TTL; field-local assertion ID, valid/record time, epistemic status, privacy, and provenance; explicit crystallization rung.
- **Data migration:** regenerate demo projection under profile `0.2.0`; preserve prior output as versioned fixture if referenced publicly.
- **Security/privacy impact:** unknown privacy or semantics fail closed; unauthorized fields never enter traces; trace records reasons without disclosing rejected values.
- **Observability:** report selected field IDs, excluded field IDs, policy reasons, and disclosure counts.
- **Tests:** decision/request mismatch, unknown privacy, expired request, forbidden capability, disputed assertion policy, minimum field set, no raw PWM export, and provenance completeness.
- **Acceptance criteria:** every projected field is necessary under the declared profile, authorized by the exact decision, and attributable.
- **Feature flag/rollout:** profile version with explicit comparison output.
- **Rollback:** retain old compiler only for old fixtures, never as an unversioned fallback.
- **Public-repo synchronization:** production compiler binds live Guardian/Covenant decision references.
- **Commit:** `feat: bind authority to minimal projections`.

- [ ] Write failing binding and minimization tests.
- [ ] Implement the request digest and field trace.
- [ ] Validate all output instances.
- [ ] Run projection, schema, and full tests.
- [ ] Commit the projection unit.

### Task 8: Implement the bounded spatial profile

- **Purpose:** Demonstrate a path-and-surface projection without exporting a global home map.
- **Current code evidence:** spatial behavior exists only in specification and a three-assertion demo.
- **Canonical invariant:** spatial projection is a purpose-bounded view with uncertainty and provenance, never an unrestricted map copy.
- **Classification:** `CREATE_FROM_SPEC`.
- **Files/modules:** create `src/pwm_hpl_ref/spatial.py`, spatial schemas, `tests/test_spatial_projection.py`, `tests/fixtures/spatial/home-delivery.json`, and `benchmarks/hpl-spatial/run.py`.
- **Interface contracts:** geometry clipping, topology reduction, semantic redaction, pseudonymization, allowed zones, TTL, source frame, uncertainty, and provenance.
- **Data migration:** replace ad hoc location assertions in the demo with a versioned spatial fixture.
- **Security/privacy impact:** bedroom and medication semantics remain absent even through topology, labels, identifiers, or provenance side channels.
- **Observability:** disclose counts by geometry, topology, semantic, and provenance class without raw private geometry in logs.
- **Tests:** path continuity, excluded-zone non-reachability, pseudonymization, uncertainty propagation, frame mismatch, and purpose/TTL binding.
- **Acceptance criteria:** robot fixture reaches the permitted surface; forbidden-zone information is absent under declared leakage checks.
- **Feature flag/rollout:** spatial profile remains `EXPERIMENTAL` until benchmark threshold is met.
- **Rollback:** fall back to no spatial projection, not a global map.
- **Public-repo synchronization:** production spatial source mapping is deferred.
- **Commit:** `feat: add bounded spatial projection profile`.

- [ ] Write failing spatial conformance and privacy tests.
- [ ] Implement minimal graph/geometry reduction.
- [ ] Add the benchmark fixture and documented limitations.
- [ ] Run spatial, projection, and full tests.
- [ ] Commit the spatial unit.

## Wave 3: Arranger and lifecycle

### Task 9: Complete Arranger issuance and verification

- **Purpose:** Make the crystallized artifact enforce all proposed bindings.
- **Current code evidence:** Ed25519 signing and tamper detection exist; lifecycle fields are largely unenforced.
- **Canonical invariant:** Arranger is an artifact and Hyperframe is the carrier; the five-rung gradient is unchanged.
- **Classification:** `COMPLETE_EXISTING`.
- **Files/modules:** modify `src/pwm_hpl_ref/arranger.py`, Arranger schema and TypeScript type; create `src/pwm_hpl_ref/replay.py`, `src/pwm_hpl_ref/revocation.py`, `tests/test_arranger_lifecycle.py`.
- **Interface contracts:** issuer/key ID/algorithm, recipient, purpose, capabilities, forbidden capabilities, rung/classes, runtime/model/hardware compatibility, issue/expiry, nonce, revocation handle, payload hash, provenance, learning-return policy, departure requirement, signature.
- **Data migration:** version manifests; regenerate demo fixture; reject ambiguous unversioned manifests at strict verification boundaries.
- **Security/privacy impact:** recompute ID/hash, verify key binding, enforce time, recipient, compatibility, one-time nonce, and revocation before release to runtime.
- **Observability:** typed verification result records rule IDs, not secret payloads.
- **Tests:** tampered ID/hash, wrong recipient/purpose/key/runtime/model/hardware, expiry, future issue time, replayed nonce, revoked handle, unknown class, and valid round trip.
- **Acceptance criteria:** no artifact verifies on signature alone; every required binding is validated; no carrier abstraction is added.
- **Feature flag/rollout:** strict verifier profile `0.2.0`; compatibility reader may inspect but never execute old artifacts.
- **Rollback:** disable execution of new artifacts while retaining revocation records; never bypass strict verification.
- **Public-repo synchronization:** production task maps to the live Arranger/D5 and Hyperframe implementations after discovery.
- **Commit:** `feat: enforce arranger lifecycle bindings`.

- [ ] Write failing lifecycle-verifier tests.
- [ ] Align manifest schema and all language types.
- [ ] Implement strict verification, replay, and revocation.
- [ ] Run Arranger, schema, security, and full tests.
- [ ] Commit the artifact lifecycle unit.

### Task 10: Add the lifecycle state machine and provenance trace

- **Purpose:** Make all twelve specified phases explicit and auditable.
- **Current code evidence:** demo directly calls disconnected constructors.
- **Canonical invariant:** every meaningful transition is provenance-bearing; unknown or invalid transitions fail closed.
- **Classification:** `CREATE_FROM_SPEC`.
- **Files/modules:** create `src/pwm_hpl_ref/lifecycle.py`, `schemas/json-schema/lifecycle-event.schema.json`, `tests/test_projection_lifecycle.py`, and lifecycle fixtures.
- **Interface contracts:** `DISCOVER -> REQUEST -> RE_GROUND -> AUTHORIZE -> PLACE -> CRYSTALLIZE -> ISSUE -> EXECUTE -> OBSERVE -> REVOKE_OR_EXPIRE -> DEPART -> RECONCILE`, with explicit refusal/termination branches.
- **Data migration:** none; wrap the demo flow after all current objects pass conformance.
- **Security/privacy impact:** no phase can skip authorization, strict artifact verification, local runtime acceptance, or reconciliation policy.
- **Observability:** each transition emits a public provenance-profile event with prior state, next state, actor, decision reference, and reason.
- **Tests:** legal sequence, every illegal skip, expiry during execution, revocation before execution, local refusal, absent departure evidence, and deferred reconciliation.
- **Acceptance criteria:** the complete first-milestone flow is expressed through the state machine; event replay explains every transition.
- **Feature flag/rollout:** keep direct demo path only until parity tests pass, then remove it rather than maintain two authorities.
- **Rollback:** return to the prior release, not direct-call bypasses inside the new release.
- **Public-repo synchronization:** production phase events map to canonical PLOG only after discovery.
- **Commit:** `feat: add auditable projection lifecycle`.

- [ ] Write the failing transition matrix tests.
- [ ] Define lifecycle event schema and states.
- [ ] Implement minimal transitions and refusal paths.
- [ ] Route the demo through the state machine.
- [ ] Run lifecycle, replay, and full tests.
- [ ] Commit the lifecycle unit.

### Task 11: Authenticate learning return and sovereign reconciliation

- **Purpose:** Return foreign evidence without silently changing canonical state.
- **Current code evidence:** `learning_candidate()` creates an unsigned dictionary and no review path exists.
- **Canonical invariant:** foreign observations are candidates; accepted changes create provenance derivations before rematerialization.
- **Classification:** `COMPLETE_EXISTING`.
- **Files/modules:** modify `src/pwm_hpl_ref/learning.py`; create `src/pwm_hpl_ref/reconciliation.py`, signed-candidate/review schemas, `tests/test_learning_return.py`, and poisoning fixtures.
- **Interface contracts:** signed source/session/artifact binding; claim, confidence, evidence, nonce/time; decisions `ACCEPT`, `REJECT`, `DEFER`, `BRANCH`, `MERGE`; resulting event references candidate and reviewer policy.
- **Data migration:** version current unsigned candidates as non-executable legacy evidence.
- **Security/privacy impact:** source authentication, replay prevention, schema checks, confidence bounds, conflict quarantine, and no direct `PWMState` mutation.
- **Observability:** candidate and decision IDs, source identity, outcome, and derivation event ID; sensitive claim values remain out of logs.
- **Tests:** unsigned rejection, wrong session, replay, poisoning conflict, reject/defer no-state-change, accept creates event, and deterministic rematerialization.
- **Acceptance criteria:** only an accepted provenance event can affect later PWM state; all other candidates remain attributable but non-canonical.
- **Feature flag/rollout:** review is mandatory in the reference profile; no bypass flag.
- **Rollback:** stop accepting candidates while retaining signed evidence and decisions.
- **Public-repo synchronization:** production review must use live Guardian/policy/epistemic and PLOG owners.
- **Commit:** `feat: add authenticated learning reconciliation`.

- [ ] Write failing source, replay, and state-mutation tests.
- [ ] Add signed candidate and decision contracts.
- [ ] Implement review outcomes and PLOG-profile derivation.
- [ ] Run learning, materialization, lifecycle, and full tests.
- [ ] Commit the learning-return unit.

### Task 12: Enforce bounded departure assurance

- **Purpose:** Make each departure claim no stronger than verified evidence.
- **Current code evidence:** tier labels exist, but receipts are unsigned and arbitrary evidence is accepted.
- **Canonical invariant:** session end is not forgetting; opaque copies and human observation remain outside claims.
- **Classification:** `COMPLETE_EXISTING`.
- **Files/modules:** modify `src/pwm_hpl_ref/departure.py` and departure schema; create `src/pwm_hpl_ref/departure_profiles.py`, `tests/test_departure_assurance.py`, and `sim/recipient_runtime.py`.
- **Interface contracts:** recipient-signed acknowledgement; level-specific evidence schema; key invalidation/revocation state; attestation/proof profile IDs; explicit residual-risk statement.
- **Data migration:** regenerate current receipt as `UNVERIFIED` unless a signed recipient acknowledgement is produced by the simulator.
- **Security/privacy impact:** signature, artifact/session/recipient binding, replay protection, and proof-profile validation; no universal deletion language.
- **Observability:** record requested level, verified level, downgrade reason, and residual risk.
- **Tests:** forged acknowledgement, wrong artifact/session, missing evidence downgrade, key invalidation, deactivation, protocol acknowledgement, unsupported attestation, and opaque-copy caveat.
- **Acceptance criteria:** verifier cannot emit a stronger level than evidence supports; current schema and generated output agree.
- **Feature flag/rollout:** stronger levels disabled unless their proof profile is registered.
- **Rollback:** downgrade to `UNVERIFIED`; never preserve an unsupported stronger claim.
- **Public-repo synchronization:** production receipts eventually reconcile with existing UOR/PLOG certificate/coherence chains.
- **Commit:** `feat: enforce evidence-tiered departure assurance`.

- [ ] Write failing evidence-level tests.
- [ ] Add the minimal non-authoritative recipient simulator.
- [ ] Implement signed receipt verification and downgrade behavior.
- [ ] Run departure, lifecycle, schema, and full tests.
- [ ] Commit the departure unit.

## Wave 4: first interoperable foreign runtime

### Task 13: Complete the first milestone demonstration

- **Purpose:** Prove the full sovereign-center flow with a foreign consumer that cannot become authoritative.
- **Current code evidence:** `demo.py` constructs local records but has no recipient runtime, carrier boundary, execution refusal, revocation, or reconciliation.
- **Canonical invariant:** execution may move; canonical PWM authority does not. Local safety may refuse.
- **Classification:** `COMPLETE_EXISTING`.
- **Files/modules:** modify `src/pwm_hpl_ref/demo.py`; create `src/pwm_hpl_ref/carrier_boundary.py`, `sim/foreign_runtime.py`, `tests/test_first_milestone.py`; update generated output and robot example.
- **Interface contracts:** transport-neutral artifact delivery boundary explicitly documented as non-Hyperframe; strict recipient verification; consume permitted fields only; local accept/refuse; signed outcome; revocation/expiry stop; departure receipt; review-mediated return.
- **Data migration:** regenerate a deterministic fixture with fixed test clock/key material while keeping the interactive CLI nondeterministic.
- **Security/privacy impact:** foreign runtime has no PWM/PLOG write handle; raw PWM never crosses its API; local safety decision is separate from HPL authorization.
- **Observability:** phase/event IDs, disclosed-field inventory, authority decision, local decision, return status, revocation status, and departure assurance.
- **Tests:** complete happy path, local refusal, wrong recipient, revoked-before-use, expire-during-session, attempted PWM write, unauthorized field access, rejected learning, and accepted learning rematerialization.
- **Acceptance criteria:** one deterministic test proves the complete stated milestone and every generated object validates against its public schema.
- **Feature flag/rollout:** mark the scenario `REFERENCE_IMPLEMENTATION`; do not upgrade specifications to `IMPLEMENTED`.
- **Rollback:** retain previous component demo as historical fixture only; do not keep a bypass execution path.
- **Public-repo synchronization:** defines boundary objects for later production mapping, not production substitutes.
- **Commit:** `feat: complete sovereign projection reference flow`.

- [ ] Write the failing end-to-end milestone tests.
- [ ] Implement the carrier boundary and foreign runtime simulator.
- [ ] Route the demo through lifecycle, safety, return, and departure.
- [ ] Generate and schema-validate deterministic evidence.
- [ ] Run the full suite and demo.
- [ ] Commit the first milestone.

## Waves 4-6: outward expansion after the milestone

### Task 14: Standardize adapter provenance and conformance

- **Purpose:** Turn isolated mappings into version-pinned, fail-closed boundary profiles.
- **Current code evidence:** HCP, VSS, and WoT have narrow experimental transforms; ROS 2, SOVD, and MHS have no code.
- **Canonical invariant:** external vocabulary is evidence, not internal authority; A2A remains agent communication and MCP remains courier/tool interaction.
- **Classification:** `EXTEND_EXISTING`.
- **Files/modules:** create `protocol/README.md`, source registry, common mapping record implementation/tests; modify implemented HCP, VSS, and WoT adapters. A2A, MCP, ROS 2, SOVD, and MHS retain their separate dispositions in `GAP_ANALYSIS.md` and are not bundled into this task.
- **Interface contracts:** source URL/version/hash/license, external path/type/unit, internal semantic target, transform, confidence, unknown-state handling, authority disclaimer, provenance.
- **Data migration:** convert hard-coded mappings into versioned records without changing unknown-fails-closed behavior.
- **Security/privacy impact:** no adapter sees raw PWM by default; capability descriptions cannot grant authority; physical commands stop at local runtime APIs.
- **Observability:** mapping version, source hash, selected rule, unknown reason, and output provenance.
- **Tests:** source integrity, known mappings, unknown closure, malformed input, version mismatch, authority absence, and local safety refusal.
- **Acceptance criteria:** each claimed adapter pins a reviewed source and passes bounded conformance fixtures; MHS remains claim-free until normative review.
- **Feature flag/rollout:** each adapter is independently experimental; no bulk enablement.
- **Rollback:** disable one mapping profile without affecting PWM or lifecycle.
- **Public-repo synchronization:** production uses CDL/NEP/A2A owners after repository discovery.
- **Commit:** split by adapter, beginning `feat: add versioned capability mapping profile`.

- [ ] Pin primary sources and hashes before adapter code changes.
- [ ] Implement the common mapping record and conformance tests.
- [ ] Migrate HCP, VSS, and WoT individually.
- [ ] Confirm A2A/MCP/ROS 2 remain outside this task and separately gated.
- [ ] Keep SOVD deferred and MHS research-only until their gates clear.

### Task 15: Add embodiment and multi-principal simulations

- **Purpose:** Exercise dynamic authority and local refusal without claiming safety certification.
- **Current code evidence:** robot example is partial; fleet and vehicle support are proposed only.
- **Canonical invariant:** HPL does not become the safety kernel; no model writes directly to actuation buses.
- **Classification:** `EXTEND_EXISTING`.
- **Files/modules:** extend `sim/`; add `tests/test_robot_delivery_sim.py`, `tests/test_fleet_authority_sim.py`; update example READMEs and spatial/authority fixtures.
- **Interface contracts:** deterministic machine state, local veto, principal constraints, lifecycle events, outcome evidence, and no direct actuator API.
- **Data migration:** none.
- **Security/privacy impact:** simulations assert that forbidden spatial data and capabilities never reach the runtime.
- **Observability:** authority changes, safety refusal, projection inventory, and outcome references.
- **Tests:** employee request versus owner/OEM/local-state veto, authority change during session, offline expiry, and safe refusal.
- **Acceptance criteria:** simulations prove architecture boundaries, not physical safety performance.
- **Feature flag/rollout:** simulations only; remain `REFERENCE_IMPLEMENTATION` or `EXPERIMENTAL`.
- **Rollback:** remove a scenario without changing core semantics.
- **Public-repo synchronization:** vehicle support waits for production BWM/Web0/IntentCasting and reviewed SOVD.
- **Commit:** one commit per simulation.

- [ ] Complete robot simulation tests.
- [ ] Add fleet authority fixtures and dynamic-veto tests.
- [ ] Keep vehicle support non-executable until dependencies are met.
- [ ] Run all simulation and core tests.

### Task 16: Define, but do not duplicate, placement and production fold-in

- **Purpose:** Prepare evidence-driven integration with NEP and the existing Edge Twin.
- **Current code evidence:** no production repositories or placement implementation are present.
- **Canonical invariant:** NEP is Neural Engine Protocol; UHR is Universal Host Runtime; Edge Twin is extended, not duplicated; canonical PWM custody does not migrate for convenience.
- **Classification:** `DEFER`.
- **Files/modules:** after repositories are supplied, create `CURRENT_STATE_LEDGER.md`, `INTEGRATION_DECISIONS.md`, and any required ADR in the production workspace; add public placement fixtures only after owner discovery.
- **Interface contracts:** placement input includes privacy, trust, latency, cost, model/hardware compatibility, and connectivity; output references an eligible delegated executor and evidence.
- **Data migration:** none until production stores and owners are known.
- **Security/privacy impact:** Guardian gates every external call; child/scoped identity and PLOG provenance follow production canon; no raw PWM replication.
- **Observability:** placement decision, rejected targets, policy evidence, failover, and canonical custody location.
- **Tests:** repository-specific NEP extension registration, Guardian denial, Edge Twin delegation, failover, and custody invariants.
- **Acceptance criteria:** live source evidence identifies every owner and no duplicate module is introduced.
- **Feature flag/rollout:** production feature flag and staged rollout are mandatory after discovery.
- **Rollback:** route to an already-authorized executor while preserving PLOG history; never bypass Guardian.
- **Public-repo synchronization:** publish only boundary profiles and non-proprietary conformance fixtures.
- **Commit:** unavailable until the production repository and its commit conventions are known.

- [ ] Obtain the live production repositories.
- [ ] Discover every canonical owner and test before planning code.
- [ ] Emit the two master-instruction discovery artifacts.
- [ ] Stop for an ADR on overlap or ambiguity.
- [ ] Implement only approved extensions.

## Wave 7: benchmarks, falsifiers, and release

### Task 17: Build the benchmark and experiment matrix

- **Purpose:** Make architectural claims falsifiable and reproducible.
- **Current code evidence:** one HPL-CONTEXT smoke count exists; seven named families and the PWM falsifier have no harness.
- **Canonical invariant:** no benchmark label or maturity claim exceeds measured evidence.
- **Classification:** `EXTEND_EXISTING`.
- **Files/modules:** expand `benchmarks/`; create `experiments/README.md`, per-family protocols/results, `tests/test_benchmark_contracts.py`, and reproducibility metadata schema.
- **Interface contracts:** each benchmark declares hypothesis, falsifier, fixture, baseline, metric, threshold, repetitions, environment, limitations, and result provenance.
- **Data migration:** preserve the smoke result as historical, explicitly non-conformant evidence.
- **Security/privacy impact:** synthetic fixtures only unless a reviewed data protocol exists; no private PWM corpus in public results.
- **Observability:** deterministic JSON result plus human-readable summary.
- **Tests:** benchmark contract validation, deterministic seeds, threshold behavior, fixture integrity, and stale-result detection.
- **Acceptance criteria:** every README benchmark claim links to an executable harness and result; Paper 01's falsifier has a memory-only baseline; negative results are retained.
- **Feature flag/rollout:** benchmarks do not gate runtime behavior until validity is reviewed; they gate public claims.
- **Rollback:** retract or downgrade claims, never delete unfavorable results.
- **Public-repo synchronization:** production performance numbers remain separate unless reproducibly publishable.
- **Commit:** one commit per benchmark family, beginning `bench: complete hpl-context protocol`.

- [ ] Define the common benchmark/result schema.
- [ ] Complete HPL-CONTEXT with utility and baseline.
- [ ] Add benchmarks in dependency order.
- [ ] Connect paper falsifiers and proof obligations.
- [ ] Re-run all results in a clean environment.

### Task 18: Release evidence gate

- **Purpose:** Publish only claims supported by reproducible artifacts.
- **Current code evidence:** release plan exists; dependency locks, SBOM, schema profile IDs, diagram regeneration, and complete evidence links do not.
- **Canonical invariant:** the public repository remains semantically aligned with production while exposing no proprietary internals.
- **Classification:** `CREATE_FROM_SPEC`.
- **Files/modules:** modify `PUBLIC_RELEASE_PLAN.md`, README, papers, security docs, diagrams, CI, packaging metadata; create release checklist, SBOM, lock/reproducibility instructions, and release evidence index.
- **Interface contracts:** versioned schemas and compatibility policy; supported Python matrix; signed release artifacts where infrastructure allows.
- **Data migration:** publish schema/version migration notes.
- **Security/privacy impact:** dependency audit, secret scan, threat-model review, and disclosure review.
- **Observability:** CI records tests, conformance, benchmarks, diagram generation, status lint, and package build.
- **Tests:** clean install, supported Python matrix, CLI smoke, package contents, schema resolution, documentation links, and reproducible benchmark subset.
- **Acceptance criteria:** all gates pass from a clean checkout; every major claim points to code, test, benchmark, proof, threat model, falsifier, or explicit research status.
- **Feature flag/rollout:** tag a pre-release before `0.2.0`; no status upgrades during release triage.
- **Rollback:** withdraw the release/tag according to repository policy and publish corrected evidence.
- **Public-repo synchronization:** production mappings must name exact reviewed versions without exposing private internals.
- **Commit:** `release: prepare reproducible pwm-hpl reference v0.2.0`.

- [ ] Run the clean-install and full evidence matrix.
- [ ] Review claims against `STATUS.md` and the evidence ledger.
- [ ] Review threat model and dependency artifacts.
- [ ] Regenerate diagrams and examples reproducibly.
- [ ] Create the release commit only after all gates pass.

## Commit sequence

Once Git history is restored, use this dependency-preserving order:

1. `docs: enforce status and evidence taxonomy`
2. `test: add public profile conformance fixtures`
3. `feat: harden public provenance event profile`
4. `feat: add temporal epistemic materialization profile`
5. `feat: complete public PWM object profile`
6. `feat: complete explainable authority profile`
7. `feat: bind authority to minimal projections`
8. `feat: add bounded spatial projection profile`
9. `feat: enforce arranger lifecycle bindings`
10. `feat: add auditable projection lifecycle`
11. `feat: add authenticated learning reconciliation`
12. `feat: enforce evidence-tiered departure assurance`
13. `feat: complete sovereign projection reference flow`
14. Adapter, simulation, and benchmark commits split by independently reviewable capability.
15. `release: prepare reproducible pwm-hpl reference v0.2.0`

Do not squash away evidence-bearing migration or negative-test commits if doing so would make design chronology harder to audit.

## Completion gates

The first milestone is complete only when all conditions hold simultaneously:

- A clean environment installs and runs the suite.
- Every public object emitted by code validates against its versioned schema.
- Event DAG validation, temporal replay, conflicts, corrections, disputes, supersession, and provenance closure have conformance fixtures.
- Point-in-time materialization is deterministic across event insertion order.
- Every projection field is bound to exact recipient, purpose, authority decision, time, privacy policy, and provenance.
- The Arranger verifier enforces every required binding, nonce, expiry, compatibility, payload hash, and revocation state.
- A foreign reference runtime consumes the artifact without receiving a PWM/PLOG mutation API.
- Local safety can refuse independently.
- Foreign outcomes remain candidates until an explicit review decision creates a provenance derivation.
- Revocation and expiry stop future authorized use in the reference runtime.
- Departure claims are cryptographically and semantically limited to verified evidence.
- HPL-CONTEXT, HPL-AUTH, HPL-RESIDUE, and HPL-HANDOFF have reproducible baseline results.
- README, STATUS, ROADMAP, examples, papers, and evidence ledger state exactly what the evidence supports.
- No accepted ADR is bypassed; any necessary change is represented by a reviewed superseding ADR.

## Plan self-review

- **Specification coverage:** Tasks 3-13 cover PWM core, HPL core, Arranger, lifecycle, multi-principal governance, departure assurance, spatial projection, and status taxonomy. Tasks 14-18 cover interoperability, simulations, production discovery, benchmarks, and release.
- **Protected terms:** UOR, PLOG, Hyperframe, Arranger, Covenant Atom, Guardian, NEP, UHR, Edge Twin, A2A, MCP, BWM, Web0, and the five-rung Crystallization Gradient retain their governing meanings.
- **Scope discipline:** MHS, SOVD, vehicle support, production placement, and Edge Twin work remain blocked or deferred until their evidence/dependency gates clear.
- **No hidden status upgrades:** passing tests authorize only bounded claims within tested scope.
- **No implementation performed:** this document defines future work; the current session adds audit/planning artifacts only.
