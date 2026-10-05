# pwm-semantic

`pwm-semantic` is the independent Rust reducer for the provisional `pwm-signed-semantics-v1` profile.

It consumes records exposed by `pwm-event::MemoryDag::verified_replay()`. Cryptographic verification, key-frontier checks, receipt validation, and causal replay remain the responsibility of `pwm-event`; this crate handles authenticated principal grants and semantic reduction only.

```bash
cargo run -q -p pwm-semantic -- identify
cargo run -q -p pwm-semantic -- evaluate --bundle conformance/sources/signed-semantic-comprehensive.json
```

The crate is a public reference implementation, not a production authority engine or private PLOG implementation.
