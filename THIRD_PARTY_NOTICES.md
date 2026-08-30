# Third-Party Notices

**Status:** `IMPLEMENTED` dependency-governance scaffold

The V1 Python reference declares these direct dependencies:

| Dependency | Purpose | Declared constraint | Integration |
|---|---|---|---|
| `cryptography` | Ed25519 reference signing | `>=45` | Python package dependency |
| `jsonschema` | Schema validation tests | `>=4.20` | Python package dependency |
| `pytest` | Test runner | `>=8` | Development dependency |

CI generates a dependency license report and CycloneDX SBOM from the resolved environment. Those artifacts describe the CI resolution, not a locked dependency closure; V1 has no lockfile and therefore is not dependency-reproducible.

The V2 Rust workspace records exact crate versions in `Cargo.toml` and commits `Cargo.lock`. Direct dependencies are `clap`, `ed25519-dalek`, `hex`, `proptest`, `rusqlite` with bundled SQLite, `serde`, `serde_json`, `sha2`, `tempfile`, `thiserror`, and `unicode-normalization`. CI audits the lockfile, fails when a resolved crate omits a declared license, and emits CycloneDX 1.5 SBOMs. `scripts/rust_supply_chain.py` produces the resolved license inventory; package declarations still require human license and notice review before release.

No OM1, OM1-sim, FABRIC, RoboPay, hosted OpenMind service, or other Wave 08 source has been copied, linked, vendored, or behaviorally reimplemented in V2 at Wave 00. Each future external source requires an exact commit/version, repository and file-level license review, dependency/SBOM evidence, required notices, security review, and an explicit disposition before integration.

This file is an engineering provenance record, not legal advice.
