# V1 Baseline Report

**Status:** `IMPLEMENTED` forensic evidence

## Identity

- Archive tag: `public-v1-archive`
- Commit: `363fe941b6c71a0235b8479a33ea7a7286e7dbe2`
- Branch at capture: `main`
- Remote: `https://github.com/Balnce-AI/personal-world-models.git`
- Tracked files: 97
- Git archive SHA-256: `38b71f7274d65dba9260042da779386012ec5e16c8f841a0479e376881b4a0e8`

The annotated tag and draft GitHub release identify the recoverable V1 public baseline. The release asset `public-v1-archive.tar` is the byte stream measured by the hash above.

## Environment

- Host platform: macOS Darwin
- Host Python: `3.14.5`
- Test environment: external virtual environment, outside the repository
- Runtime dependencies exercised: `cryptography`, `jsonschema`
- Test dependency exercised: `pytest`

V1 has no lockfile, dependency hashes, supported upper bounds, container, or reproducible environment declaration. This report therefore records an observed baseline, not a reproducible dependency closure.

## Commands And Results

The original interpreter lived in an external temporary virtual environment. The portable transcription below assumes `BASELINE_VENV` names an equivalent environment:

```bash
BASELINE_VENV=/path/to/pwm-baseline-venv
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  "$BASELINE_VENV/bin/python" \
  -m pytest -q -p no:cacheprovider
```

Result: `10 passed in 0.12s`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  "$BASELINE_VENV/bin/python" \
  -m pwm_hpl_ref.demo
```

Result: exit 0 and a JSON document containing a projection, Arranger artifact, learning candidate, departure receipt, and machine broadcast.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  "$BASELINE_VENV/bin/python" \
  benchmarks/hpl-context/run.py
```

Result:

```text
{'total_assertions': 3, 'disclosed_assertions': 2, 'disclosure_ratio': 0.6666666666666666}
```

```bash
git fsck --full --no-reflogs
git archive --format=tar 363fe941b6c71a0235b8479a33ea7a7286e7dbe2 | shasum -a 256
```

Result: no Git integrity errors and the archive hash recorded above.

## Coverage Boundary

An isolated extraction of `public-v1-archive` was measured with `coverage.py 7.16.0`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ARCHIVE_DIR/src" \
  python -m coverage run --source="$ARCHIVE_DIR/src/pwm_hpl_ref" \
  -m pytest -q -p no:cacheprovider "$ARCHIVE_DIR/tests"
python -m coverage report
```

Result: `10 passed`; 199 statements, 26 missed, 87% statement coverage. Coverage was measured after installing `coverage.py` into the external test environment; it is forensic evidence and not a V1 project dependency.

The ten tests cover basic repeated materialization, privacy exclusion, deny-overrides, signature tamper detection, bounded departure labeling, three narrow adapter behaviors, schema metaschema validity, and GitHub-compatible Markdown math delimiters.

They do not establish causal DAG validity, bitemporal correctness, persistence or crash recovery, generated-instance schema conformance, complete artifact verification, HPL lifecycle enforcement, independent conformance, recipient execution, R0 safety, Synthetic Life, DeROS, or production readiness.

## Known V1 Contract Defects

- `departure.make_receipt()` emits `receiptId`, which its public schema rejects.
- Demo assertions omit schema-required `recordTime`.
- PLOG payloads remain mutable and parent/DAG validity is not enforced.
- Materialization ordering is lexical chronological order, not validated topological replay.
- Arranger and broadcast verification check signatures without complete ID, expiry, recipient, replay, revocation, or payload binding enforcement.
- The benchmark is a fixed disclosure smoke metric without utility, baseline, threshold, repetitions, or uncertainty.

## Public User Evidence

At capture, GitHub exposed no issues, pull requests, milestones, tags before the archive tag, releases before the draft archive release, or package publication evidence. This is absence of repository-visible evidence, not proof that no external user exists.

## Baseline Conclusion

V1 is a small executable Python reference corpus with bounded research demonstrations. It is not the V2 architecture and must not be described as canonical UOR/PLOG, a complete sovereign world-model harness, an enforced HPL lifecycle, a safety kernel, or a production system.
