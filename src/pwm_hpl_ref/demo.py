import json
from .plog import PLog
from .pwm import Materializer
from .authority import Constraint, AuthorityEngine
from .projection import ProjectionRequest, ProjectionCompiler
from .crypto import generate_keypair
from .arranger import ArrangerIssuer
from .learning import learning_candidate
from .departure import make_receipt
from .web0 import issue_broadcast

def build_fixture():
    log=PLog(); actor="did:example:person:alice"
    e=log.append("entity.put",{"id":actor,"type":"Person","labels":["Alice"],"privacyClass":"PERSONAL","provenance":[]},actor)
    now="2026-01-01T00:00:00+00:00"
    log.append("assertion.put",{"id":"a1","subject":actor,"predicate":"delivery.preferred_surface","object":"kitchen.counter.north","recordTime":now,"epistemicStatus":"ASSERTED","confidence":{"explicit":1.0},"privacyClass":"PERSONAL","provenance":[e.event_id]},actor)
    log.append("assertion.put",{"id":"a2","subject":actor,"predicate":"home.private_zone","object":"bedroom","recordTime":now,"epistemicStatus":"ASSERTED","confidence":{"explicit":1.0},"privacyClass":"SENSITIVE","provenance":[e.event_id]},actor)
    log.append("assertion.put",{"id":"a3","subject":actor,"predicate":"accessibility.route","object":"avoid-stairs","recordTime":now,"epistemicStatus":"ASSERTED","confidence":{"explicit":1.0},"privacyClass":"PERSONAL","provenance":[e.event_id]},actor)
    return log,actor

def main():
    log,person=build_fixture(); state=Materializer().materialize(log)
    constraints=[
      Constraint(person,"ALLOW",frozenset({"navigate.allowed_zone","place.sealed_package"}),"PERSONAL"),
      Constraint("did:example:robot:oem","DENY",frozenset({"map.export","camera.raw_export"}),"PHYSICAL"),
    ]
    decision=AuthorityEngine().resolve({"navigate.allowed_zone","place.sealed_package","map.export"},constraints)
    req=ProjectionRequest("Deliver sealed parcel to kitchen counter","did:example:robot:delivery-7",("delivery.preferred_surface","accessibility.route"),tuple(decision.requested),"PERSONAL",600)
    projection=ProjectionCompiler().compile(state,req,decision)
    private,public=generate_keypair(); issuer=ArrangerIssuer()
    arranger=issuer.issue(private,person,req.recipient,req.purpose,{"projection":projection},["CONTEXT","AUTHORITY","PROCEDURE"],projection["provenance"])
    assert issuer.verify(public,arranger)
    candidate=learning_candidate(req.recipient,{"subject":person,"predicate":"delivery.observed_success","object":True},{"sourceReliability":0.8},arranger["artifactId"],True)
    receipt=make_receipt("session-demo",arranger["artifactId"],req.recipient,"PROTOCOL_DEPARTURE",{"acknowledged":True})
    broadcast=issue_broadcast(private,req.recipient,"CAPABILITY",{"capability":"sealed-package-delivery","zone":"kitchen-only"})
    print(json.dumps({"projection":projection,"arranger":arranger,"learningCandidate":candidate,"departureReceipt":receipt,"machineBroadcast":broadcast},indent=2))

if __name__=="__main__": main()
