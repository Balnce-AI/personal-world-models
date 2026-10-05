# Foundation-Model Augmentation

**Status:** `EXPERIMENTAL_REAL`

`ReasoningModel` receives a task and a bounded `ModelProjection`. Implementations include a local callable adapter and OpenAI-compatible HTTP/Ollama clients. Credentials remain external. The model never receives a canonical write handle; returned model candidates require `ModelLifecycle` proposal and reviewed acceptance. `ModelQuery` enforces declared subject, status, temporal, confidence, privacy, provenance, and edge bounds, but the experimental query API is not a substitute for a production HPL authority decision; callers must authorize recipient and purpose before external disclosure.

The benchmark distinguishes three experiment classes rather than treating every context change as structural evidence:

- Representation controls compare normalized source facts with structured assertions, or the explicit `flat_information_matched` and `structured_information_matched` pair. Raw retrieval and rich model-ecology conditions expose additional metadata and are not treated as information-equivalent merely because their ledgers share source units.
- Selection controls change which source units are retrieved.
- Derived-information controls introduce model or meta-model claims beyond normalized source facts.

Negative controls alter graph structure, freshness, provenance, confidence, or contradictions. Every information unit records role, value, value hash, source references, derivation status, and privacy class. Its semantic signature commits to the complete unit record. Only pairs rendered solely from the same complete ledger may claim information equivalence.

The harness renders the complete provider request before counting. The fixture adapter uses the dependency-free `deterministic-byte-v1` tokenizer and declared one-byte padding, so matched cells record natural, padding, target, and final counts and verify exact equality. Remote provider tokenizers are opaque by default and are explicitly recorded as unverified; byte counts or local estimates are never presented as exact provider token counts.

Local Ollama example:

```bash
pwm-research run --model ollama:llama3.2 --persona experiments/data/personas/longitudinal-persona.json --output experiments/results/ollama-llama3.2.json
```

OpenAI-compatible example:

```bash
OPENAI_API_KEY=... pwm-research run --model openai:model-name --base-url https://provider.example/v1 --persona experiments/data/personas/longitudinal-persona.json --output experiments/results/model-name.json
```

Run the same condition list, seed, and repetition count for comparisons. For example, add `--seed 17 --repetitions 5`. Exact token equality removes one confound but does not establish structural causality: matched information signatures, held-out tasks, repeated runs, and the declared expected-control direction are all required evidence.
