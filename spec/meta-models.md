# Meta-Model Profile

**Truth plane:** `EXPERIMENTAL`

A meta-model describes the quality, limits, dependency, reliability, freshness, contradiction state, capability estimate, or authority uncertainty of another model or reasoning process. It MUST identify its target in state or topology and retain its own evidence and uncertainty.

A meta-model MUST NOT silently rewrite its target, convert a capability estimate into permission, or present evaluator-dependent accuracy as universal. Calibration is linked as a separate derived record so historical predictions remain unchanged.

Families that require explicit meta targets declare that constraint in the registry. Their `state.targetModelId` MUST resolve to an accepted model and MUST also occur in `dependencyRefs`; helper construction and replay enforce the same rule.

Inspectable projection means exposing sufficient evidence, uncertainty, authority, and dependency references for accountable action. It does not require disclosure of hidden chain-of-thought or claim complete symbolic access to neural computation.
