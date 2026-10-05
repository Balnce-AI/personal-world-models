from common import model

with model() as pwm:
    print([item.capability_id for item in pwm.capabilities()])
