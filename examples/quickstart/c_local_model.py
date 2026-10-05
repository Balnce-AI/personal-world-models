from pwm_hpl_ref.foundation_models import LocalCallableModel, ModelProjection, Task

adapter = LocalCallableModel(
    "local-example-v1",
    lambda task, context: {"answer": context.content["preference"], "task": task.task_id},
)
result = adapter.infer(
    Task("route", "Choose the route preference", ("answer",)),
    ModelProjection("bounded", {"preference": "quiet"}),
)
print(result.output)
