---
status: RESEARCH
audit_date: 2026-08-28
repository_version: 0.1.0
---

# Gap Analysis

## Classification method

Each public-repository capability receives exactly one requested classification:

- `HARDEN_EXISTING`: behavior exists and needs correctness, security, or conformance work without a material scope expansion.
- `COMPLETE_EXISTING`: a documented interface or flow is partially implemented and should be completed.
- `EXTEND_EXISTING`: a working bounded capability should gain an additional defined behavior.
- `CREATE_FROM_SPEC`: a sufficiently specified capability has no implementation.
- `EXPERIMENT`: the implementation requires empirical evaluation before normative commitment.
- `RESEARCH_ONLY`: the scientific, legal, standards, or proof basis is not ready for implementation claims.
- `DEFER`: valid work that is not on the critical path or is blocked by unavailable authority/evidence.
- `REJECT`: work that violates governing architecture or overstates evidence.

These public classifications do not replace the production classifications in `../MASTER_INSTRUCTION.md`. Production classification is blocked until the live Balnce/Reasn repositories and canonical implementations are available for discovery.

## Immediate contract defects

| ID | Finding | Evidence | Classification | Required disposition |
|---|---|---|---|---|
| G-001 | Generated departure receipts violate their JSON Schema because `receiptId` is emitted but undeclared under `additionalProperties: false`. | `src/pwm_hpl_ref/departure.py`; departure schema; generated demo output. | `HARDEN_EXISTING` | Reconcile schema and implementation, then validate generated instances. |
| G-002 | `PROTOCOL_DEPARTURE` requires signed recipient acknowledgement, but current receipts are unsigned local records with arbitrary evidence. | Departure spec and demo. | `COMPLETE_EXISTING` | Add signed acknowledgement and level-specific evidence validation or downgrade the emitted level. |
| G-003 | Arranger's proposed required bindings are absent or optional in schema/code. | `spec/arranger.md`, schema, TypeScript, issuer. | `COMPLETE_EXISTING` | Align capability, forbidden-capability, compatibility, environment, learning-return, revocation, and departure bindings. |
| G-004 | Public interface promises Projection Request and Capability Mapping Record without machine-readable contracts. | `spec/public-interface-profile.md`. | `CREATE_FROM_SPEC` | Add JSON Schema, TypeScript types, fixtures, and conformance tests. |
| G-005 | Schema tests validate schemas, not implementation-generated instances. | `tests/test_schemas.py`. | `HARDEN_EXISTING` | Add positive and negative instance suites for every public contract. |
| G-006 | README claims benchmark harnesses for authority, residue, and portability that do not exist. | README and `benchmarks/`. | `HARDEN_EXISTING` | Qualify the claim until harnesses and reproducible results exist. |
| G-007 | Most significant modules and evidence artifacts have no taxonomy status. | `STATUS.md` versus source/schemas/tests/benchmarks. | `COMPLETE_EXISTING` | Add status metadata or a manifest that covers every significant artifact. |
| G-008 | Required `spec/status-taxonomy.md`, `protocol/`, `experiments/`, and `sim/` paths are absent. | Repository tree. | `CREATE_FROM_SPEC` | Add the taxonomy specification and only the minimal protocol/experiment/simulation structure justified by later tasks. |

## Capability classification by dependency wave

### Wave 0: canon and evidence

| Capability | Classification | Evidence and decision |
|---|---|---|
| Status taxonomy specification | `CREATE_FROM_SPEC` | Root taxonomy exists; mandated spec path and status coverage do not. |
| Artifact status linting | `CREATE_FROM_SPEC` | Policy exists without enforcement. |
| Evidence ledger contract and populated source records | `COMPLETE_EXISTING` | Seed ledger omits source/version/class, reviewer/date, and falsifier fields and uses divergent statuses. |
| Terminology/canon map | `COMPLETE_EXISTING` | Glossary and ADRs exist, but no machine-checkable protected-term audit exists. |
| Primary-source archive with hashes and review dates | `CREATE_FROM_SPEC` | Standards and competitor claims are unpinned. |
| Public/private boundary documentation | `HARDEN_EXISTING` | The boundary is clear in prose but should be enforced by status/claim tests. |
| Production current-state ledger | `DEFER` | No Balnce/Reasn repository was supplied; do not infer production ownership. |
| Production integration decisions | `DEFER` | Requires live canonical package/file/type/store/API evidence. |
| New parallel HPL authority, carrier, runtime, edge twin, or UOR-lite | `REJECT` | Violates canonical synthesis, master instruction, and accepted ADRs. |

