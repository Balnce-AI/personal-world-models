from common import model, seed

with model() as pwm:
    print(seed(pwm).event_id)
