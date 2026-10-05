# V1 Signed Semantic Migration

This document maps the abstract `pwm-json-semantics-v1` vocabulary into the signed provisional profile. It is not an automatic conversion rule and does not make unsigned V1 fixtures signed evidence.

## Envelope mapping

| V1 JSON field | Signed profile location |
|---|---|
| `eventId` | verified Wave01 EventBody CID text in reports; not duplicated in payload |
| `eventType` | `EventBody.event_kind` using the mapping below |
| `recordedAt` | no semantic equivalent; append audit time is receipt `ingestion_time`, author assertion is `event_time` |
| `validFrom` | payload `valid_from_ns`, converted exactly to integer UTC nanoseconds |
| `validTo` | payload `valid_to_ns`, exclusive, or null |
| `parents` | `EventBody.parent_event_cids` |
| `payload` | payload envelope `data` after field-name and type conversion |

The signed payload adds `profile`, `schema_version`, and exact closed data maps. Every camelCase data name becomes the snake_case name in `signed-semantic-payloads-v1.md`. RFC 3339 timestamps become integer nanoseconds. JSON numbers that are not exact integers must become normalized fixed-point maps or the migration fails.

## Event vocabulary

| V1 vocabulary | Signed vocabulary |
|---|---|
| `pwm.model.proposed` | `pwm.model.propose` |
| `pwm.model.reviewed` | `pwm.model.review` |
| `pwm.model.accepted` | `pwm.model.accept` |
| `pwm.model.updated` | `pwm.model.update` |
| `pwm.model.disputed` | `pwm.model.dispute` |
| `pwm.model.revoked` | `pwm.model.revoke` |
| `pwm.topology.edge-added` | `pwm.topology.edge` |
| `pwm.possible-world.created` | `pwm.possible-world` |
| `pwm.contradiction.proposed` | `pwm.contradiction.propose` |
| `pwm.contradiction.reviewed` | `pwm.contradiction.review` |
| `pwm.contradiction.accepted` | `pwm.contradiction.accept` |
| no exact V1 event | `pwm.contradiction.resolve` |
| fixture `authority` | `pwm.query-authority` signed event |
| fixture `projectionRequest` | `hpl.request`, then authorization and projection events |

`pwm.family.registered`, `pwm.model.derived`, prediction, and calibration events have no v1 signed-semantic event kind. Preserve them outside this profile or fail migration; do not coerce them into another kind. Conversely, genesis grants, privacy-boundary lifecycle, HPL lifecycle, and conformance evaluation require new signed events.

## Migration procedure

1. Validate the original semantic vector and retain its digest as migration provenance outside the signed payload.
2. Choose one principal scope and a fixed root trust anchor.
3. Create a signed genesis at receipt sequence zero with all required principals and bounded grants.
4. Convert events to closed payload maps, adding explicit evidence, world, privacy, and principal references that V1 inferred from fixture setup.
5. Build canonical CBOR payloads, payload CIDs, unchanged Wave01 EventBodies, signatures, receipts, and frontiers.
6. Replay through both old and new reducers where vocabularies overlap and compare normalized observable state, not event IDs.
7. Record intentional differences, especially authenticated authority, retained history, fixed-point values, and HPL minimization.

An `initialState` fixture cannot migrate directly because the signed reducer has no trusted state injection. Reconstruct it through signed events or classify the case as non-migratable.
