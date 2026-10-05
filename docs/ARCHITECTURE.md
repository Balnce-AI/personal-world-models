# Public architecture map

Status: `PROPOSED`, except linked executable reference modules marked `REFERENCE_IMPLEMENTATION`.

## Boundaries

| Boundary | Owns | Does not own |
|---|---|---|
| Normative (`spec/`, `schemas/`, `rfcs/`) | Public records, invariants, validation and protocol proposals | Production deployment or private Balnce internals |
| Reference (`src/pwm_hpl_ref/`, `conformance/`) | Executable examples and deterministic checks | Safety certification, production authority or durable custody |
| Ecosystem (`adapters/`, `examples/`, `templates/`) | External mappings and independently named extensions | Canonical ontology, implicit trust or authorization |
| Research (`research/`, `experiments/`, `benchmarks/`) | Falsifiable questions, fixtures and measurements | Product claims or normative semantics |

## Layer map

```text
Evidence / devices / apps / simulators
        | provenance-bearing references and event drafts
role-specific adapters (untrusted by default)
        | public EventSink
event DAG ------------------------------------ sync/federation boundary
        | deterministic replay                 (design-only profile)
PWM materializer
        |
+------------------------------------------------------------------+
| World-model ecology                                               |
| entities + relations + assertions                                 |
| SELF | OTHER | RELATIONSHIP | WORLD | META | POSSIBLE_WORLD      |
| model topology | contradictions | predictions | calibration       |
+------------------------------------------------------------------+
        |                         ^
        |                         | observed outcomes / calibration
policy + authority + privacy-taint propagation
        |
authorized model query
        |
HPL capability negotiation -> bounded, expiring projection
        |
+------------------------------------------------------------------+
| model adapters | apps | agents | robots | vehicles | homes       |
| storefronts | workplaces | industrial and accessibility systems  |
+------------------------------------------------------------------+
        |
local safety / recipient lifecycle / departure evidence

Research harness: scenario corpus -> information ledger -> matched
conditions -> model adapter -> generated manifest and coverage report

Extension registry: namespaced families, schemas, adapters, profiles,
simulators and benchmark suites; extensions do not redefine core IDs.
```

The event DAG is the reconstruction source; `PWMState` is disposable materialization. A possible world is an isolated hypothetical branch. A projection is a bounded disclosure artifact. None is interchangeable with authority.

Solid behavior described by public schemas and conformance vectors is portable across languages. Python modules are reference implementations; model providers, storage, transports, devices, safety kernels, and federation are replaceable ecosystem components. `PWMState` is not a wire protocol.

## Extension rules

- Use the narrowest role protocol in `pwm_hpl_ref.adapters`; there is no universal adapter.
- Treat `CapabilityDescriptor` as descriptive metadata only.
- Start and stop adapters explicitly. A stopped adapter cannot restart in the experimental profile.
- Reject unknown semantics. Extension fields cannot silently redefine base meanings.
- Keep media bytes out of events. Events contain integrity-checked, provenance-bearing references.
- Route all durable observations through `EventSink`; never mutate a materialized state.
- Require separate authorization for query, projection, tool invocation, transport, promotion and actuation.

See `SDK.md`, `ADAPTERS.md`, and the public decisions in `docs/adr/`.