### Wave 1: provenance and PWM core

| Capability | Classification | Evidence and decision |
|---|---|---|
| Deterministic JSON/hash utility | `HARDEN_EXISTING` | Exists but lacks interoperable canonicalization rules, invalid-value handling, and vectors. It must remain explicitly non-UOR. |
| Public PLOG event profile | `HARDEN_EXISTING` | Event DAG shape exists; parent, immutability, hash, topology, schema, and timestamp validation do not. |
| Deterministic materialization | `COMPLETE_EXISTING` | Basic puts and assertion revocation exist; temporal validity, conflict/supersession, authorization closure, schema versions, and reproducibility are incomplete. |
| Point-in-time query | `COMPLETE_EXISTING` | `at_time` performs lexical record-time filtering only; valid-time semantics and timezone validation are absent. |
| Typed entity/relation/assertion contracts | `HARDEN_EXISTING` | Schemas exist but are not enforced; implementation/schema naming drifts. |
| Normative and intentional object support | `CREATE_FROM_SPEC` | Required by PWM core, absent from schemas and materializer. |
| Provenance and projection reference contracts | `CREATE_FROM_SPEC` | Named by the spec but not independently modeled. |
| Conflict, dispute, correction, and supersession fixtures | `CREATE_FROM_SPEC` | Core constitutional distinctions are not exercised. |
| Checkpoints/caches with reconstruction proof | `EXTEND_EXISTING` | ADR permits caching only if event reconstruction remains authoritative. |
| Canonical UOR implementation in this public repo | `REJECT` | Conventional hashes may support independent execution but must not be labeled UOR. |
| Higher-dimensional UOR/Clifford/sheaf implementation claims | `RESEARCH_ONLY` | Proof-status document identifies unresolved or invalid generalizations. |
| Production PWM/PLOG/UOR serialization adapter | `DEFER` | Requires unavailable production source discovery and ADR reconciliation. |

### Wave 2: HPL projection and authority

| Capability | Classification | Evidence and decision |
|---|---|---|
| Projection Request contract | `CREATE_FROM_SPEC` | Python dataclass exists, but advertised public schema/type does not. |
| Projection Manifest conformance | `HARDEN_EXISTING` | Output exists without runtime schema validation or complete provenance detail. |
| Predicate/privacy minimization | `HARDEN_EXISTING` | Current filter is useful but accepts invalid TTL/privacy and omits field-level trace. |
| Utility-aware representation selection | `EXPERIMENT` | Mathematical objective exists, but utility/leakage/persistence/dependency measures are not operational. |
| Five-rung crystallization selection | `CREATE_FROM_SPEC` | Gradient is canonical; compiler does not select or report a rung. |
| Authority request binding | `HARDEN_EXISTING` | Compiler accepts a decision without proving it belongs to the exact request. |
| Multi-principal constraint validation | `COMPLETE_EXISTING` | Set algebra exists; mandate, scope, time, jurisdiction, class, and evidence semantics do not. |
| Covenant Atom production composition | `DEFER` | Must compose the live canonical implementation; none is available here. |
| Spatial clipping, topology reduction, redaction, pseudonymization, uncertainty | `CREATE_FROM_SPEC` | Spatial specification exists; no implementation or fixture exists. |
| Recipient/runtime/environment discovery profile | `CREATE_FROM_SPEC` | Lifecycle DISCOVER is prose only. |
| Semantic re-grounding framework | `EXTEND_EXISTING` | Three adapters demonstrate isolated mappings; there is no common fail-closed mapping record. |
| Guardian-bound production decisions | `DEFER` | Public profile may model decision evidence; production gate wiring requires live Guardian/Covenant code. |

### Wave 3: Arranger and lifecycle

