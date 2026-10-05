# Model Topology Profile

**Truth plane:** `EXPERIMENTAL`

Model edges are first-class records with source, target, relation type, confidence, privacy, provenance, and schema version. Reference edge types are `DEPENDS_ON`, `CONSTRAINED_BY`, `INFORMED_BY`, `UNCERTAINTY_SOURCE`, and `SUPERSEDES`.

Both endpoints MUST exist in the queried model closure. `DEPENDS_ON` MUST be acyclic in the reference profile. Other edges may form cycles where the relation semantics permit them. Query projections MUST remove edges whose endpoints are withheld and MUST enforce edge privacy independently.

Edge effective privacy is the join of its declaration, endpoint effective privacy, and available evidence privacy. Edge privacy does not by itself relabel either endpoint: it protects disclosure of the relationship. Model derivation through an edge incorporates that edge when computing the derived model's effective privacy.

Topography is a vector of diagnostics, never a universal score. Current coverage and connectivity calculations are experimental fixture heuristics.
Contradiction load includes only accepted, active contradiction records associated with selected models; unreviewed semantic proposals do not affect it.
