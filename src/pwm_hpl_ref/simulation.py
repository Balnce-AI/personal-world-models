"""Deterministic event-only simulation fixtures for SDK and adapter tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from .adapters import EventDraft, EventSink
from .plog import Event


@dataclass(frozen=True)
class SimulationStep:
    offset_seconds: int
    event_type: str
    payload: Mapping[str, Any]
    actor: str = "did:example:simulation"


class SimulationSource:
    """Emits a fixed script through EventSink and has no canonical-state handle."""

    def __init__(self, steps: Iterable[SimulationStep], *, epoch: str = "2026-01-01T00:00:00+00:00"):
        self._steps = tuple(sorted(steps, key=lambda step: (step.offset_seconds, step.event_type)))
        parsed = datetime.fromisoformat(epoch.replace("Z", "+00:00"))
        self._epoch = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def emit(self, sink: EventSink) -> tuple[Event, ...]:
        emitted = []
        for step in self._steps:
            if step.offset_seconds < 0:
                raise ValueError("reference simulation offsets cannot be negative")
            emitted.append(
                sink.append_event(
                    EventDraft(
                        step.event_type,
                        step.payload,
                        step.actor,
                        record_time=(self._epoch + timedelta(seconds=step.offset_seconds)).isoformat(),
                    )
                )
            )
        return tuple(emitted)
