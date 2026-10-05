"""Experimental, dependency-injected Python facade over public PWM boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .adapters import (
    AuthorizationRequiredError,
    BoundedAdapter,
    CapabilityDescriptor,
    EventDraft,
    LifecycleState,
    StorageAdapter,
)
from .model_query import ModelQuery, ModelQueryAuthorization, execute_query
from .model_registry import ModelRegistry, default_registry
from .plog import Event, PLog
from .possible_worlds import PossibleWorld
from .pwm import Materializer, PWMState
from .self_models import ModelLifecycle
from .self_models import ModelRecord


AuthorizationHook = Callable[[str, Any], Any]
QueryHook = Callable[[PWMState, ModelQuery, ModelQueryAuthorization], Mapping[str, Any]]
ProjectionHook = Callable[[PWMState, Any, Any], Mapping[str, Any]]
ResearchHook = Callable[..., Mapping[str, Any]]


@dataclass(frozen=True)
class SDKDependencies:
    storage: StorageAdapter
    authorize: AuthorizationHook
    materializer: Materializer
    registry: ModelRegistry
    query_hook: QueryHook = execute_query
    projection_hook: ProjectionHook | None = None
    research_hook: ResearchHook | None = None


class PersonalWorldModel:
    """Boundary-visible facade; it does not mint authority or production claims."""

    def __init__(self, dependencies: SDKDependencies):
        self._deps = dependencies
        self._lifecycle = ModelLifecycle(dependencies.registry)
        self._started = False

    @classmethod
    def experimental(cls, storage: StorageAdapter, authorize: AuthorizationHook, **hooks: Any) -> "PersonalWorldModel":
        return cls(SDKDependencies(storage, authorize, Materializer(), default_registry(), **hooks))

    @classmethod
    def open(
        cls,
        *,
        authorize: AuthorizationHook,
        storage: StorageAdapter | None = None,
        **hooks: Any,
    ) -> "PersonalWorldModel":
        """Open the experimental SDK with explicit authority and replaceable storage."""
        from .adapters import InMemoryStorageAdapter

        return cls.experimental(storage or InMemoryStorageAdapter(), authorize, **hooks)

    def start(self) -> None:
        if self._started:
            return
        self._deps.storage.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._deps.storage.stop()
        self._started = False

    def __enter__(self) -> "PersonalWorldModel":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def append_event(self, draft: EventDraft) -> Event:
        if self._deps.authorize("append_event", draft) is None:
            raise AuthorizationRequiredError("append_event")
        return self._deps.storage.append_event(draft)

    def _event_log(self, at_time: str | None = None) -> PLog:
        log = PLog()
        events = self._deps.storage.ordered_events(at_time)
        log.events = {event.event_id: event for event in events}
        parent_ids = {parent for event in events for parent in event.parents}
        log.heads = set(log.events) - parent_ids
        return log

    def materialize(self, at_time: str | None = None) -> PWMState:
        return self._deps.materializer.materialize(self._event_log(at_time))

    @property
    def model_lifecycle(self) -> ModelLifecycle:
        """Lifecycle emits governed events; callers still append through the public log."""
        return self._lifecycle

    def event_log_snapshot(self, at_time: str | None = None) -> PLog:
        """Return an isolated snapshot for existing lifecycle APIs, never storage internals."""
        return self._event_log(at_time)

    def _append_generated(self, log: PLog, known_ids: set[str]) -> tuple[Event, ...]:
        generated = tuple(event for event in log.ordered() if event.event_id not in known_ids)
        for event in generated:
            persisted = self._deps.storage.append_event(
                EventDraft(event.event_type, event.payload, event.actor, event.record_time, event.parents)
            )
            if persisted.event_id != event.event_id:
                raise RuntimeError("storage changed a generated lifecycle event")
        return generated

    def propose_model(self, model: ModelRecord, actor: str) -> Event:
        if self._deps.authorize("propose_model", {"model": model, "actor": actor}) is None:
            raise AuthorizationRequiredError("propose_model")
        log = self._event_log()
        known_ids = set(log.events)
        proposed = self._lifecycle.propose(log, model, actor)
        self._append_generated(log, known_ids)
        return proposed

    def accept_model(self, model: ModelRecord, actor: str, proposal_event_id: str) -> Event:
        if self._deps.authorize(
            "accept_model", {"model": model, "actor": actor, "proposalEventId": proposal_event_id}
        ) is None:
            raise AuthorizationRequiredError("accept_model")
        log = self._event_log()
        known_ids = set(log.events)
        try:
            proposal = log.events[proposal_event_id]
        except KeyError as exc:
            raise ValueError(f"unknown proposal event: {proposal_event_id}") from exc
        accepted = self._lifecycle.accept(log, model, actor, proposal)
        self._append_generated(log, known_ids)
        return accepted

    def transition_model(self, model_id: str, status: str, actor: str, reason: str) -> Event:
        if self._deps.authorize(
            "transition_model", {"modelId": model_id, "status": status, "actor": actor, "reason": reason}
        ) is None:
            raise AuthorizationRequiredError("transition_model")
        log = self._event_log()
        known_ids = set(log.events)
        transition = self._lifecycle.transition(log, model_id, status, actor, reason)
        self._append_generated(log, known_ids)
        return transition

    def query(self, query: ModelQuery) -> Mapping[str, Any]:
        authorization = self._deps.authorize("query", query)
        if not isinstance(authorization, ModelQueryAuthorization):
            raise AuthorizationRequiredError("query")
        return self._deps.query_hook(self.materialize(), query, authorization)

    def project(self, request: Any) -> Mapping[str, Any]:
        if self._deps.projection_hook is None:
            raise NotImplementedError("no projection hook was injected")
        authorization = self._deps.authorize("project", request)
        if authorization is None:
            raise AuthorizationRequiredError("project")
        return self._deps.projection_hook(self.materialize(), request, authorization)

    def possible_world(
        self,
        label: str,
        assumptions: tuple[dict[str, Any], ...],
        provenance_refs: tuple[str, ...],
        *,
        base_time: str | None = None,
    ) -> tuple[PossibleWorld, PWMState]:
        state = self.materialize()
        world = PossibleWorld.create(label, assumptions, provenance_refs).bind(
            state, base_time or datetime.now(timezone.utc).isoformat()
        )
        return world, world.branch(state)

    def research(self, *args: Any, **kwargs: Any) -> Mapping[str, Any]:
        if self._deps.research_hook is None:
            raise NotImplementedError("no research hook was injected")
        authorization = self._deps.authorize("research", {"args": args, "kwargs": kwargs})
        if authorization is None:
            raise AuthorizationRequiredError("research")
        return self._deps.research_hook(*args, authorization=authorization, **kwargs)

    def capabilities(self) -> tuple[CapabilityDescriptor, ...]:
        descriptors = list(self._deps.storage.capabilities())
        for hook, capability_id in (
            (self._deps.projection_hook, "pwm.sdk.projection"),
            (self._deps.research_hook, "pwm.sdk.research"),
        ):
            if hook is not None:
                descriptors.append(CapabilityDescriptor(capability_id, "1.0-experimental", (capability_id,), ("invoke",)))
        return tuple(descriptors)

    def adapter_states(self) -> Mapping[str, LifecycleState]:
        adapters = [self._deps.storage]
        return {descriptor.capability_id: adapter.lifecycle_state for adapter in adapters for descriptor in adapter.capabilities()}


def discover_capabilities(*adapters: BoundedAdapter) -> tuple[CapabilityDescriptor, ...]:
    """Discover declarations only; callers must separately authorize every operation."""
    return tuple(descriptor for adapter in adapters for descriptor in adapter.capabilities())
