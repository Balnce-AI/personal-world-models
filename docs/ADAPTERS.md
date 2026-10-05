# Adapter contracts

Status: `EXPERIMENTAL`; descriptor and error vocabularies are versioned public contracts.

## Distinct roles

| Protocol | Responsibility | Explicit non-responsibility |
|---|---|---|
| `StorageAdapter` | Append and ordered event snapshots | Policy, inference, projection |
| `EvidenceAdapter` | Provenance-bearing observations and authorized durable promotion drafts | Authority, raw state mutation |
| `IdentityAdapter` | Identifier resolution and proof verification | Granting capabilities |
| `TransportAdapter` | Authorized artifact transfer | Interpreting artifact semantics |
| `ToolAgentAdapter` | Authorized bounded tool invocation | Canonical writes unless separately routed as events |
| `DeviceAdapter` | Device observations and explicitly authorized actuation | Local safety replacement |
| `ProjectionAdapter` | Apply an already-issued authorization to a state/request | Minting authorization |
| `ModelAdapter` | Capability discovery and inference | Acceptance of candidates into PWM |

Every adapter implements bounded lifecycle and `capabilities()`. Do not create an adapter implementing every role merely to reduce wiring: compromise, authorization and data exposure differ by role.

## Capability discovery

Descriptors contain ID, version, exact semantics, operations, status and constraints. Discovery is not negotiation, endorsement, conformance evidence, attestation or authority. Callers must reject unsupported semantics and independently authorize each operation.

## Evidence and streams

`MultimodalReference` carries URI, media type, digest, provenance, privacy segment and optional byte/time metadata. It never carries media bytes. `StreamWindow` is ephemeral unless `durable_event_ref` identifies an accepted promotion event. Promotion returns an `EventDraft`; only a caller with an authorization reference may append it.

## Third parties

Use a reverse-domain or organization namespace, pin semantic sources and versions, expose the smallest protocol, document custody/dependencies, add lifecycle and unknown-semantic tests, and start from `templates/adapter/`. See `examples/third-party-adapter/`.
