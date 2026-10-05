# Foundation-model adapters

**Status:** `EXPERIMENTAL`

The executable adapters live in `pwm_hpl_ref.foundation_models` so they are included in the Python package. `ReasoningModel` accepts a controlled `ModelProjection`; `LocalCallableModel`, `OpenAICompatibleModel`, and `OllamaModel` provide local and HTTP integration paths without provider SDK lock-in.

Inference responses may contain model candidates, but adapters never receive a canonical write handle and never reconcile candidates into PWM state. Callers must authorize the projection through their HPL/authority boundary, then use the reviewed `ModelLifecycle` proposal and acceptance path for returned candidates. The V1 reference actor string is not production authentication.
