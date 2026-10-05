# ADR-0003: Capability discovery is not authority

- Status: `ACCEPTED`
- Scope: public SDK and extensions

## Decision
Capability descriptors are versioned support claims only. Every query, disclosure, transfer, tool call, durable promotion and actuation requires a separate authorization decision.

## Consequences
Discovery cannot enable behavior. Missing or malformed authorization fails closed.
