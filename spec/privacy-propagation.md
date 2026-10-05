# Privacy Propagation Profile

**Truth plane:** `EXPERIMENTAL`

Privacy classes form the ordered lattice `PUBLIC < LOW < PERSONAL < SENSITIVE < HIGHLY_SENSITIVE`. Unknown classes fail closed. A model's effective class is retained in its materialized record and is normally the join of its declared class, evidence events, model dependencies, model edges present during derivation, policy floors, and derivation references. Edge effective privacy similarly joins its declaration, endpoints, and evidence.

An approved `REDACTION` or `PROOF` boundary may release a lower-class result only when it names an existing policy and covers every source, dependency, and derivation reference. Its input class must cover the source join. Unapproved or incomplete boundaries do not declassify. Query authorization is checked against effective rather than declared privacy.

A declassified projection MUST NOT expose raw provenance, dependency references, or derivation references. It exposes only state keys listed in the approved boundary's `releasedFields` and a minimized boundary description. This reference profile treats the `approved` flag plus a materialized policy reference as fixture-level authority; production approval requires the platform's signed policy and PLOG verification path.

Possible worlds bind a parent world, base-state content identifier, base time, declared privacy, and effective privacy. A branch is a deep copy with a distinct world identifier. Queries are bound to exactly one materialized world, so an actual-world query cannot inspect a hypothetical branch.
