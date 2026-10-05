# ADR 0011: Foundation-Model Interface Is Provider-Neutral

**Status:** `PROPOSED`

## Context
PWM continuity must not depend on one hosted model or chat API.

## Decision
Research and applications depend on the `ReasoningModel` behavior and a bounded `ModelProjection`. OpenAI-compatible and Ollama clients are adapters, not the cognitive interface definition.

## Alternatives
Provider SDKs as the core interface were rejected because they impede local, multimodal, specialized, and future model runtimes.

## Consequences
Provider-specific usage and tokenizer behavior remain adapter metadata. Model swapping does not migrate PWM semantics.