| Capability | Classification | Evidence and decision |
|---|---|---|
| Arranger issue contract | `COMPLETE_EXISTING` | Signing exists; required bindings and validation are incomplete. |
| Arranger verification | `HARDEN_EXISTING` | Must recompute IDs/hashes and enforce signature, recipient, purpose, expiry, classes, and compatibility. |
| Nonce replay prevention | `CREATE_FROM_SPEC` | Nonce field exists without a consumption store or verifier behavior. |
| Revocation registry and operation | `CREATE_FROM_SPEC` | Handle exists without lifecycle behavior or schema. |
| Runtime/model/hardware compatibility registry | `CREATE_FROM_SPEC` | Required conditionally by spec; no profile or implementation exists. |
| Hyperframe transport integration | `DEFER` | Public repo may define an adapter boundary, but canonical carrier implementation must be reconciled with live D5 code. Do not create a competing envelope. |
| Lifecycle state machine and provenance events | `CREATE_FROM_SPEC` | Twelve phases are specified; only fragments are executable. |
| Signed learning candidate | `COMPLETE_EXISTING` | Candidate shape exists without source authentication or evidence closure. |
| Learning review and PLOG reconciliation | `CREATE_FROM_SPEC` | No accept/reject/defer/branch/merge transition materializes an authorized derivation. |
| Signed departure receipt | `COMPLETE_EXISTING` | Tier vocabulary exists but evidence is not authenticated or level-validated. |
| Attested/verified departure proof profiles | `RESEARCH_ONLY` | Claims depend on specific hardware/runtime evidence and bounded assumptions. |
| Universal foreign deletion guarantee | `REJECT` | Contradicts ADR-0006 and the threat model. |

### Wave 4: interoperability

| Capability | Classification | Evidence and decision |
|---|---|---|
| HCP mapping experiment | `HARDEN_EXISTING` | Adapter exists; pin source/version and validate a bounded profile before stronger claims. |
| COVESA VSS mapping experiment | `HARDEN_EXISTING` | Closed-unknown behavior exists; add version, units, types, time, and fixtures. |
| WoT capability-evidence mapping | `HARDEN_EXISTING` | Affordance extraction exists; add TD validation, semantics, forms, and security metadata without treating capability as authority. |
| ROS 2 reference adapter | `CREATE_FROM_SPEC` | Mapping prose exists; implementation must terminate above local safety/actuation. |
| SOVD support adapter | `DEFER` | Requires pinned normative source, security profile, and completion of the sovereign core. |
| VISS interaction profile | `DEFER` | VSS semantic mapping alone is insufficient; not needed for the first milestone. |
| MHS compatibility/parser | `RESEARCH_ONLY` | Normative source artifacts remain unavailable/unreviewed. |
| A2A agent interaction profile | `CREATE_FROM_SPEC` | Canonical role is stated; no public protocol profile exists. |
| MCP courier/tool profile | `CREATE_FROM_SPEC` | Must remain courier/tool-facing and not replace A2A. |
| External vocabulary as internal ontology | `REJECT` | Violates ADR-0007. |

### Wave 5: foreign execution, embodiment, and Web0

| Capability | Classification | Evidence and decision |
|---|---|---|
| Minimal foreign reference runtime | `CREATE_FROM_SPEC` | The first milestone requires a recipient that consumes but cannot author canonical PWM state. |
| Local safety accept/refuse interface | `CREATE_FROM_SPEC` | Must demonstrate independent veto without implementing a safety kernel. |
| Robot kitchen-delivery simulation | `COMPLETE_EXISTING` | Current demo stops before recipient execution and cleanup. |
| Fleet authority conflict simulation | `CREATE_FROM_SPEC` | Documentation exists; the claimed complete test does not. |
| Vehicle service support demonstration | `DEFER` | Depends on lifecycle, Web0, multi-principal authority, COVESA, and SOVD. |
| Signed machine broadcasts | `HARDEN_EXISTING` | Signing exists; ID, key, expiry, replay, payload, and trust validation do not. |
| Web0 discovery/matching/settlement network | `DEFER` | Beyond the first milestone and dependent on production Reasn/BWM/IntentCasting. |
| Business World Model machine entities | `DEFER` | Requires the unavailable production BWM source of truth. |
| Model-to-CAN/EtherCAT/direct actuator path | `REJECT` | Violates local deterministic validation and OEM safety authority. |
| Machine World Model as a new default authority | `REJECT` | BWM can represent machines without inventing a new canonical world model. |

### Wave 6: placement and edge

| Capability | Classification | Evidence and decision |
|---|---|---|
| Placement policy interface | `RESEARCH_ONLY` | Privacy, trust, latency, cost, compatibility, and connectivity objective requires production NEP discovery. |
| Production NEP placement extension | `DEFER` | Must extend the live Neural Engine Protocol rather than create a standalone public substitute. |
| Existing Edge Twin as delegated target | `DEFER` | Requires the live Edge Twin; ADR-0009 forbids duplication absent evidence. |
| Local/edge/cloud/vehicle/robot failover | `EXPERIMENT` | Needs trust and failure simulations after lifecycle enforcement exists. |
| Canonical PWM custody migration for convenience | `REJECT` | Execution placement does not move canonical authority. |

