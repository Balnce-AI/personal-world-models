"""Experimental public extension contracts for the PWM reference implementation.

Capabilities describe what an adapter can attempt.  They never convey authority.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from .plog import Event, PLog


class ErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN_SEMANTICS = "UNKNOWN_SEMANTICS"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    LIFECYCLE_VIOLATION = "LIFECYCLE_VIOLATION"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"


class AdapterError(RuntimeError):
    """Base error with stable, machine-readable and fail-closed semantics."""

    def __init__(self, code: ErrorCode, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class UnknownSemanticsError(AdapterError):
    def __init__(self, semantic: str):
        super().__init__(ErrorCode.UNKNOWN_SEMANTICS, f"unknown semantic: {semantic}")
        self.semantic = semantic


class AuthorizationRequiredError(AdapterError):
    def __init__(self, operation: str):
        super().__init__(ErrorCode.AUTHORIZATION_REQUIRED, f"authorization required for: {operation}")


class LifecycleError(AdapterError):
    def __init__(self, message: str):
        super().__init__(ErrorCode.LIFECYCLE_VIOLATION, message)


class LifecycleState(str, Enum):
    CREATED = "CREATED"
    STARTED = "STARTED"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Versioned support claim, not permission, trust, or normative compliance."""

    capability_id: str
    version: str
    semantics: tuple[str, ...]
    operations: tuple[str, ...]
    status: str = "EXPERIMENTAL"
    constraints: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.capability_id or not self.version:
            raise ValueError("capability_id and version are required")
        if self.status not in {"EXPERIMENTAL", "REFERENCE_IMPLEMENTATION"}:
            raise ValueError(f"unsupported public capability status: {self.status}")


@dataclass(frozen=True)
class EventDraft:
    event_type: str
    payload: Mapping[str, Any]
    actor: str
    record_time: str | None = None
    parents: tuple[str, ...] | None = None


@dataclass(frozen=True)
class MultimodalReference:
    """A provenance-bearing locator. Media bytes are deliberately out of band."""

    uri: str
    media_type: str
    digest: str
    provenance_refs: tuple[str, ...]
    byte_range: tuple[int, int] | None = None
    captured_at: str | None = None
    privacy_segment: str = "PERSONAL"

    def __post_init__(self) -> None:
        if not self.uri or not self.media_type or not self.digest or not self.provenance_refs:
            raise ValueError("multimodal references require URI, media type, digest, and provenance")
        if self.byte_range and (self.byte_range[0] < 0 or self.byte_range[1] <= self.byte_range[0]):
            raise ValueError("byte_range must be a non-empty half-open range")


@dataclass(frozen=True)
class StreamWindow:
    stream_id: str
    sequence: int
    start_time: str
    end_time: str
    references: tuple[MultimodalReference, ...]
    durable_event_ref: str | None = None

    def __post_init__(self) -> None:
        if self.sequence < 0 or self.end_time < self.start_time:
            raise ValueError("invalid stream window bounds")
        if not self.references:
            raise ValueError("a stream window requires at least one reference")


@dataclass(frozen=True)
class EvidenceObservation:
    semantic: str
    value: Any
    references: tuple[MultimodalReference, ...]
    observed_at: str


@runtime_checkable
class BoundedAdapter(Protocol):
    @property
    def lifecycle_state(self) -> LifecycleState: ...

    def capabilities(self) -> tuple[CapabilityDescriptor, ...]: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...


@runtime_checkable
class EventSink(Protocol):
    def append_event(self, draft: EventDraft) -> Event: ...


@runtime_checkable
class StorageAdapter(BoundedAdapter, Protocol):
    def append_event(self, draft: EventDraft) -> Event: ...

    def ordered_events(self, at_time: str | None = None) -> tuple[Event, ...]: ...


@runtime_checkable
class EvidenceAdapter(BoundedAdapter, Protocol):
    def observe(self, semantic: str, window: StreamWindow | None = None) -> EvidenceObservation: ...

    def promote(self, window: StreamWindow, authorization_ref: str) -> EventDraft: ...


@runtime_checkable
class IdentityAdapter(BoundedAdapter, Protocol):
    def resolve(self, identifier: str) -> Mapping[str, Any]: ...

    def verify(self, identifier: str, proof: Mapping[str, Any]) -> bool: ...


@runtime_checkable
class TransportAdapter(BoundedAdapter, Protocol):
    def send(self, recipient: str, artifact: Mapping[str, Any], authorization_ref: str) -> str: ...

    def receive(self) -> Sequence[Mapping[str, Any]]: ...


@runtime_checkable
class ToolAgentAdapter(BoundedAdapter, Protocol):
    def invoke(self, operation: str, arguments: Mapping[str, Any], authorization_ref: str) -> Mapping[str, Any]: ...


@runtime_checkable
class DeviceAdapter(BoundedAdapter, Protocol):
    def observe(self, semantic: str) -> EvidenceObservation: ...

    def actuate(self, operation: str, arguments: Mapping[str, Any], authorization_ref: str) -> Mapping[str, Any]: ...


@runtime_checkable
class ProjectionAdapter(BoundedAdapter, Protocol):
    def project(self, state: Any, request: Any, authorization: Any) -> Mapping[str, Any]: ...


@runtime_checkable
class ModelAdapter(BoundedAdapter, Protocol):
    @property
    def model_id(self) -> str: ...

    def infer(self, task: Any, context: Any, tools: Sequence[Any] | None = None) -> Any: ...


class InMemoryStorageAdapter:
    """Thread-safe reference storage. It is volatile and not production authority."""

    _DESCRIPTOR = CapabilityDescriptor(
        "pwm.storage.memory", "1.0-experimental", ("pwm.event-dag",), ("append", "ordered-read"),
        "REFERENCE_IMPLEMENTATION", {"durability": "process-lifetime"},
    )

    def __init__(self) -> None:
        self._log = PLog()
        self._state = LifecycleState.CREATED
        self._lock = RLock()

    @property
    def lifecycle_state(self) -> LifecycleState:
        return self._state

    def capabilities(self) -> tuple[CapabilityDescriptor, ...]:
        return (self._DESCRIPTOR,)

    def start(self) -> None:
        with self._lock:
            if self._state is LifecycleState.STOPPED:
                raise LifecycleError("a stopped adapter cannot be restarted")
            self._state = LifecycleState.STARTED

    def stop(self) -> None:
        with self._lock:
            if self._state is not LifecycleState.STARTED:
                raise LifecycleError("only a started adapter can be stopped")
            self._state = LifecycleState.STOPPED

    def _require_started(self) -> None:
        if self._state is not LifecycleState.STARTED:
            raise LifecycleError("storage adapter is not started")

    def append_event(self, draft: EventDraft) -> Event:
        self._require_started()
        if not draft.event_type or not draft.actor:
            raise AdapterError(ErrorCode.INVALID_INPUT, "event_type and actor are required")
        with self._lock:
            return self._log.append(
                draft.event_type, dict(draft.payload), draft.actor,
                parents=draft.parents, record_time=draft.record_time,
            )

    def ordered_events(self, at_time: str | None = None) -> tuple[Event, ...]:
        self._require_started()
        with self._lock:
            return tuple(deepcopy(self._log.ordered(at_time)))
