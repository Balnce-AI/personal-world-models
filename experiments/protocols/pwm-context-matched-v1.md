# PWM Context-Matched Experiment Protocol v1

**Status:** `PROVISIONAL` protocol; no foundation-model result claimed

## Primary Hypothesis

Given the same model checkpoint, decoding configuration, task, persona snapshot, evaluator, repetition policy, information units, privacy ceiling, and final rendered token budget, structured PWM context improves one or more preregistered situated-reasoning lanes relative to flat and retrieval representations.

## Primary Falsifier

If token- and information-matched flat or retrieval conditions perform equivalently to intact PWM across temporal continuity, contradiction handling, relationship-state reasoning, calibration, privacy minimization, prediction, and planning, while topology/family/provenance ablations do not reduce performance, the tested structural claims are weakened or falsified.

## Required Arms

1. Stateless.
2. Full transcript.
3. Flat normalized source facts.
4. Retrieval over raw events.
5. Retrieval over normalized facts.
6. Structured PWM assertions.
7. Flat source plus derived facts.
8. Structured self/other/relationship model ecology.
9. Structured ecology plus meta-models.
10. Topology-shuffled control.
11. Provenance-redacted control.
12. Stale, confidence-corrupt, random, and adversarial controls.

## Matching Rules

Representation contrasts MUST have equal `InformationLedger.signature` values. Exact-token claims MUST use a verified tokenizer over the complete rendered request and equal final token counts. Natural and padding token counts are reported separately. Opaque remote tokenizers are marked unverified unless provider usage agrees within a preregistered tolerance.

## Analysis

Report task correctness, temporal consistency, contradiction handling, declared literal leakage-canary hits, provenance precision/recall, probabilistic calibration, constraint violations, prompt/completion tokens, latency, failures, and paired effect sizes separately. Canary hits are not semantic privacy-leakage estimates; a separate adversarial evaluator is required for that claim. Use held-out scenarios, multiple models, randomized condition order, repeated runs, and paired confidence intervals. Negative, null, and adverse outcomes remain publishable.
