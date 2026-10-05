# Synchronization and federation

Status: `PROPOSED`, design-only. No wire protocol or production federation is implemented here.

## Sync semantics

- Exchange immutable events plus parent references; causal parents precede dependent application.
- Deterministically order concurrent events without pretending that ordering resolves semantic conflict.
- A partial replica declares included privacy segments, event ranges and omitted-parent commitments.
- Offline writers retain local events and reconcile by event identity and causal closure, never last-write-wins over canonical meaning.
- Revocations are events. Peers maintain revocation cursors and reject artifacts beyond their freshness policy when the cursor is stale.
- Privacy segments are separately authorized and encrypted; possession of one segment reveals no entitlement to another.
- Deletion/departure evidence states what was observed and cannot prove remote erasure beyond the available mechanism.

## Federation connection points

Identity resolves principals and verifies proofs. Transport exchanges bounded artifacts. Storage persists accepted event closures. Projection limits disclosure before transfer. Policy/authority remains local and deny-by-default. Receipts record bounded outcomes. None of these connection points is a global trust root.

## Required envelope concepts

A future protocol must bind protocol version, sender, recipient, purpose, event IDs, parent closure, privacy segment, sequence/cursor, expiry, nonce, revocation cursor, content digest and signature. Unknown versions or semantics are quarantined, not guessed.

## Open proof obligations

Partition convergence, metadata leakage, causal garbage collection, key rotation, selective revocation, rollback, clock uncertainty, schema upgrade and denial-of-service limits require simulation and conformance vectors before implementation status can advance.
