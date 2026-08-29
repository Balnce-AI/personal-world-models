from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from .canonical import sha256_urn

@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    record_time: str
    actor: str
    payload: dict[str, Any]
    parents: tuple[str, ...]
    content_hash: str

class PLog:
    """Public reference event DAG. Not the complete private Balnce PLOG/UOR implementation."""
    def __init__(self):
        self.events: dict[str, Event] = {}
        self.heads: set[str] = set()

    def append(self, event_type: str, payload: dict[str, Any], actor: str, parents=None, record_time=None) -> Event:
        parents = tuple(sorted(parents if parents is not None else self.heads))
        record_time = record_time or datetime.now(timezone.utc).isoformat()
        body = {"eventType":event_type,"recordTime":record_time,"actor":actor,"payload":payload,"parents":list(parents)}
        content_hash = sha256_urn("pwm:event-content", body)
        event_id = sha256_urn("pwm:event", {**body,"contentHash":content_hash})
        event = Event(event_id,event_type,record_time,actor,payload,parents,content_hash)
        self.events[event_id]=event
        self.heads.difference_update(parents)
        self.heads.add(event_id)
        return event

    def ordered(self, at_time: str|None=None):
        events=list(self.events.values())
        if at_time: events=[e for e in events if e.record_time <= at_time]
        return sorted(events, key=lambda e:(e.record_time,e.event_id))
