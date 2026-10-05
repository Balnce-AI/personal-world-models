from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from .canonical import sha256_urn
from .pwm import PWMState
from .authority import Decision

PRIVACY_ORDER={"PUBLIC":0,"LOW":1,"PERSONAL":2,"SENSITIVE":3,"HIGHLY_SENSITIVE":4}

@dataclass(frozen=True)
class ProjectionRequest:
    purpose: str
    recipient: str
    predicates: tuple[str,...]
    capabilities: tuple[str,...]
    max_privacy: str="PERSONAL"
    ttl_seconds: int=600

class ProjectionCompiler:
    def compile(self,state:PWMState,request:ProjectionRequest,authority:Decision):
        if authority.requested != frozenset(request.capabilities):
            raise ValueError("authority decision is not bound to the requested capabilities")
        if not authority.allowed:
            raise ValueError("authority decision grants no requested capability")
        limit=PRIVACY_ORDER[request.max_privacy]
        fields=[]; provenance=[]
        for a in state.assertions.values():
            if a.get("epistemicStatus") in {"REVOKED","SUPERSEDED"}: continue
            if a.get("predicate") not in request.predicates: continue
            privacy=a.get("privacyClass","PERSONAL")
            if privacy not in PRIVACY_ORDER:
                raise ValueError(f"unknown privacy class: {privacy}")
            if PRIVACY_ORDER[privacy] > limit: continue
            fields.append({k:a.get(k) for k in ["subject","predicate","object","epistemicStatus","confidence"] if k in a})
            provenance.extend(a.get("provenance",[]))
        now=datetime.now(timezone.utc)
        body={
            "purpose":request.purpose,"recipient":request.recipient,
            "issuedAt":now.isoformat(),"expiresAt":(now+timedelta(seconds=request.ttl_seconds)).isoformat(),
            "fields":fields,"allowedCapabilities":sorted(authority.allowed),
            "forbiddenCapabilities":sorted(authority.denied),"provenance":sorted(set(provenance))
        }
        return {"projectionId":sha256_urn("hpl:projection",body),**body}
