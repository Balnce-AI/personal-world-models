# Contributing

This repository separates normative specifications, executable reference code, ecosystem extensions and open research. A contribution must say which boundary it changes.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,research]'
pytest -q
cargo test --workspace
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
```

Run signed semantic interoperability checks with:

```bash
pwm-conformance verify --implementation rust-signed-semantic --profile PWM-MODEL-ECOLOGY-1
pwm-conformance verify --implementation python-signed-semantic --profile PWM-MODEL-ECOLOGY-1
pwm-conformance compare --implementations rust-signed-semantic python-signed-semantic --suite PWM-SIGNED-SEMANTICS-V1
```

## Before proposing code

1. Identify the invariant, falsifiable claim or benchmark being improved.
2. Declare `IMPLEMENTED`, `REFERENCE_IMPLEMENTATION`, `EXPERIMENTAL`, `PROPOSED`, `RESEARCH`, or `HYPOTHESIS` using `STATUS.md`.
3. Check `spec/`, `docs/ARCHITECTURE.md` and `docs/adr/` before adding a primitive.
4. Prefer the narrowest role-specific protocol. Do not introduce a universal adapter.
5. State external dependencies, custody, privacy segments and supported footprint profiles.
6. Add tests, conformance evidence or an explicit proof obligation and negative control.
7. Use synthetic/public fixtures only. Never commit personal world-model data, credentials or provider responses containing private context.
8. For external standards, pin the primary source/version and fail unknown semantics closed. Structural mapping is not normative compliance.
9. During the current architectural freeze, prefer bug fixes, conformance corrections, documentation, external implementation support, benchmarks and scoped security work. A major new subsystem requires evidence and explicit architectural review.

## Pull requests

Include purpose and scope, boundary/status, changed invariants, test commands/results, security/privacy impact, compatibility/migration, rollback and limitations. Adapter changes must test lifecycle, malformed input, unknown semantics, missing authorization and dependency failure. Benchmark changes must use `templates/benchmark/` and preserve reproducibility metadata.

Run focused tests first, then the relevant broader suite. Formatting or generated-file changes must remain scoped; do not update unrelated baselines.

## Public ADR process

Use an ADR when a change creates or merges a primitive, alters normative semantics, changes trust/authority boundaries, adds a persistence or federation protocol, changes privacy/identity/cryptography, or makes a compatibility promise. Copy `templates/adr/ADR-TEMPLATE.md` to `docs/adr/NNNN-short-title.md`.

An ADR starts `PROPOSED`. Review must cover alternatives, threat-model delta, migration/rollback, evidence and unresolved questions. Maintainers mark it `ACCEPTED`; code landing alone does not accept an ADR, and architectural acceptance does not authorize a production implementation. Reversals use a new ADR that names the superseded decision; history is not rewritten.

Security-sensitive reports follow `SECURITY.md`, not public issues. See `spec/`, `STATUS.md`, `PUBLIC_RELEASE_PLAN.md`, `docs/EXTENSIONS.md` and `docs/adr/README.md`.
