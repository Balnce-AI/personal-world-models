# Contradiction Profile

**Truth plane:** `EXPERIMENTAL`

Conflict types are `ASSERTION_CONFLICT`, `MODEL_CONFLICT`, `UNCERTAINTY`, `TEMPORAL_CHANGE`, `PERSPECTIVE_DISAGREEMENT`, and `GENUINE_CONTRADICTION`. Resolution statuses are `OPEN`, `EXPLAINED`, `SUPERSEDED`, `RESOLVED`, `IRREDUCIBLE`, and `PERSPECTIVE_DEPENDENT`.

The deterministic detector recognizes only assertions with identical subject, predicate, and valid-time key and incompatible values. Broader semantic or model-assisted detections are proposals and MUST NOT auto-accept. Acceptance is a separate event. Every resolution appends a typed resolution record containing status, explanation, resolver, time, and provenance; replay preserves the original conflict and all prior resolutions.

Queries and topography consume accepted contradiction records only. Candidate records remain inspectable in internal materialized state but do not influence user-facing contradiction projections or metrics.
