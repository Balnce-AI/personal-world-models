from common import model, seed

with model() as pwm:
    evidence = seed(pwm)
    world, branch = pwm.possible_world("rain", ({"predicate": "weather", "object": "rain"},), (evidence.event_id,))
    print(world.world_id, branch.assertions)
