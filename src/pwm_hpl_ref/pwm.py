from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .plog import PLog

@dataclass
class PWMState:
    entities: dict[str, dict[str,Any]] = field(default_factory=dict)
    relations: dict[str, dict[str,Any]] = field(default_factory=dict)
    assertions: dict[str, dict[str,Any]] = field(default_factory=dict)
    policies: dict[str, dict[str,Any]] = field(default_factory=dict)
    applied_events: list[str] = field(default_factory=list)

class Materializer:
    def materialize(self, plog:PLog, at_time:str|None=None) -> PWMState:
        state=PWMState()
        for event in plog.ordered(at_time):
            p=event.payload
            if event.event_type == "entity.put": state.entities[p["id"]]=dict(p)
            elif event.event_type == "relation.put": state.relations[p["id"]]=dict(p)
            elif event.event_type == "assertion.put": state.assertions[p["id"]]=dict(p)
            elif event.event_type == "assertion.revoke" and p["id"] in state.assertions:
                state.assertions[p["id"]]["epistemicStatus"]="REVOKED"
            elif event.event_type == "policy.put": state.policies[p["id"]]=dict(p)
            state.applied_events.append(event.event_id)
        return state
