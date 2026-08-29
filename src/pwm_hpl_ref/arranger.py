from datetime import datetime, timedelta, timezone
import secrets
from .canonical import canonical_json, sha256_urn
from .crypto import sign_json, verify_json

class ArrangerIssuer:
    def issue(self,private_key,issuer:str,recipient:str,purpose:str,payload:dict,classes:list[str],provenance:list[str],ttl_seconds=600,departure_requirement="PROTOCOL_DEPARTURE"):
        now=datetime.now(timezone.utc)
        unsigned={
            "artifactClasses":classes,"issuer":issuer,"recipient":recipient,"purpose":purpose,
            "issuedAt":now.isoformat(),"expiresAt":(now+timedelta(seconds=ttl_seconds)).isoformat(),
            "nonce":secrets.token_hex(16),"payloadHash":sha256_urn("hpl:payload",payload),
            "revocationHandle":secrets.token_urlsafe(24),"provenance":sorted(set(provenance)),
            "departureRequirement":departure_requirement
        }
        artifact_id=sha256_urn("hpl:arranger",unsigned)
        signed={"artifactId":artifact_id,**unsigned}
        signed["signature"]=sign_json(private_key,signed)
        return signed

    @staticmethod
    def verify(public_key,artifact):
        sig=artifact.get("signature","")
        unsigned={k:v for k,v in artifact.items() if k!="signature"}
        return verify_json(public_key,unsigned,sig)
