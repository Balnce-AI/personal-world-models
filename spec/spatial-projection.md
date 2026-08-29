---
status: PROPOSED
version: 0.1.0
---
# Spatial Projection Profile

A spatial projection is not a copy of a person's global map. It is a purpose-bounded view of geometry, topology, semantics, uncertainty and permissions.

\[
S = \langle V,E,\Phi,\Gamma,\Theta,\Sigma \rangle
\]

- `V`: spatial entities;
- `E`: spatial/topological relations;
- `Φ`: geometry and frames;
- `Γ`: policy/access zones;
- `Θ`: temporal state;
- `Σ`: uncertainty and source provenance.

A spatial minimizer SHOULD support:

- geometry clipping;
- topology reduction;
- semantic redaction;
- identity pseudonymization;
- purpose-specific zones;
- TTL/session binding;
- uncertainty propagation.

Example: a delivery robot may receive a path from entry to kitchen and a placement surface while never receiving the bedroom graph, medication semantics, or a global exportable home map.