### Wave 7: benchmarks and release

| Capability | Classification | Evidence and decision |
|---|---|---|
| HPL-CONTEXT benchmark | `COMPLETE_EXISTING` | Smoke count exists; needs baseline, utility, threshold, limitations, metadata, and repeatability. |
| HPL-AUTH benchmark | `CREATE_FROM_SPEC` | Unit test is not a benchmark. |
| HPL-SPATIAL benchmark | `CREATE_FROM_SPEC` | Blocked on spatial projection fixture and implementation. |
| HPL-RESIDUE benchmark | `CREATE_FROM_SPEC` | Requires enforceable lifecycle and recipient simulator. |
| HPL-LEAKAGE benchmark | `EXPERIMENT` | Leakage metrics require explicit threat model and proxy validation. |
| HPL-DRIFT benchmark | `EXPERIMENT` | Requires runtime/model compatibility and change fixtures. |
| HPL-HANDOFF benchmark | `CREATE_FROM_SPEC` | Requires two recipient/runtime sessions and bounded artifact transfer. |
| HPL-OFFLINE benchmark | `CREATE_FROM_SPEC` | Requires revocation/expiry and reconnection semantics. |
| Memory-only baseline for PWM falsifier | `EXPERIMENT` | Necessary to test Paper 01's stated falsifier. |
| UOR proof/counterexample executable suite | `EXPERIMENT` | Can test published finite claims without claiming full UOR implementation. |
| Reproducibility package | `CREATE_FROM_SPEC` | No lockfile, environment manifest, seeded fixtures, or result provenance exists. |
| Public release claim audit | `HARDEN_EXISTING` | Claims must match implemented tests, benchmarks, and evidence records. |

## First-milestone gap

The requested milestone is not currently achieved as a complete interoperable flow.

| Milestone link | Existing evidence | Missing evidence | Classification |
|---|---|---|---|
| Provenance-bearing events | In-memory public PLOG profile | Immutable/schema-conformant validated DAG and event signatures | `HARDEN_EXISTING` |
| Reproducible current state | Basic deterministic materializer | Temporal/conflict/supersession profiles and independent replay fixtures | `COMPLETE_EXISTING` |
| Point-in-time query | Lexical `at_time` filter | Valid-time semantics and normalized timestamp behavior | `COMPLETE_EXISTING` |
| Minimal authorized projection | Predicate/privacy filter and set authority | Bound request/decision, field provenance, utility evidence, spatial handling | `COMPLETE_EXISTING` |
| Bound artifact | Ed25519 Arranger-shaped object | Full required bindings and lifecycle enforcement | `COMPLETE_EXISTING` |
| Foreign consumption | None | Reference runtime that cannot mutate canonical PWM | `CREATE_FROM_SPEC` |
| Return/revocation | Candidate and receipt constructors | Revocation, authenticated return, review, reconciliation, and bounded cleanup evidence | `CREATE_FROM_SPEC` |

## ADR and stop-condition assessment

No discovered evidence justifies replacing an accepted ADR. The current implementation is incomplete relative to proposed contracts, but it does not establish that the architectural decisions are invalid.

Implementation must stop for a new or superseding ADR if work would:

- make public event/hash utilities claim canonical UOR semantics;
- make `PLog` a generic log or a replacement for production PLOG;
- turn Arranger into a transport envelope or invent a Hyperframe substitute;
- create a parallel authority system instead of composing Covenant Atoms;
- add a Crystallization Gradient rung;
- make HPL or a model the physical safety kernel;
- create another UHR or Edge Twin;
- let foreign observations mutate canonical state without review and provenance;
- imply deletion stronger than recipient/runtime evidence;
- expose raw PWM state to make an adapter work;
- or treat an unvalidated research claim as implemented fact.

## Recommended critical path

1. Correct status, schema, and claim mismatches before extending behavior.
2. Harden provenance events and deterministic temporal materialization.
3. Bind authority decisions to minimal projection requests and provenance.
4. Complete the Arranger contract and enforce lifecycle controls.
5. Add a minimal foreign runtime, authenticated learning return, revocation, and bounded departure evidence.
6. Turn that complete path into conformance tests and the HPL-CONTEXT/AUTH/RESIDUE/HANDOFF baselines.
7. Only then expand into spatial, standards, embodiment, Web0, and placement experiments.
