# Self-Model Profile

**Truth plane:** `EXPERIMENTAL`  
**Evidence status:** `EXPERIMENTAL_REAL`

A PWM model is a derived, versioned representation with evidence, perspective, uncertainty, lifecycle, and action or prediction relevance. It is not an assertion and cannot grant authority.

Kinds are `SELF`, `OTHER`, `RELATIONSHIP`, `WORLD`, `META`, and `POSSIBLE_WORLD`. Families come from the open registry and carry independent status. `WORLD` represents modeled external state rather than forcing places, institutions, machines, or environments into a self/other category. Accepted records MUST retain proposal and evidence provenance. Proposals MUST NOT materialize as accepted state. Updates MUST identify lineage and preserve superseded records. Disputed records MUST remain available only when explicitly queried. Revoked and superseded records MUST be excluded from current projections.

Possible-world records are temporary hypotheses. They MUST NOT mutate actual-world state without a separate governed acceptance event.

Each registered family declares machine-readable ontology constraints: allowed model kinds, subject cardinality, perspective rules, required state fields, and any meta-target or possible-world parent requirement. The same registry checks run before proposal emission and during replay. Independently of family constraints, relationship models require at least two distinct subjects, `SELF` perspectives are subjects, `OTHER` perspectives are outside the modeled subjects, and every `POSSIBLE_WORLD` model names `parentWorldId`.

Contradictions are governed records rather than a destructive merge rule. Deterministic equality conflicts may be proposed from assertions sharing subject, predicate, and valid time but carrying incompatible values. Semantic and model-assisted detections remain proposals until explicitly accepted. Resolution appends a typed record and never erases the original conflict or earlier resolutions.

Public confidence uses integer parts-per-million because canonical V2 signed records forbid floating point. The Python semantic layer is not itself the V2 event profile; a verified replay adapter remains required.
