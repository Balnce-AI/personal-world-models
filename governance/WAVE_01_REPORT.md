# Wave 01 Completion Report

## Wave

- ID: Wave 01, Canonical Bytes, Typed IDs, Crypto Profile, and Causal Event DAG
- Date: 2026-08-29
- Builder: OpenCode under founder direction
- Branch: `v2/reconstruction`
- Tracking issue: [Wave 01](https://github.com/Balnce-AI/personal-world-models/issues?q=is%3Aissue+%22Wave+01%22)

## Grounding

The 13-file source-authority bundle was acquired outside this repository and verified byte-for-byte against two independent manifests. Its archive SHA-256 and the founder's public-profile authorization are recorded in `WAVE_01_AUTHORITY_RECORD.md`; source contents are not redistributed.

The approved implementation is a bounded public interoperability profile. It is explicitly not private UOR, the private production PLOG, a resolution of UOR-to-Atom/PLOG/PWM identity, or a disclosure of production key custody, recovery, Guardian, Edge, routing, anti-abuse, or topology internals. No canon conflict was found.

## Implemented

- Restricted RFC 8949 deterministic CBOR with fail-closed canonical decoding and resource limits.
- Domain-separated typed CIDv1 raw SHA-256 identifiers.
- Raw Ed25519 event-author and append-receipt signatures.
- Exact event and receipt records with integer nanosecond times.
- Schema binding, sorted unique parents, genesis/branch/merge, parent and scope checks, per-key causal sequence, key activation/rotation/revocation, and historical frontier verification.
- Deterministic topological replay with raw-CID tie-breaking.
- Atomic SQLite append, idempotent retry, process-crash recovery, complete reopen verification, and edge-table integrity checks.
- Rust CLI vector generation, verification, and replay.
- Independent Python conformance oracle.
- Public valid and malformed vectors.
- Synthetic 1K/10K/100K validation and replay benchmark.

## Tests Run

```text
cargo fmt --all --check: pass
cargo clippy --workspace --all-targets -- -D warnings: pass
cargo test --workspace: 36 passed, 0 failed, 1 ignored child-process helper
pytest: 25 passed
status metadata linter: valid
workflow YAML parse: valid
Rust/Python valid bundle verification: 4 events each
Rust/Python deterministic replay: identical
malformed corpus: 16 cases rejected by Rust and Python
gitleaks history and worktree: no leaks
cargo-audit 0.22.2: no vulnerabilities reported
Rust dependency license inventory: 124 resolved packages, all with declarations
CycloneDX 1.5 SBOM generation: pass
```

Property tests use `proptest` generated cases. The final bounded fuzz verification used `cargo-fuzz 0.13.2` and pinned `nightly-2026-08-01`: the canonical decoder completed 676,022 executions and the event-body decoder completed 498,285 executions with no crashes.

## Acceptance Matrix

| Dimension | Result | Evidence |
|---|---|---|
| Architecture | PASS | `spec/public-provenance-profile-v1.md` defines a bounded provenance spine and excludes later-wave semantics. |
| Code | PASS | `pwm-canonical`, `pwm-crypto`, `pwm-event`, and `pwm-cli` implement the complete Wave 01 public path. |
| Correctness | PASS | Golden, malformed, property, mutation, DAG, key lifecycle, SQLite, and CLI tests pass. |
| Independent conformance | PASS | Rust-generated vectors are byte-stable; the clean-room Python oracle independently verifies them and emits identical replay order. |
| Security | PASS | Domain separation, strict parsing, weak-key rejection, append-order revocation, corruption checks, audit, and secret scans pass within the declared profile. |
| Privacy/custody | PASS | Synthetic identities and payloads only; no real-person data, credentials, private policy, or production topology are present. |
| Durability | PASS | SQLite transaction rollback, real process abort, verification of all present records on reopen, strict retry matching, and historical receipt verification pass. |
| Determinism | PASS | Exact CBOR/CID/signature vectors regenerate byte-for-byte and replay is permutation invariant with a specified CID tie-break. |
| Performance | PASS | Release benchmark completed 1K, 10K, and 100K event validation/replay with environment metadata. |
| Science | PASS | `PUBLIC_CLAIM_LEDGER.json` records evidence, falsifiers, and limitations for every Wave 01 claim. |
| Docs | PASS | Public specification, crate READMEs, commands, boundaries, authority record, benchmark documentation, and this report are present. |
| Visuals | PASS | `diagrams/source/signed-event-dag.dot` and `diagrams/exports/signed-event-dag.svg` describe the implemented flow. |
| Third-party provenance | PASS | Exact Rust versions are locked; license inventory, advisory audit, and CycloneDX generation are automated. No external product source was integrated. |
| IP/release | PASS | The founder-authorized safe profile is marked `RELEASABLE`; restricted production mechanisms remain excluded. |
| Reproducibility | PASS | Toolchains, dependencies, vectors, malformed corpus, commands, benchmark implementation, and machine result are checked in. |

## Performance

The recorded release-build result on macOS/aarch64 with Rust 1.96.0 is:

| Events | Append validation events/s | Replay events/s |
|---:|---:|---:|
| 1,000 | 9,573 | 1,946,153 |
| 10,000 | 9,761 | 1,921,968 |
| 100,000 | 9,715 | 851,174 |

The raw nanosecond measurements and environment are in `benchmarks/results/wave01-dag.json`. These single-run synthetic linear-DAG results are evidence that all required sizes completed. They are not service-level objectives or production capacity claims.

## Artifacts

- `Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`
- `crates/pwm-canonical/`
- `crates/pwm-crypto/`
- `crates/pwm-event/`
- `crates/pwm-cli/`
- `conformance/vectors/wave01-valid.json`
- `conformance/vectors/wave01-invalid.json`
- `conformance/python/pwm_oracle.py`
- `fuzz/`
- `spec/public-provenance-profile-v1.md`
- `governance/WAVE_01_AUTHORITY_RECORD.md`
- `governance/PUBLIC_CLAIM_LEDGER.json`
- `benchmarks/results/wave01-dag.json`
- `diagrams/source/signed-event-dag.dot`
- `diagrams/exports/signed-event-dag.svg`

## Negative Results / Limitations

- The initial fuzz command on stable Rust failed because sanitizer flags require nightly; fuzzing was rerun successfully on the pinned nightly toolchain.
- Local `cargo-audit 0.21.2` could not parse a CVSS 4 advisory record; the tool was upgraded to the exact CI version, 0.22.2, and the audit then passed.
- A raw worktree secret scan initially flagged six strings in compiled `ed25519-dalek` metadata. `.gitleaks.toml` now excludes only generated Rust build directories; a source-focused worktree scan and full Git-history scan pass.
- The 100K benchmark is a synthetic single-author linear graph on one machine and does not test multi-author contention, SQLite persistence throughput, network behavior, or production capacity.
- The reference store detects mutation of present records and edge inconsistencies, but cannot detect deletion of a valid suffix or rollback to an older internally valid database without an externally protected expected head.
- The independent Python implementation is a conformance oracle, not a second production authority service.
- Historical key-frontier verification is implemented; production key custody, recovery, incident response, and trusted appender discovery remain intentionally outside the public profile.
- Existing V1 Python code remains a bounded archived reference and is not promoted to canonical V2 authority.

## Deferred Work

- Metagraph, bitemporal world-model state, epistemics, phenomenological projections, and materialization begin only in Wave 02 or later.
- General authority, HPL lifecycle, NEP placement, physical safety, DeROS, Edge, and learning remain predecessor-gated.
- External OM1/FABRIC acquisition remains Wave 08 work; no external source was copied or behaviorally reimplemented.

## Release Leakage Review

No source-authority document, private UOR/PLOG implementation, production key material, credential, real-user data, private prompt, policy corpus, routing/topology detail, anti-abuse mechanism, OEM material, or previously removed local-only path was added. Synthetic signing seeds are test fixtures and are never represented as operational keys.

## Gate

`PASS` for Wave 01 based on the recorded local evidence. Remote CI evidence is attached to the tracking issue after the commit is pushed. This pass authorizes only progression to Wave 02; it does not claim later-wave functionality.
