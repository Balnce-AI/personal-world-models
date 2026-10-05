from pathlib import Path

from pwm_hpl_ref.research import FixtureControlModel, run_experiment

root = Path(__file__).resolve().parents[2]
result = run_experiment(
    root / "experiments/data/personas/longitudinal-persona.json",
    FixtureControlModel(),
    conditions=("flat_derived", "structured_model_ecology"),
)
print(result["experimentId"], [run["metrics"] for run in result["runs"]])
