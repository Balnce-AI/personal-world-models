# HPL Benchmarks

The benchmark program turns architectural claims into falsifiable tests.

- **HPL-CONTEXT:** task success versus disclosed personal information.
- **HPL-AUTH:** authorization correctness under conflicting principals.
- **HPL-SPATIAL:** task completion with excluded zones/semantics.
- **HPL-RESIDUE:** lifecycle/departure evidence quality.
- **HPL-LEAKAGE:** extraction/inversion risk from behavioral/model artifacts.
- **HPL-DRIFT:** safe rejection/regeneration across model/runtime/firmware changes.
- **HPL-HANDOFF:** bounded session movement across local/edge/vehicle/robot compute.
- **HPL-OFFLINE:** expiry, replay and safe degradation under network loss.

Every benchmark must state baseline, metric, pass/fail condition, and limitations.

## Wave 01 Provenance DAG

The Wave 01 benchmark measures end-to-end in-memory validation and deterministic replay for synthetic single-author linear DAGs at 1K, 10K, and 100K events. It includes canonical encoding, typed CID construction, Ed25519 author signing and verification, append-receipt signing and verification, and replay ordering.

Run:

```bash
cargo run --release -p pwm-event --example dag_benchmark
```

The checked-in result is [`results/wave01-dag.json`](results/wave01-dag.json). It is descriptive evidence from one environment, not a latency service-level objective, production capacity claim, multi-author contention result, or comparison against an external baseline.
