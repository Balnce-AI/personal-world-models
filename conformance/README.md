# Conformance Assets

This directory provides language-neutral evidence inputs. `manifest.json` identifies suites, required features, fixture formats, and conformance levels. A level's `features` are the requirements introduced at that stage; its cumulative `requiredSuites` carry requirements from preceding stages. Files under `schemas/` validate suite and semantic-vector envelopes. Files under `vectors/` are data, not executable test programs.

## Fixture families

- `wave01-*.json` are the unchanged, authoritative fixtures for `pwm-public-provenance-v1`. Their canonical CBOR, CID, signature, receipt, and key-state semantics are governed by the Wave01 profile.
- `model-ecology-*.json` and `hpl-*.json` use `semantic-vector-v1` envelopes and the `pwm-json-semantics-v1` profile. Event objects are an abstract JSON test notation, not canonical signed records.

`spec/wave01-bundle-profile.md` defines the JSON envelope, key-status frontier construction, processing order, and replay tie-break needed in addition to the canonical record profile. `expectations/wave01-valid.json` publishes replay output without requiring implementers to derive expected results from Rust or Python source.

`expectations/wave01-negative-operations.json` is a non-normative backlog of mutation recipes. It is intentionally excluded from the conformance manifest because those recipes do not yet contain complete mutated bundles or normative validation precedence.

For an `ACCEPT` case, an implementation MUST accept all input events and produce the stated observable outcomes. For a `REJECT` case, it MUST reject the operation with the specified `error.code` before committing the invalid transition. Comparisons ignore object-member ordering but not array ordering unless an invariant states otherwise.

An evidence report SHOULD record implementation version, suite ID and version, fixture digest, adapter version, pass/fail per case, and execution environment. The repository currently makes no full-conformance claim; an empty `claims` array in `manifest.json` is deliberate.
