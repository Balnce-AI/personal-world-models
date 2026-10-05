# ADR-0001: Event log is the reconstruction source

- Status: `ACCEPTED`
- Scope: public reference architecture

## Decision
Immutable provenance events are the source of deterministic reconstruction. Materialized PWM state is disposable and must not be directly mutated by extensions.

## Consequences
All durable changes cross `EventSink`; simulations and adapters cannot receive canonical-state handles. Event closure and ordering become portability obligations.
