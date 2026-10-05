from common import model, seed


def projection_hook(state, request, authorization):
    return {"authorization": authorization["authorizationRef"], "request": request, "count": len(state.assertions)}


with model(projection_hook=projection_hook) as pwm:
    seed(pwm)
    print(pwm.project({"purpose": "route-help"}))
