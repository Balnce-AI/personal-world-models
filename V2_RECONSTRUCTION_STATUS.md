# V2 Reconstruction Status

**Program:** PWM Public Repository Reconstruction, Package One v1.1

**Branch:** `v2/reconstruction`

**Archive:** `public-v1-archive` at `363fe941b6c71a0235b8479a33ea7a7286e7dbe2`

**Current wave:** Wave 01, public provenance spine
**Gate:** `WAVE_01_PASS`

## Canon

The Personal World Model is the person's sovereign world-model harness.

Memories are evidence, models are derived behavior, and the twelve phenomenological lenses are versioned projections rather than canonical storage buckets. The public reconstruction does not redefine the frozen NEP 12 Technical plus 12 Cognitive topology, the independent R0/OEM safety veto, or the distinction between personal, machine, OEM, and session authority.

## Program State

| Wave | State | Evidence |
|---:|---|---|
| 00 | `PASS` | [`governance/WAVE_00_REPORT.md`](governance/WAVE_00_REPORT.md) |
| 01 | `PASS` | [`governance/WAVE_01_REPORT.md`](governance/WAVE_01_REPORT.md) |
| 02 | `READY_NOT_STARTED` | Wave 01 predecessor gate passed; no Wave 02 implementation has begun |
| 03-13 | `BLOCKED_BY_PREDECESSOR` | Every wave has a hard dependency on the preceding gate |

## Wave 00 Outputs

- [`migration/V1_FILE_LEDGER.md`](migration/V1_FILE_LEDGER.md)
- [`migration/v1_file_ledger.json`](migration/v1_file_ledger.json)
- [`migration/V1_BASELINE_REPORT.md`](migration/V1_BASELINE_REPORT.md)
- [`migration/V1_ARCHIVE_MANIFEST.json`](migration/V1_ARCHIVE_MANIFEST.json)
- [`governance/WAVE_00_REPORT.md`](governance/WAVE_00_REPORT.md)
- Annotated Git tag `public-v1-archive`
- Draft GitHub release with source archive and SHA-256
- Dedicated branch `v2/reconstruction`

## Wave 01 Outputs

- [`spec/public-provenance-profile-v1.md`](spec/public-provenance-profile-v1.md)
- [`governance/WAVE_01_AUTHORITY_RECORD.md`](governance/WAVE_01_AUTHORITY_RECORD.md)
- [`governance/WAVE_01_REPORT.md`](governance/WAVE_01_REPORT.md)
- [`governance/PUBLIC_CLAIM_LEDGER.json`](governance/PUBLIC_CLAIM_LEDGER.json)
- Rust crates under [`crates/`](crates/)
- Public vectors and independent Python oracle under [`conformance/`](conformance/)
- Synthetic scale evidence in [`benchmarks/results/wave01-dag.json`](benchmarks/results/wave01-dag.json)

## Publication Holds

The source-authority corpus and founder-approved publication matrix authorized the bounded Wave 01 profile only. Enabling implementations in these other areas remain held unless their wave receives module-level approval:

- authority beyond a safe public mechanism boundary;
- context minimization and HPL lifecycle internals;
- private UOR/PLOG identity or serialization semantics;
- crystallization/model absorption and personal training;
- general multi-principal legal authority;
- production privacy, edge, federation, routing, and anti-abuse internals.

Public schemas, explicit non-enabling profiles, conformance vectors, independent oracles, synthetic data, and bounded research fixtures remain eligible only after per-component review.

## Authority Inputs

The 13 source-authority documents were supplied out of tree and matched both independent manifests by byte count and SHA-256. They were read in precedence order and were not copied into this public repository. The public-safe decision and bundle provenance are recorded in `governance/WAVE_01_AUTHORITY_RECORD.md`.

## Removed-Path Policy

Previously removed local paths, including `research/`, `architecture/adrs/`, `ROADMAP.md`, `EXECUTION_PLAN.md`, and `site/AI_LAB_PAGE.md`, remain ignored and non-public. The reconstruction will not stage those retained local copies. Any future public path with a similar purpose must be newly authored, public-safe, and reviewed rather than restored silently.

## Next Gate

Wave 01 passed the local acceptance gate. Wave 02 may begin only under its package specification and must not reinterpret the public provenance profile as private UOR/PLOG identity or skip the metagraph, temporal, epistemic, and materialization acceptance requirements.
