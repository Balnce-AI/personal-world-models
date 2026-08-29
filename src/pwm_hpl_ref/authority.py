from dataclasses import dataclass
from typing import Iterable

MANDATORY_CLASSES={"PHYSICAL","LEGAL"}

@dataclass(frozen=True)
class Constraint:
    principal: str
    effect: str
    capabilities: frozenset[str]
    constraint_class: str

@dataclass(frozen=True)
class Decision:
    requested: frozenset[str]
    allowed: frozenset[str]
    denied: frozenset[str]
    reasons: tuple[str,...]

class AuthorityEngine:
    """Conservative deny-overrides reference algebra."""
    def resolve(self, requested:Iterable[str], constraints:Iterable[Constraint]) -> Decision:
        requested=frozenset(requested)
        grants=set()
        denies=set()
        reasons=[]
        for c in constraints:
            if c.effect == "ALLOW": grants.update(c.capabilities)
            elif c.effect == "DENY":
                denies.update(c.capabilities)
                reasons.append(f"{c.constraint_class}:{c.principal} denied {sorted(c.capabilities)}")
        # No implicit authority: requested capabilities require at least one grant.
        allowed=(requested & grants) - denies
        denied=requested-allowed
        return Decision(requested,frozenset(allowed),frozenset(denied),tuple(reasons))
