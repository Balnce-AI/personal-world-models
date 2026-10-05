import json
from pathlib import Path

from pwm_hpl_ref.ablation import ABLATIONS
from pwm_hpl_ref.foundation_models import InferenceResult, ModelProjection, Task
from pwm_hpl_ref.research import CONDITIONS, FixtureControlModel, build_condition, load_persona, materialize_persona, run_experiment
from pwm_hpl_ref.schema_validation import validate_record


ROOT = Path(__file__).parents[1]
PERSONA = ROOT / "experiments/data/personas/longitudinal-persona.json"


def test_research_run_emits_all_conditions_and_negative_controls():
    conditions = CONDITIONS + tuple(sorted(ABLATIONS))
    result = run_experiment(PERSONA, FixtureControlModel(), conditions=conditions)
    assert {run["condition"] for run in result["runs"]} == set(conditions)
    assert result["metricStatus"] == "EXPERIMENTAL"
    assert result["datasetHash"].startswith("urn:pwm:dataset:sha256:")
    assert all(run["taskCount"] == 6 for run in result["runs"])
    by_condition = {run["condition"]: run["metrics"] for run in result["runs"]}
    assert by_condition["pwm+self_meta"]["correctPpm"] > by_condition["no_memory"]["correctPpm"]
    assert by_condition["fabricated_provenance"]["provenanceCoveragePpm"] == 0
    assert by_condition["adversarial_contradiction"]["correctPpm"] < by_condition["pwm+self_meta"]["correctPpm"]
    assert by_condition["shuffled_topology"]["correctPpm"] < by_condition["pwm+self_meta"]["correctPpm"]
    validate_record("pwm-experiment-manifest.schema.json", result)


def test_scenario_corpus_has_required_25_scenarios_and_research_fields():
    corpus = json.loads((ROOT / "experiments/scenarios/corpus.json").read_text())
    assert len(corpus["scenarios"]) == 25
    required = {
        "rawEvidence", "rubric", "requiredModelClasses", "prohibitedInformationLeakage",
        "expectedUncertainty", "expectedActionConstraints", "counterfactualVariants",
    }
    assert all(required <= scenario.keys() for scenario in corpus["scenarios"])


def test_foundation_model_candidates_are_not_canonical_writes():
    class CandidateModel:
        model_id = "candidate-only"

        def infer(self, task, context, tools=None):
            return InferenceResult({}, self.model_id, ({"modelId": "unreviewed"},))

    context = ModelProjection("no_memory", {"knowledge": {}})
    result = CandidateModel().infer(Task("t", "test"), context)
    assert result.candidates == ({"modelId": "unreviewed"},)
    assert "models" not in context.content


def test_all_three_topologically_distinct_personas_execute():
    persona_dir = ROOT / "experiments/data/personas"
    results = [run_experiment(path, FixtureControlModel(), conditions=("pwm+self_meta",)) for path in sorted(persona_dir.glob("*.json"))]
    assert len(results) == 3
    assert all(result["runs"][0]["taskCount"] >= 1 for result in results)
    topologies = {json.loads(path.read_text())["topology"] for path in persona_dir.glob("*.json")}
    assert len(topologies) == 3


def test_projection_provenance_does_not_reintroduce_withheld_sensitive_assertions():
    persona = load_persona(PERSONA)
    state, raw = materialize_persona(persona)
    travel_task = next(task for task in persona["tasks"] if task["taskId"] == "travel-plan")
    projection = build_condition("pwm+self_meta", state, raw, persona["personaId"], travel_task)
    provenance_payloads = [entry["payload"] for entry in projection.content["provenanceEvents"].values()]
    assert not any(payload.get("predicate") == "healthUncertainty" for payload in provenance_payloads)


def test_checked_in_experiment_result_is_a_valid_generated_manifest():
    result = json.loads((ROOT / "experiments/results/fixture-control.json").read_text())
    validate_record("pwm-experiment-manifest.schema.json", result)
    assert result["foundationModel"] == "fixture-control-v1"
