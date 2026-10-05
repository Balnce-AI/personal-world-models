# Physical AI HPL simulator scenarios

**Status:** `EXPERIMENTAL` simulation

These eight fixtures exercise contract behavior without controlling hardware. Expected execution dispositions are only `WOULD_DISPATCH` or `REFUSED`; `actuationPerformed` is always false. Local safety is an independent veto and this experiment makes no safety certification claim. The foreign runtime has no PWM or PLog handle, and every generated record declares `canonicalV2Effect: NONE`.

The target profiles and field rules are illustrative rather than normative device policy. Scenario 8 combines the compromised-device assumption with graceful degradation to keep the suite at eight scenarios while covering both concerns.

Error semantics are fail-closed. Binding, freshness, unknown capability, consent, policy, revocation, and safety failures have stable machine-readable codes; retryability is explicit where negotiation can reasonably be retried.
