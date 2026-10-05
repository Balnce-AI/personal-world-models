from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable
from copy import deepcopy
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
    def __init__(self, clock: Callable[[], str] | None = None):
        self.events: dict[str, Event] = {}
        self.heads: set[str] = set()
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def append(self, event_type: str, payload: dict[str, Any], actor: str, parents=None, record_time=None) -> Event:
        parents = tuple(sorted(parents if parents is not None else self.heads))
        record_time = record_time or self._clock()
        payload = deepcopy(payload)
        body = {"eventType":event_type,"recordTime":record_time,"actor":actor,"payload":payload,"parents":list(parents)}
        content_hash = sha256_urn("pwm:event-content", body)
        event_id = sha256_urn("pwm:event", {**body,"contentHash":content_hash})
        event = Event(event_id,event_type,record_time,actor,payload,parents,content_hash)
        self.events[event_id]=event
        self.heads.difference_update(parents)
        self.heads.add(event_id)
        return deepcopy(event)

    def ordered(self, at_time: str|None=None):
        events=[]
        for event in self.events.values():
            body = {"eventType":event.event_type,"recordTime":event.record_time,"actor":event.actor,"payload":event.payload,"parents":list(event.parents)}
            content_hash = sha256_urn("pwm:event-content", body)
            event_id = sha256_urn("pwm:event", {**body,"contentHash":content_hash})
            if content_hash != event.content_hash or event_id != event.event_id:
                raise ValueError(f"event integrity check failed: {event.event_id}")
            events.append(deepcopy(event))
        if at_time: events=[e for e in events if e.record_time <= at_time]
        selected={event.event_id:event for event in events}
        children={event_id:[] for event_id in selected}
        indegree={event_id:0 for event_id in selected}
        for event in events:
            for parent in event.parents:
                if parent not in selected:
                    raise ValueError(f"missing parent in selected event closure: {parent}")
                children[parent].append(event.event_id)
                indegree[event.event_id]+=1
        ready=sorted((selected[event_id] for event_id,degree in indegree.items() if degree == 0),key=lambda event:(event.record_time,event.event_id))
        ordered=[]
        while ready:
            event=ready.pop(0); ordered.append(event)
            for child in children[event.event_id]:
                indegree[child]-=1
                if indegree[child] == 0:
                    ready.append(selected[child]); ready.sort(key=lambda item:(item.record_time,item.event_id))
        if len(ordered) != len(events):
            raise ValueError("event graph contains a cycle")
        return ordered
