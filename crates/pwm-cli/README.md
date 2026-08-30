# pwm-cli

`pwm-cli` exposes public provenance conformance operations:

```bash
cargo run -q -p pwm-cli -- vectors emit --output /tmp/wave01.json
cargo run -q -p pwm-cli -- event verify --bundle conformance/vectors/wave01-valid.json
cargo run -q -p pwm-cli -- event replay --bundle conformance/vectors/wave01-valid.json
```

The CLI verifies public test bundles. It is not an operational key manager or production append service.
