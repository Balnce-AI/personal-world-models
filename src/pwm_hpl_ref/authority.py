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
    binding_ref: str | None = None
    granting_principals: tuple[str, ...] = ()
    denying_principals: tuple[str, ...] = ()
    grant_sources: tuple[tuple[str, str], ...] = ()
    deny_sources: tuple[tuple[str, str], ...] = ()

class AuthorityEngine:
    """Conservative deny-overrides reference algebra."""
    def resolve(
        self, requested:Iterable[str], constraints:Iterable[Constraint], *, binding_ref: str | None = None
    ) -> Decision:
        requested=frozenset(requested)
        grants=set()
        denies=set()
        reasons=[]
        granting_principals=set()
        denying_principals=set()
        grant_sources=set()
        deny_sources=set()
        for c in constraints:
            if c.effect == "ALLOW":
                grants.update(c.capabilities)
                granting_principals.add(c.principal)
                grant_sources.update((capability, c.principal) for capability in c.capabilities)
            elif c.effect == "DENY":
                denies.update(c.capabilities)
                denying_principals.add(c.principal)
                deny_sources.update((capability, c.principal) for capability in c.capabilities)
                reasons.append(f"{c.constraint_class}:{c.principal} denied {sorted(c.capabilities)}")
        # No implicit authority: requested capabilities require at least one grant.
        allowed=(requested & grants) - denies
        denied=requested-allowed
        return Decision(
            requested, frozenset(allowed), frozenset(denied), tuple(reasons), binding_ref,
            tuple(sorted(granting_principals)), tuple(sorted(denying_principals)),
            tuple(sorted(grant_sources)), tuple(sorted(deny_sources)),
        )
