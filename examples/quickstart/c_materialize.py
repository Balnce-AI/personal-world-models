from common import model, seed

with model() as pwm:
    seed(pwm)
    print(pwm.materialize().assertions)
