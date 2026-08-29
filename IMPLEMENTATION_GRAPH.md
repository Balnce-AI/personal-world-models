---
status: RESEARCH
audit_date: 2026-08-28
repository_version: 0.1.0
---

# Implementation Graph

## Reading the graph

This is a dependency graph, not a directory tree. Solid edges describe imports or direct data dependencies present in the repository. Dashed edges describe specified but absent links required for the first milestone. A foreign runtime never becomes a source of canonical PWM state.

## Existing executable graph

```mermaid
flowchart TD
    CJ[canonical_json]
    H[sha256_urn<br/>conventional hash, not UOR]
    SIG[Ed25519 sign_json / verify_json]
    E[PLog Event DAG profile]
    M[Materializer]
    W[PWMState]
    C[Authority Constraint]
    A[AuthorityEngine Decision]
    R[ProjectionRequest]
    PC[ProjectionCompiler]
    PM[Projection Manifest]
    AI[ArrangerIssuer]
    AR[Signed Arranger artifact<br/>not Hyperframe]
    LC[Learning Candidate]
    DR[Departure Receipt]
    WB[Signed Machine Broadcast]
    D[Demo]
    HC[HPL-CONTEXT smoke]

    CJ --> H
    CJ --> SIG
    H --> E
    E --> M
    M --> W
    C --> A
    A --> PC
    R --> PC
    W --> PC
    H --> PC
    PC --> PM
    PM --> AI
    H --> AI
    SIG --> AI
    AI --> AR
    H --> LC
    H --> DR
    H --> WB
    SIG --> WB
    E --> D
    M --> D
    A --> D
    PC --> D
    AI --> D
    LC --> D
    DR --> D
    WB --> D
    D --> HC
```

## Actual Python import graph

| Consumer | Direct repository dependency | Role |
|---|---|---|
| `plog.py` | `canonical.sha256_urn` | Hash event bodies and identifiers. |
| `pwm.py` | `plog.PLog` | Replay ordered provenance-profile events. |
| `projection.py` | `canonical.sha256_urn`, `authority.Decision`, `pwm.PWMState` | Compile selected state under a capability decision. |
| `crypto.py` | `canonical.canonical_json` | Sign and verify local canonicalized JSON bytes. |
| `arranger.py` | `canonical.sha256_urn`, `crypto.sign_json`, `crypto.verify_json` | Identify and sign an Arranger artifact. |
| `learning.py` | `canonical.sha256_urn` | Identify a non-canonical learning candidate. |
| `departure.py` | `canonical.sha256_urn` | Identify a bounded departure record. |
| `web0.py` | `canonical.sha256_urn`, `crypto.sign_json`, `crypto.verify_json` | Identify and sign a machine broadcast. |
| `demo.py` | PLOG, PWM, authority, projection, crypto, Arranger, learning, departure, Web0 | Compose the current demonstration. |
| HPL-CONTEXT harness | Demo fixture, materializer, authority, projection | Count disclosed assertions. |

`authority.py` has no repository imports. The HCP, COVESA VSS, and WoT adapters are standalone transformation modules and are not wired into `demo.py` or the lifecycle.

## Current data flow

```text
fixture assertion dictionaries
    -> PLog.append()
    -> public Event records with SHA-256 identifiers
    -> PLog.ordered()
    -> Materializer.materialize()
    -> PWMState

requested capabilities + Constraint records
    -> AuthorityEngine.resolve()
    -> Decision

PWMState + ProjectionRequest + Decision
    -> ProjectionCompiler.compile()
    -> Projection Manifest
    -> ArrangerIssuer.issue()
    -> signed Arranger artifact dictionary

foreign observation (simulated locally)
    -> learning_candidate()
    -> candidate dictionary, not canonical PWM mutation

session end evidence (simulated locally)
    -> make_receipt()
    -> unsigned departure record

machine claim
    -> issue_broadcast()
    -> signed broadcast evidence, not authorization
```

