"""Namespaced example extension using only the public adapter module."""

from datetime import datetime, timezone
from typing import Any, Mapping

from pwm import (
    CapabilityDescriptor,
    EvidenceObservation,
    LifecycleError,
    LifecycleState,
    MultimodalReference,
    StreamWindow,
    UnknownSemanticsError,
)


class AcmeWeatherAdapter:
    KNOWN_SEMANTICS = frozenset({"air.temperature.celsius", "air.relative_humidity.percent"})

    def __init__(self, values: Mapping[str, Any]):
        self._values = dict(values)
        self._state = LifecycleState.CREATED

    @property
    def lifecycle_state(self):
        return self._state

    def capabilities(self):
        return (
            CapabilityDescriptor(
                "org.example.acme.weather", "0.1.0", tuple(sorted(self.KNOWN_SEMANTICS)), ("observe",)
            ),
        )

    def start(self):
        if self._state is LifecycleState.STOPPED:
            raise LifecycleError("stopped Acme adapters cannot restart")
        self._state = LifecycleState.STARTED

    def stop(self):
        if self._state is not LifecycleState.STARTED:
            raise LifecycleError("Acme adapter is not started")
        self._state = LifecycleState.STOPPED

    def observe(self, semantic: str, window: StreamWindow | None = None):
        if self._state is not LifecycleState.STARTED:
            raise LifecycleError("Acme adapter is not started")
        if semantic not in self.KNOWN_SEMANTICS or semantic not in self._values:
            raise UnknownSemanticsError(semantic)
        reference = MultimodalReference(
            "acme-fixture://weather/station-1", "application/json", "sha256:fixture", ("acme:fixture:1",)
        )
        return EvidenceObservation(semantic, self._values[semantic], (reference,), datetime.now(timezone.utc).isoformat())

    def promote(self, window: StreamWindow, authorization_ref: str):
        if not authorization_ref:
            raise LifecycleError("promotion requires an authorization reference")
        raise NotImplementedError("the example does not claim durable promotion support")
