# Experimental Python SDK

Status: `EXPERIMENTAL`. The `pwm` package is the developer-facing facade; lower-level reference modules remain available from `pwm_hpl_ref`.

## Fifteen-minute path

```python
from pwm import EventDraft, InMemoryStorageAdapter, PersonalWorldModel

def authorize(operation, request):
    if operation == "append_event":
        return {"authorizationRef": "local-example-write"}
    return None  # every unlisted operation remains denied

with PersonalWorldModel.open(storage=InMemoryStorageAdapter(), authorize=authorize) as pwm:
    pwm.append_event(EventDraft("entity.put", {"id": "did:example:alice"}, "did:example:alice"))
    state = pwm.materialize()
```

The complete A-G path is in `examples/quickstart/`.

## Facade boundaries

| API | Boundary |
|---|---|
| `append_event(EventDraft)` | Explicit provenance-log write through injected storage |
| `materialize(at_time)` | New disposable state reconstructed from an event snapshot |
| `model_lifecycle` | Existing low-level proposal/review/accept/revoke rules |
| `propose_model`, `accept_model`, `transition_model` | Run those rules over an isolated snapshot and append resulting events |
| `query(ModelQuery)` | Requires an injected `ModelQueryAuthorization` |
| `project(request)` | Requires both authorization and an injected projection hook |
| `possible_world(...)` | Returns an isolated hypothetical branch |
| `research(...)` | Requires authorization and an injected research hook |
| `capabilities()` | Discovery only; grants no permission |

`SDKDependencies` makes storage, materialization, registry, authorization, query, projection and research choices visible. The facade does not select providers, mint authorization, claim production persistence or expose storage internals as canonical state.

`append_event`, `propose_model`, `accept_model`, and `transition_model` all require a non-null operation-specific result from the injected authorization hook. The experimental hook result is an integration boundary, not cryptographic authority; production implementations must bind it to authenticated principals and signed provenance.

## Lifecycle and errors

Call `start()`/`stop()` or use a context manager. Adapter failures expose an `ErrorCode` and `retryable`; unknown semantics, missing authorization and lifecycle violations are non-retryable and fail closed. Only `TRANSIENT_FAILURE` should normally be retried, under caller policy.
