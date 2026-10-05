from common import model, seed

with model() as pwm:
    evidence = seed(pwm)
    world, branch = pwm.possible_world(
        "route closed",
        ({"subject": "did:example:alice", "predicate": "route.closed", "object": True},),
        (evidence.event_id,),
        base_time="2026-01-01T00:00:02+00:00",
    )
    print(world.to_record())
    print(branch.assertions)
