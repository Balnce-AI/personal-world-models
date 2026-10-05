from pwm_hpl_ref.demo import build_fixture
from pwm_hpl_ref.pwm import Materializer
from pwm_hpl_ref.authority import Constraint, AuthorityEngine
from pwm_hpl_ref.projection import ProjectionRequest, ProjectionCompiler
from pwm_hpl_ref.crypto import generate_keypair
from pwm_hpl_ref.arranger import ArrangerIssuer
from pwm_hpl_ref.departure import make_receipt

def test_materialization_is_deterministic():
    log,_=build_fixture(); m=Materializer()
    assert m.materialize(log).assertions == m.materialize(log).assertions

def test_projection_minimizes_and_excludes_sensitive_zone():
    log,person=build_fixture(); state=Materializer().materialize(log)
    d=AuthorityEngine().resolve({"navigate.allowed_zone"},[Constraint(person,"ALLOW",frozenset({"navigate.allowed_zone"}),"PERSONAL")])
    req=ProjectionRequest("delivery","robot",("delivery.preferred_surface","home.private_zone"),tuple(d.requested),"PERSONAL")
    proj=ProjectionCompiler().compile(state,req,d)
    predicates={x["predicate"] for x in proj["fields"]}
    assert "delivery.preferred_surface" in predicates
    assert "home.private_zone" not in predicates

def test_projection_rejects_authority_decision_for_different_capabilities():
    log,person=build_fixture(); state=Materializer().materialize(log)
    d=AuthorityEngine().resolve({"navigate.allowed_zone"},[Constraint(person,"ALLOW",frozenset({"navigate.allowed_zone"}),"PERSONAL")])
    req=ProjectionRequest("delivery","robot",("delivery.preferred_surface",),("map.export",),"PERSONAL")
    try:
        ProjectionCompiler().compile(state,req,d)
        assert False, "mismatched authority decision was accepted"
    except ValueError as error:
        assert "not bound" in str(error)

def test_deny_overrides_grant():
    constraints=[Constraint("owner","ALLOW",frozenset({"drive","export.map"}),"PERSONAL"),Constraint("oem","DENY",frozenset({"export.map"}),"PHYSICAL")]
    d=AuthorityEngine().resolve({"drive","export.map"},constraints)
    assert d.allowed == frozenset({"drive"})
    assert "export.map" in d.denied

def test_arranger_signature_detects_tamper():
    private,public=generate_keypair(); issuer=ArrangerIssuer()
    a=issuer.issue(private,"person","robot","task",{"x":1},["CONTEXT"],[])
    assert issuer.verify(public,a)
    a["purpose"]="changed"
    assert not issuer.verify(public,a)

def test_departure_receipt_is_bounded_claim():
    r=make_receipt("s","a","robot","PROTOCOL_DEPARTURE",{"ack":True})
    assert r["level"] == "PROTOCOL_DEPARTURE"
