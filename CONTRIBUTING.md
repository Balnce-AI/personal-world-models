# Contributing

This repository is deliberately split between implemented reference code and open research.

Before proposing code:

1. Identify the invariant or benchmark you are trying to improve.
2. State whether the contribution is `IMPLEMENTED`, `REFERENCE_IMPLEMENTATION`, `EXPERIMENTAL`, `PROPOSED`, `RESEARCH`, or `HYPOTHESIS`.
3. Do not introduce a new top-level primitive when an existing schema/profile can be extended.
4. Add tests or a proof obligation.
5. For security, physical actuation, identity, or cryptography changes, include a threat-model delta.
6. For external standards, pin the source/version and avoid claiming normative compliance without conformance evidence.

See `architecture/adrs/`, `STATUS.md`, and `PUBLIC_RELEASE_PLAN.md`.
