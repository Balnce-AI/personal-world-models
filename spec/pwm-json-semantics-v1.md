# PWM JSON Semantics Profile v1

**Status:** `PROVISIONAL`  
**Purpose:** language-independent semantic conformance; not the canonical V2 wire/event profile

This profile defines the abstract reducer used by `PWM-MODEL-ECOLOGY-V1` and `HPL-PROJECTION-V1`. Inputs are already integrity-verified events in deterministic causal order. Implementations MUST NOT infer that this JSON envelope replaces the canonical CBOR, CID, signature, receipt, or key-state rules in `public-provenance-profile-v1.md`.

## Event Envelope

Every event has `eventId`, `eventType`, `recordedAt`, and `payload`. Optional `validFrom`, `validTo`, and `parents` describe modeled validity and causal parents. An implementation MUST process the array in supplied order after checking that every declared parent precedes its child. Unknown standard event types fail with `UNSUPPORTED_EVENT_TYPE`; extension events require a declared extension manifest.

## Model Lifecycle

The standard transition is:

```text
pwm.model.proposed -> pwm.model.reviewed -> pwm.model.accepted
                                      \-> pwm.model.updated
```

Proposal identifies the complete candidate and evidence references. Review identifies the proposal and decision. Acceptance identifies both proposal and review and MUST preserve candidate semantics and evidence. `updated` additionally identifies an existing accepted predecessor, which becomes historical `SUPERSEDED`. `disputed` preserves the model but excludes it from default current queries. `revoked` and `superseded` are not current.

Direct acceptance without proposal and review fails with `LIFECYCLE_PRECONDITION_MISSING`. Invalid family/kind combinations fail with `FAMILY_KIND_NOT_ALLOWED`.

## Standard Event Registry

| Event type | Required payload | Atomic effect |
|---|---|---|
| `pwm.family.registered` | `familyId`, `allowedKinds`, `stability` | Add one previously unknown namespaced family; duplicate or incompatible definitions fail. |
| `pwm.model.proposed` | complete candidate including `modelId`, family, kind, subjects, perspective, evidence and privacy | Validate and add only to candidate state. |
| `pwm.model.reviewed` | `modelId`, `proposalEventId`, `decision`, `reviewer` | Record review for the exact candidate; no accepted-state effect. |
| `pwm.model.accepted` | `modelId`, `proposalEventId`, `reviewEventId` | Materialize the unchanged reviewed candidate. |
| `pwm.model.updated` | acceptance fields plus `previousModelId` | Materialize successor and mark an existing accepted predecessor historical. |
| `pwm.model.disputed` | `modelId`, `reason` | Retain model and mark it disputed. |
| `pwm.model.revoked` | `modelId`, `reason` | Retain history and exclude model from current queries. |
| `pwm.model.derived` | model identity, family/kind, source IDs, privacy | Register a research derivation artifact; it is not accepted person state without the standard lifecycle. |
| `pwm.topology.edge-added` | edge ID, endpoints, edge type, privacy | Add only when endpoints exist and `DEPENDS_ON` remains acyclic. |
| `pwm.possible-world.created` | non-actual `worldId`, `parentWorldId`, `baseStateId`, `baseTime` | Create an isolated world scope; no actual-state mutation. |
| `pwm.contradiction.proposed` | contradiction ID, typed conflicting references, status | Add only to contradiction candidates. |
| `pwm.contradiction.reviewed` | contradiction ID, proposal ID, decision, reviewer | Record review without resolving or accepting a winner. |
| `pwm.contradiction.accepted` | contradiction ID, proposal ID, review ID | Materialize the contradiction while retaining all inputs. |
| `pwm.prediction.recorded` | prediction ID, model ID, evaluator ID | Retain immutable forecast metadata. |
| `pwm.calibration.recorded` | prediction ID, evaluator ID, score | Append evaluator-scoped calibration without rewriting prediction. |

Every identifier reference MUST resolve in the already accepted prefix unless an event definition explicitly creates that identifier. Unknown or missing required payload members fail before mutation.

## State And Time

Materialization starts from empty entities, relations, assertions, models, edges, contradictions, predictions, and calibration records. Events are applied atomically. Invalid events do not partially mutate state. `recordedAt` is audit time; `validFrom` is inclusive and `validTo` exclusive. Current queries select accepted records valid at `asOfValidTime` and retain superseded records as history.

## Kinds And Topology

Model kinds are `SELF`, `OTHER`, `RELATIONSHIP`, `WORLD`, `META`, and `POSSIBLE_WORLD`. Family constraints define legal kinds and cardinality. `DEPENDS_ON` MUST remain acyclic and every edge endpoint MUST resolve before commit. Possible-world records name a non-actual `worldId` and parent; actual-world queries exclude them.

## Contradictions

Contradiction declaration follows proposal/review/acceptance semantics. It preserves incompatible references and does not select a winner. Resolution appends a resolution record; it does not erase source evidence. Default queries omit disputed models unless `includeDisputed` is true.

## Privacy And Queries

Effective privacy is the lattice join defined by `privacy-propagation.md`. A record may declare a lower class than its inputs only if materialization raises `effectivePrivacyClass`; claiming a lower effective class without an authorized proof/redaction boundary fails with `PRIVACY_EFFECTIVE_CLASS_MISMATCH`. Query authorization binds subjects, perspectives where required, families, recipient, purpose, expiry, world, and privacy ceiling. Multi-subject relationship records require authority covering every represented subject or an explicit joint-disclosure policy.

## Fixture Evaluation

Each case declares `decision`, stable `error.code` when rejected, observable output fragments, and invariants. Implementations compare maps without relying on object-key order and compare arrays in declared semantic order. A suite may test invariants where IDs are implementation-derived. Passing a schema alone is not conformance.

`input.initialState`, when present, is fixture setup rather than an event: it is assumed already valid under the named profile and exists only to isolate query, privacy, or topology operations from lifecycle setup. It MUST NOT be interpreted as a portable bypass for production ingestion.

Expected sections have these meanings: `materialized` is the post-reducer state fragment, `query` is the deterministic selected-ID/result fragment, `privacy` is the computed lattice result, `contradictions` is accepted contradiction state, `topology` is committed graph state, `possibleWorlds` is world-scoped state, and `projection` is the recipient-visible result. An implementation MUST compare every member present in `expected`; omitted sections make no assertion.