## Existing evidence graph

```mermaid
flowchart LR
    INV[Published architectural invariants] --> SPEC[Proposed specs]
    SPEC --> SCH[JSON Schema / TypeScript]
    SPEC --> MATH[Math profiles]
    SPEC --> CODE[Reference code]
    SCH --> ST[Schema metaschema test]
    CODE --> RT[Reference behavior tests]
    CODE --> AT[Adapter tests]
    CODE --> DEMO[Generated demo output]
    CODE --> BENCH[HPL-CONTEXT smoke]
    SEC[Threat model and trust assumptions] -. requirements .-> CODE
    STD[Standards mappings] --> AD[Boundary adapters]

    classDef gap stroke-dasharray: 5 5;
    SEC:::gap
```

The evidence graph has three breaks:

- Schemas are validated as schemas but are not used to validate code-generated instances.
- Security requirements are mostly documented fields rather than verifier behavior.
- Benchmarks do not yet test the core utility, authority, lifecycle, or falsifier claims.

## First-milestone target graph

```mermaid
flowchart TD
    OBS[Observation / action / assertion]
    PUBID[Validated public event identifier<br/>explicitly not UOR]
    PLOG[Immutable provenance DAG profile]
    MAT[Versioned deterministic materializer]
    PWM[Point-in-time PWM view]
    REQ[Schema-conformant Projection Request]
    AUTH[Explainable composed authority decision<br/>Covenant-compatible profile]
    MIN[Minimum projection compiler]
    PROJ[Projection Manifest + provenance trace]
    ARR[Complete signed Arranger artifact]
    CARRIER[Carrier boundary<br/>Hyperframe in production]
    FOREIGN[Foreign reference runtime<br/>non-authoritative]
    SAFETY[Local deterministic safety decision]
    OUTCOME[Signed outcome / learning candidate]
    REVIEW[Guardian/policy/epistemic review profile]
    DERIVE[Accepted provenance derivation]
    REVOKE[Expiry / nonce / revocation enforcement]
    DEPART[Evidence-tiered signed departure]

    OBS --> PUBID --> PLOG --> MAT --> PWM
    PWM --> MIN
    REQ --> AUTH --> MIN
    MIN --> PROJ --> ARR --> CARRIER --> FOREIGN
    FOREIGN --> SAFETY
    SAFETY --> OUTCOME --> REVIEW
    REVIEW -->|accept / branch / merge| DERIVE --> PLOG
    REVIEW -->|reject / defer| PLOG
    ARR --> REVOKE --> FOREIGN
    FOREIGN --> DEPART --> PLOG
```

The carrier node is an explicit boundary, not permission to invent a new envelope. In the public repository, a small test carrier or function boundary may demonstrate transport neutrality; production integration must use the existing Hyperframe implementation after discovery.

## Foundational dependency layers

| Layer | Inputs | Outputs | Must be true before dependents proceed |
|---|---|---|---|
| 0. Canon and evidence | Published specifications, status taxonomy, source records | Versioned terminology and claim ledger | Protected meanings and evidence status are mechanically checkable. |
| 1. Public encoding | Canonicalization profile, schemas | Validated bytes and conventional IDs | Deterministic behavior is specified without claiming UOR. |
| 2. Provenance profile | Validated events and parents | Immutable event DAG/closure | Parent/hash/time/signature rules fail closed. |
| 3. Materialization | Authorized event closure, schema/conflict profile, point in time | Reproducible PWM view | History/current state and evidence/interpretation remain distinct. |
| 4. Authority | Requested purpose/capabilities and typed principal constraints | Explainable bounded decision | Capability is not authorization; Covenant compatibility is preserved. |
| 5. Projection | PWM view, exact authority decision, recipient/environment profile | Minimal projection plus trace | Raw PWM does not cross the boundary; unknown semantics fail closed. |
| 6. Crystallization | Projection and representation policy | One of five canonical rungs | No sixth rung is introduced. |
| 7. Arranger | Crystallized payload and bindings | Signed, revocable artifact | Arranger remains distinct from Hyperframe. |
| 8. Foreign execution | Artifact, carrier, runtime compatibility | Local accept/refuse and bounded outcome | Foreign runtime is non-authoritative; local safety can veto. |
| 9. Lifecycle return | Outcome, revocation/expiry state, departure evidence | Candidate, receipt, review decision | No silent mutation or universal forgetting claim. |
| 10. Reconciliation | Accepted review decision | New provenance derivation and rematerialized PWM | Every accepted state change is attributable. |
| 11. Interoperability | Stable boundary contracts | HCP/A2A/MCP/ROS/VSS/SOVD/WoT mappings | External vocabularies remain adapters, not semantic authority. |
| 12. Demonstrations and benchmarks | Complete vertical slice | Reproducible claims and falsifiers | Every claim names a baseline, metric, threshold, and limitation. |

