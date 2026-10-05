# Signed Semantic Conformance v1.0.0 (Provisional)

**Tag:** `signed-semantic-conformance-v1.0.0-provisional`

**Implementation commit:** `f89a72c9a751a093c9d595fcfdaed5b9431899bd`

**Evidence commit:** `65897466ae7e8d266699a743e4d208dced81ea47`

**Claims commit:** `244e522391258f6e83e6c433a6c8e8d940da8f9a`

## Why This Milestone Matters

PWM now has independently implemented Rust and Python semantic reducers that agree over the same cryptographically verified event history. Semantic behavior is no longer demonstrated only inside one reference implementation: it is expressed through public payload maps, signed bundles, expected outcomes, deterministic error precedence, and implementation-neutral tooling.

The profile remains `PROVISIONAL`. This release establishes bounded reproducible agreement, not a permanent standard or production deployment claim.

## Major Areas

- Stabilized normative, reference implementation, ecosystem, and research boundaries.
- Added constrained self, other, relationship, world, meta, and possible-world model ecology.
- Added evidence-backed model lifecycle, contradiction transitions, privacy propagation, and bounded declassification.
- Added HPL capability negotiation, authorized minimum projections, lifecycle/revocation, and non-actuating physical-AI simulation.
- Added provider-neutral model adapters and a public experimental Python SDK facade.
- Added matched-context research protocols, information ledgers, negative controls, and reproducible fixture-control execution.
- Added canonical signed semantic payloads over Wave 01, authenticated principal grants, independent reducers, language-neutral bundles, and semantic diff tooling.

## Evidence

| Evidence | Result |
| --- | --- |
| `PWM-MODEL-ECOLOGY-1` | 21 passing cases per implementation |
| `PWM-SIGNED-SEMANTICS-V1` | Exact Rust/Python agreement over 20 signed cases |
| Suite SHA-256 | `f1fda71d804a3e03ec3157ba11d10696e8f7c57845b622f2ef4c048e6289778b` |
| Result SHA-256 | `02b058aa9a8b72f265a8627e7620ca7db56bb615d86765dd19e2857713fe2f28` |

The formal claims are in [`conformance/claims/`](../../conformance/claims/), with scope and exclusions summarized in [`governance/SIGNED_SEMANTIC_CONFORMANCE_REPORT.md`](../../governance/SIGNED_SEMANTIC_CONFORMANCE_REPORT.md).

The publication gate also ran `gitleaks dir` against the current tree and `gitleaks git` against full history with no detected credentials or provider secrets.

## Limitations

- The signed semantic, model-ecology, HPL, SDK, and research surfaces are not promoted to `STABLE`.
- Fixed synthetic keys and fixtures establish reproducibility, not production key custody or identity assurance.
- No production distributed synchronization, federation, rollback protection, device attestation, remote deletion proof, or safety-certified actuation is included.
- The fixture-control research run validates the harness; no real foundation-model superiority result is claimed.
- Agreement on this finite suite does not prove semantic correctness outside the profile and exact suite digest.

## Next Research Direction

The next evidence-producing work should be independent third-party implementations and preregistered, information-matched foundation-model studies. Major architecture expansion is intentionally paused while external implementers and researchers test the current boundary.
