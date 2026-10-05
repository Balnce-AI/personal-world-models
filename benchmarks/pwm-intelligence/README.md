# PWM Intelligence Benchmark

**Status:** `EXPERIMENTAL`  
**Metric interpretation:** research diagnostics, not a person score or consciousness measure

Run the complete local control, including source, retrieval, structured, information-matched, metacognitive, and negative-control conditions:

```bash
pwm-research run \
  --persona experiments/data/personas/longitudinal-persona.json \
  --output experiments/results/fixture-control.json
```

The deterministic `fixture-control-v1` model establishes that loading, projection, privacy filtering, condition construction, scoring, and manifest generation work end to end. It is a plumbing control, not evidence that PWM improves a foundation model. Replace it through the `ReasoningModel` protocol to test an OpenAI-compatible or Ollama model under the same condition builder and rubric.

The result reports contextual correctness, privacy leaks, provenance coverage, and context bytes separately. It deliberately does not aggregate them into one intelligence or PWM score.

The harness now supports exact rendered-request matching for verified tokenizer adapters and explicit information-ledger matching for the `flat_information_matched` / `structured_information_matched` pair. Other conditions intentionally vary selection or derived information and are not causal representation comparisons. A publishable foundation-model experiment still requires a real model tokenizer, repeated runs, preregistered contrasts, model-specific decoding parameters, and uncertainty analysis.
