# pwm-event

`pwm-event` implements the signed causal event DAG and durable SQLite reference store for the [public provenance profile](../../spec/public-provenance-profile-v1.md).

It verifies payload and body CIDs, author and receipt signatures, schema bindings, parent closure, principal scope, genesis shape, per-key causal sequence, historical key frontiers, and deterministic replay. SQLite recovery re-verifies present records and fails closed on record mutation or edge mismatch. Detecting valid-suffix deletion or whole-database rollback requires an externally protected expected head outside this reference profile.

Run:

```bash
cargo test -p pwm-event
cargo run --release -p pwm-event --example dag_benchmark
```

This crate is not a world-model materializer, authority engine, safety kernel, or private production PLOG.
