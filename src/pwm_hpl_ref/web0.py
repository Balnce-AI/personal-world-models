from datetime import datetime, timedelta, timezone
from .canonical import sha256_urn
from .crypto import sign_json, verify_json

KINDS={"NEED","CAPABILITY","AVAILABILITY","FAILURE","OPPORTUNITY","SUPPORT_REQUEST","SERVICE_REQUEST","ENERGY_NEED","COMPUTE_CAPACITY","MAINTENANCE_ALERT"}

def issue_broadcast(private_key,sender:str,kind:str,payload:dict,ttl_seconds=300):
    if kind not in KINDS: raise ValueError("unsupported broadcast kind")
    now=datetime.now(timezone.utc)
    unsigned={"sender":sender,"kind":kind,"payload":payload,"issuedAt":now.isoformat(),"expiresAt":(now+timedelta(seconds=ttl_seconds)).isoformat()}
    body={"broadcastId":sha256_urn("web0:broadcast",unsigned),**unsigned}
    body["signature"]=sign_json(private_key,body)
    return body

def verify_broadcast(public_key,broadcast):
    sig=broadcast["signature"]
    unsigned={k:v for k,v in broadcast.items() if k!="signature"}
    return verify_json(public_key,unsigned,sig)
