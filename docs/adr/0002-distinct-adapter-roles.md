# ADR-0002: Keep adapter roles distinct

- Status: `ACCEPTED`
- Scope: public extension API

## Decision
Storage, evidence, identity, transport, tool/agent, device, projection and model integrations use separate protocols rather than a universal adapter.

## Consequences
Least privilege and test boundaries remain visible. An implementation may implement multiple protocols, but each role is authorized and assessed independently.
