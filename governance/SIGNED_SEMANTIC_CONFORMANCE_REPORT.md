# Signed Semantic Conformance Report

## Bounded Result

| Field | Value |
| --- | --- |
| Profile | `pwm-signed-semantics-v1` (`PROVISIONAL`) |
| Suite | `PWM-SIGNED-SEMANTICS-V1` `1.0.0` |
| Suite SHA-256 | `f1fda71d804a3e03ec3157ba11d10696e8f7c57845b622f2ef4c048e6289778b` |
| Implementation source | `f89a72c9a751a093c9d595fcfdaed5b9431899bd` |
| Evidence commit | `65897466ae7e8d266699a743e4d208dced81ea47` |
| Signed suite cases | 20 |
| Cumulative level cases | 21 |
| Normalized result SHA-256 | `02b058aa9a8b72f265a8627e7620ca7db56bb615d86765dd19e2857713fe2f28` |
| Rust/Python semantic differences | 0 |

The claim records exact agreement between independently implemented Rust and Python reducers after Wave 01 verification. The checked-in result artifacts are byte-identical.

## Exclusions

- Interoperability beyond the exact profile, suite version, and suite digest above.
- Production identity, key custody, delegation, recovery, distributed synchronization, and storage durability.
- Private Balnce internals, private PLOG semantics, physical actuation, and safety certification.

The result does not promote the profile, model ecology, HPL, SDK, or extensions from `PROVISIONAL` or `EXPERIMENTAL` to `STABLE`.
