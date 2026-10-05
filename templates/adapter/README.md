# Adapter template

Status: `TEMPLATE`.

Copy `adapter.py` and complete the checklist. Keep an organization namespace, implement only needed public protocols, pin semantics and dependencies, declare lifecycle/resource bounds, reject unknown semantics, require authorization at effect boundaries, and add synthetic tests for denial, replay, malformed input and shutdown.

Document data custody, network destinations, credential handling, telemetry, retention, deletion limits, supply-chain lockfiles and supported footprint profiles. Capability discovery never grants authority.
