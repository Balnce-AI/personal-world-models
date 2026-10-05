from common import PERSON, model, seed
from pwm import ModelRecord

with model() as pwm:
    evidence = seed(pwm)
    candidate = ModelRecord.create(
        model_kind="SELF",
        family_id="pwm.preference",
        subject_ids=(PERSON,),
        perspective=PERSON,
        state={"routePreference": "quiet"},
        epistemic_status="INFERRED",
        confidence_ppm=800_000,
        uncertainty={"kind": "single-source"},
        provenance_refs=(evidence.event_id,),
        record_time="2026-01-01T00:00:02+00:00",
    )
    proposal = pwm.propose_model(candidate, "model:local")
    pwm.accept_model(candidate, PERSON, proposal.event_id)
    print(pwm.materialize().models[candidate.model_id])
