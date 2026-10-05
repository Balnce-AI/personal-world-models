# Functional Self-Models

**Status:** `EXPERIMENTAL_REAL`

`ModelRecord` distinguishes an evidence-backed, revisable model from a raw assertion. Models have kind, family, perspective, subjects, bitemporal fields, fixed-point confidence, uncertainty, provenance, dependencies, privacy, and lineage. `ModelLifecycle.propose` creates a candidate only; `accept` is an explicit reviewed transition by the modeled perspective in this bounded reference. Updates pass through a new proposal and supersede rather than erase history, and disputes remain queryable.

The current Python reducer is an experimental semantic layer over the V1 reference log. The canonical V2 Rust profile remains the required verified event boundary for production-like experiments. The Python log is not represented as the private Balnce PLOG or as V2 authority.

Falsifier: if an unaccepted model proposal appears in `PWMState.models`, or an accepted model cannot be traced to evidence and its proposal event, the implemented lifecycle claim fails.
