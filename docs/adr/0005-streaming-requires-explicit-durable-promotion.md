# ADR-0005: Streaming requires explicit durable promotion

- Status: `ACCEPTED`
- Scope: stream ingestion

## Decision
Stream windows are ephemeral until an authorized event records durable promotion through the public event interface.

## Consequences
Observation and inference do not imply retention. Backpressure, gaps, replay and promotion policy are explicit.
