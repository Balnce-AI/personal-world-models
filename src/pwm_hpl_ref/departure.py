from datetime import datetime, timezone
from .canonical import sha256_urn

LEVELS=("KEY_INVALIDATED","DEACTIVATED","PROTOCOL_DEPARTURE","ATTESTED_DEPARTURE","VERIFIED_DEPARTURE","UNVERIFIED")

def make_receipt(session_id:str,artifact_id:str,recipient:str,level:str,evidence:dict):
    if level not in LEVELS: raise ValueError("unknown departure assurance level")
    body={"sessionId":session_id,"artifactId":artifact_id,"recipient":recipient,"level":level,"timestamp":datetime.now(timezone.utc).isoformat(),"evidence":evidence}
    body["receiptId"]=sha256_urn("hpl:departure",body)
    return body
