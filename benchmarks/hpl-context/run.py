from pwm_hpl_ref.demo import build_fixture
from pwm_hpl_ref.pwm import Materializer
from pwm_hpl_ref.authority import Constraint, AuthorityEngine
from pwm_hpl_ref.projection import ProjectionRequest, ProjectionCompiler

def run():
    log,person=build_fixture(); state=Materializer().materialize(log)
    total=len(state.assertions)
    decision=AuthorityEngine().resolve({"navigate.allowed_zone"},[Constraint(person,"ALLOW",frozenset({"navigate.allowed_zone"}),"PERSONAL")])
    req=ProjectionRequest("delivery","robot",("delivery.preferred_surface","accessibility.route"),tuple(decision.requested),"PERSONAL")
    proj=ProjectionCompiler().compile(state,req,decision)
    disclosed=len(proj["fields"])
    return {"total_assertions":total,"disclosed_assertions":disclosed,"disclosure_ratio":disclosed/total if total else 0}

if __name__=="__main__": print(run())
