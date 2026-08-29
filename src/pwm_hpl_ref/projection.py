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
        limit=PRIVACY_ORDER[request.max_privacy]
        fields=[]; provenance=[]
        for a in state.assertions.values():
            if a.get("epistemicStatus") in {"REVOKED","SUPERSEDED"}: continue
            if a.get("predicate") not in request.predicates: continue
            if PRIVACY_ORDER.get(a.get("privacyClass","PERSONAL"),2) > limit: continue
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