## Adapter dependency graph

```mermaid
flowchart LR
    EXT[External description / protocol]
    NORM[Version-pinned normalization]
    MAP[Capability Mapping Record]
    REGROUND[Fail-closed semantic re-grounding]
    AUTH[Authority evaluation]
    PROJ[Projection or procedure]
    LOCAL[Foreign runtime + local safety]

    EXT --> NORM --> MAP --> REGROUND --> AUTH --> PROJ --> LOCAL

    HCP[HCP experiment] -. currently maps projection fields .-> MAP
    VSS[VSS experiment] -. currently maps 3 signals .-> MAP
    WOT[WoT experiment] -. currently extracts affordances .-> MAP
    ROS[ROS 2 proposed] -. absent .-> LOCAL
    SOVD[SOVD proposed] -. absent .-> LOCAL
    MHS[MHS research only] -. blocked on normative artifacts .-> NORM
```

The current adapters do not share a common Capability Mapping Record, pinned-source registry, or lifecycle integration. Their tests correctly establish only narrow boundary properties.

## Demonstration dependencies

| Demonstration | Required predecessor chain | Current state |
|---|---|---|
| First milestone: foreign bounded projection | Layers 0 through 10 | Stops at locally constructed artifact/candidate/receipt records; no foreign runtime or reconciliation. |
| Robot kitchen delivery | First milestone + spatial projection + local safety fixture | Partial local demo only. |
| Fleet authority conflict | Typed authority + changing local machine state + explanation | Documentation and generic set test only. |
| Vehicle service support | Web0 broadcast + multi-principal authority + VSS/VISS + SOVD + lifecycle | Proposed and intentionally deferred. |
| Sovereign AI Grid | Production NEP + Guardian + existing Edge Twin + placement evidence | Not implementable honestly from this public repository alone. |

## Test dependency graph

```text
schema metaschema validity
    -> generated-instance conformance
    -> module contract tests
    -> provenance/materialization conformance
    -> authority/projection conformance
    -> artifact lifecycle conformance
    -> foreign-runtime integration
    -> learning/departure reconciliation
    -> interoperability profiles
    -> benchmarks and falsifiers
```

Only the first level and selected module behavior tests exist. No later evidence should be treated as proven until its predecessor evidence exists.

## Production fold-in boundary

The following production nodes are intentionally outside the executable public graph and must be discovered before integration:

- canonical UOR object/address/certificate owners;
- canonical PLOG signer, DAG, and derivation owners;
- production PWM/metagraph stores and materializers;
- Covenant Atom and Guardian decision owners;
- Hyperframe and live Arranger/D5 owners;
- NEP extension and placement owners;
- UHR runtime owners;
- A2A and MCP boundary owners;
- existing Edge Twin owners;
- BWM, Web0, and IntentCasting owners.

Until those repositories are supplied, all production graph edges remain `DEFER`, and no public module may be promoted into a competing authority.
