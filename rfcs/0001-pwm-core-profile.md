# RFC 0001 — Minimum Personal World Model public profile

**Status:** PROPOSED

Question: what is the smallest schema that allows independent implementations to exchange evidence-bearing personal world state without forcing one ontology or storage engine?

The proposed core is Entity + n-ary Relation + temporally qualified Assertion + ProvenanceReference + Policy/Projection references, with extension profiles for spatial, authority, intent and domain-specific semantics.

Success criterion: two independent implementations can materialize equivalent scoped views from the same fixture while retaining epistemic status and provenance links.
