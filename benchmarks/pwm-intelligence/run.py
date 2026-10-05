from pathlib import Path

from pwm_hpl_ref.research import CANONICAL_CONDITIONS, FixtureControlModel, generate_coverage, run_experiment, write_result


ROOT = Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    result = run_experiment(
        ROOT / "experiments/data/personas/longitudinal-persona.json",
        FixtureControlModel(),
        conditions=CANONICAL_CONDITIONS,
    )
    output = ROOT / "experiments/results/fixture-control.json"
    write_result(result, output)
    write_result(
        generate_coverage(
            ROOT / "experiments/scenarios/corpus.json",
            (ROOT / "experiments/data/personas").glob("*.json"),
        ),
        ROOT / "experiments/results/scenario-coverage.json",
    )
    print(output)
