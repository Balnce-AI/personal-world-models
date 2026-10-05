# ADR 0010: HPL Is The External Projection Boundary

**Status:** `PROPOSED`

## Context
Applications and machines need bounded human context, not unrestricted PWM access.

## Decision
External disclosure passes through recipient-, purpose-, capability-, authority-, privacy-, and time-bound HPL negotiation and a bounded projection artifact. Capability discovery is evidence, not permission. Physical execution remains behind independent local safety.

## Alternatives
Direct PWM reads and permanent context exports were rejected.

## Consequences
Targets must advertise understood capabilities, projections expire, and recipients can receive transformed or derived fields without receiving source evidence.
