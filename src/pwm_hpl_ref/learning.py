from .canonical import sha256_urn

def learning_candidate(source:str,claim:dict,confidence:dict,session_artifact:str,requires_review=True):
    body={"source":source,"claim":claim,"confidence":confidence,"sessionArtifact":session_artifact,"requiresReview":requires_review}
    return {"candidateId":sha256_urn("hpl:learning",body),**body}
