# Metacognition

**Status:** `EXPERIMENTAL_REAL`

Meta-models are ordinary provenance-bearing `ModelRecord` objects with `modelKind=META`. They describe limits such as staleness, source reliability, prediction accuracy, capability uncertainty, contradiction awareness, or policy uncertainty without mutating their target model.

The flagship fixture includes a prediction-reliability meta-model derived from an observed failed prediction. Benchmark conditions can withhold meta-models while holding the base state constant. This supports causal tests of utility; it does not establish introspective consciousness.
