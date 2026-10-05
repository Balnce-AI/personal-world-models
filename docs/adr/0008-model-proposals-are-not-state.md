# ADR 0008: Model Proposals Are Not Accepted State

**Status:** `PROPOSED`

## Context
Derivations and external models can be wrong, poisoned, or unauthorized.

## Decision
Model creation emits a candidate. Materialized accepted state requires a matching proposal, explicit review record, evidence closure, ontology validation, privacy propagation, and acceptance event. Model adapters receive no canonical write handle.

## Alternatives
Direct last-write-wins updates were rejected because they erase review and provenance boundaries.

## Consequences
Implementations need lifecycle state and additional events. V1 actor strings remain reference-only until integrated with signed V2 identity.
