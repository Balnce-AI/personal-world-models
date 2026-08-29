---
status: PROPOSED
version: 0.1.0
---
# HPL Projection Lifecycle

1. **DISCOVER** — obtain recipient identity, capability description, runtime profile, constraints, jurisdiction and attestation evidence.
2. **REQUEST** — declare task, purpose, requested data/artifact classes, duration and retention requirements.
3. **RE-GROUND** — translate external vocabulary into internal semantics without making the external schema canonical.
4. **AUTHORIZE** — evaluate principal authority, Covenant constraints, policy, consent and vetoes.
5. **PLACE** — choose an allowed execution environment.
6. **CRYSTALLIZE** — select the least persistent representation that can satisfy the task.
7. **ISSUE** — bind/sign the Arranger or projection object.
8. **EXECUTE** — recipient acts under local runtime and safety controls.
9. **OBSERVE** — collect receipts and optional learning candidates.
10. **REVOKE/EXPIRE** — terminate authority by policy, time, manual action, event or safety condition.
11. **DEPART** — recipient performs the declared unload/cleanup protocol and emits evidence.
12. **RECONCILE** — sovereign model evaluates learning candidates and records accepted derivations.

Every transition SHOULD produce a provenance event in implementations that support an auditable event substrate.
