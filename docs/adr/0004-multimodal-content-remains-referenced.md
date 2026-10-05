# ADR-0004: Multimodal content remains referenced

- Status: `ACCEPTED`
- Scope: public records and adapters

## Decision
Events carry integrity-bound, provenance-bearing multimodal references, not media blobs.

## Consequences
External substrate custody and deletion limits must be declared. Consumers validate digest, type, size and provenance before decoding.
