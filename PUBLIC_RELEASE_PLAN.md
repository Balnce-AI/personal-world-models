# Public Release Policy

## Current Milestone

Python package version `0.2.0` accompanies the stabilized research/developer platform and the provisional Signed Semantic Conformance v1 milestone. The Rust reference crates remain `0.2.0-alpha.1`.

The repository's version axes are independent: package version, protocol/profile version, schema version, ontology version, conformance-suite version, and extension version do not silently advance one another. See [`VERSIONING.md`](VERSIONING.md).

## Publication Gate

A public milestone requires:

1. a clean tracked worktree and reviewed diff;
2. complete Python and Rust verification appropriate to the change;
3. schema, status, lockfile, formatting, and lint checks;
4. deterministic conformance regeneration where relevant;
5. full-history and current-tree secret scanning;
6. public/private boundary review;
7. evidence-bound claims with explicit limitations;
8. release notes and citation metadata;
9. non-force push and remote verification.

## Current Evidence

- `platform-stabilization-v0.2.0` records the stabilization checkpoint.
- `signed-semantic-conformance-v1.0.0-provisional` records the signed semantic claims boundary.
- `conformance/claims/` binds implementation and evidence commits to the exact suite digest.
- `governance/SIGNED_SEMANTIC_CONFORMANCE_REPORT.md` summarizes the reproducible result.

## Temporary Freeze

The current architecture is held at a temporary stabilization boundary. Permitted follow-up work is limited to bug fixes, conformance corrections, documentation, external implementation support, researcher questions, benchmark execution, bounded vectors, and carefully scoped security work. See [`governance/ARCHITECTURAL_FREEZE.md`](governance/ARCHITECTURAL_FREEZE.md).

## Future Release Evidence

Logical next milestones are external implementations and preregistered foundation-model experiments. Version numbers and dates are not promised in advance. A release should lead with the problem and primitive, then support claims with reproducible evidence rather than promotional language.
