# Conformance Runner

`scripts/pwm_conformance.py` runs implementation adapters without depending on an implementation language or private infrastructure.

## Commands

```console
pwm-conformance verify --implementation rust-signed-semantic --profile PWM-MODEL-ECOLOGY-1
pwm-conformance verify --implementation python-signed-semantic --profile PWM-MODEL-ECOLOGY-1
pwm-conformance compare --implementations rust-signed-semantic python-signed-semantic --suite PWM-SIGNED-SEMANTICS-V1
pwm-conformance diff --expected expected.json --actual actual.json
```

The installed convenience command expects to run from a repository clone containing `conformance/` and `scripts/`. External implementations can invoke `scripts/pwm_conformance.py` directly with their own adapter manifest directory.

`verify --profile` accepts either a level ID or suite ID from `conformance/manifest.json`. A level runs all of its `requiredSuites`. `compare` requires one suite and at least two named implementations. The optional `--conformance-manifest` and `--implementations-dir` arguments support isolated test and downstream conformance catalogs.

Only fixtures with normative expected outcomes are scored. Semantic vectors carry those outcomes in each case. Evidence profiles can provide a separate expectation document with a `fixture` member, as Wave01 does. Corpora without per-case expected outcomes are not silently treated as passing cases.

## Adapter Manifest

Each JSON file in `conformance/implementations/` has this language-neutral shape:

```json
{
  "name": "example-zig",
  "version": "1.0.0",
  "language": "Zig",
  "command": ["./zig-out/bin/pwm-adapter", "--bundle", "{bundle}", "--profile", "{profile}", "--suite", "{suite}"],
  "profiles": ["pwm-json-semantics-v1"]
}
```

Commands are argv arrays and are never evaluated by a shell. Supported placeholders are `{bundle}`, `{profile}`, `{suite}`, `{python}`, and `{root}`. `{bundle}` is mandatory. The runner executes adapters from the repository root with a 60-second timeout.

## Output Contract

An adapter writes exactly one canonical JSON document followed by one newline to stdout. Canonical JSON here means UTF-8, lexicographically sorted object keys, compact separators, no NaN or infinity, and no insignificant whitespace. Diagnostics belong on stderr.

```json
{"cases":[{"actual":{"decision":"ACCEPT","query":{"modelIds":["model-a"]}},"events":[{"eventId":"evt-1","status":"applied"}],"id":"case-1"}],"contract":"pwm-conformance-result-v1","profile":"pwm-json-semantics-v1","suite":"PWM-MODEL-ECOLOGY-V1"}
```

The envelope fields are:

- `contract`: exactly `pwm-conformance-result-v1`.
- `profile` and `suite`: exactly the values supplied to the adapter command.
- `cases`: one object per vector case, each with unique string `id` and object `actual`.
- `events`: optional ordered event trace used to identify the first divergent event.

Expected `invariants` are explanatory assertions and are not copied into adapter output. The runner compares observable expected fields. Diagnostics identify the first divergent event and differences in materialized state, query, privacy, contradictions, topology, HPL/projection, error code, and canonical bytes, followed by any remaining result difference.

Adding a TypeScript, Swift, or Zig implementation only requires an executable honoring this contract and a manifest. Suites and vectors do not change.
