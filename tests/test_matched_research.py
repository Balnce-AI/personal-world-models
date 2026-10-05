import json
from pathlib import Path

from pwm_hpl_ref.foundation_models import DeterministicByteTokenizer, DeterministicWhitespaceTokenizer, InferenceResult
from pwm_hpl_ref.research import FixtureControlModel, generate_coverage, run_experiment


ROOT = Path(__file__).parents[1]
PERSONA = ROOT / "experiments/data/personas/longitudinal-persona.json"


def _tasks_by_condition(result):
    return {run["condition"]: {task["taskId"]: task for task in run["tasks"]} for run in result["runs"]}


def test_information_equivalent_representations_have_equal_signatures_and_exact_tokens():
    conditions = (
        "flat_normalized_source_facts", "structured_assertions",
        "flat_information_matched", "structured_information_matched",
    )
    result = run_experiment(PERSONA, FixtureControlModel(), conditions=conditions)
    tasks = _tasks_by_condition(result)
    for task_id in tasks["flat_normalized_source_facts"]:
        assert tasks["flat_normalized_source_facts"][task_id]["informationSignature"] == tasks["structured_assertions"][task_id]["informationSignature"]
        assert tasks["flat_information_matched"][task_id]["informationSignature"] == tasks["structured_information_matched"][task_id]["informationSignature"]
        budgets = [tasks[condition][task_id]["tokenBudget"] for condition in conditions]
        assert len({budget["finalTokenCount"] for budget in budgets}) == 1
        assert all(budget["exact"] and budget["verified"] for budget in budgets)
        assert all(budget["naturalTokenCount"] + budget["paddingTokenCount"] == budget["finalTokenCount"] for budget in budgets)


def test_controls_change_only_declared_experimental_axes():
    result = run_experiment(
        PERSONA,
        FixtureControlModel(),
        conditions=("flat_information_matched", "structured_information_matched", "structured_model_ecology_meta", "corrupt"),
    )
    runs = {run["condition"]: run for run in result["runs"]}
    assert runs["flat_information_matched"]["conditionTaxonomy"]["experimentClass"] == "representation"
    assert runs["structured_information_matched"]["conditionTaxonomy"]["experimentClass"] == "representation"
    assert runs["structured_model_ecology_meta"]["conditionTaxonomy"]["experimentClass"] == "derivation"
    assert runs["corrupt"]["conditionTaxonomy"]["experimentClass"] == "confidence"
    flat = _tasks_by_condition(result)["flat_information_matched"]["travel-plan"]
    structured = _tasks_by_condition(result)["structured_information_matched"]["travel-plan"]
    assert flat["informationLedger"] == structured["informationLedger"]


def test_unverified_tokenizer_never_claims_exact_matching():
    result = run_experiment(
        PERSONA,
        FixtureControlModel(),
        conditions=("stateless", "structured_assertions"),
        tokenizer=DeterministicWhitespaceTokenizer(),
    )
    assert result["tokenizer"]["tokenizerId"] == "deterministic-whitespace-v1"
    assert result["tokenizer"]["exact"] is False
    assert result["tokenizer"]["verified"] is False
    assert all(not task["tokenBudget"]["verified"] for run in result["runs"] for task in run["tasks"])


def test_seed_and_repetition_are_recorded_and_coverage_is_deterministic():
    result = run_experiment(PERSONA, FixtureControlModel(), conditions=("shuffled_topology",), seed=17, repetitions=2)
    assert result["seed"] == 17
    assert result["repetitions"] == 2
    assert [run["repetition"] for run in result["runs"]] == [0, 1]
    corpus = ROOT / "experiments/scenarios/corpus.json"
    personas = tuple((ROOT / "experiments/data/personas").glob("*.json"))
    first = generate_coverage(corpus, personas)
    second = generate_coverage(corpus, reversed(personas))
    assert first == second
    assert first["scenarioCount"] == 25
    assert first["coverageHash"].startswith("urn:pwm:scenario-coverage:sha256:")
    by_id = {scenario["scenarioId"]: scenario for scenario in first["scenarios"]}
    assert by_id["travel"]["coverageStatus"] == "EXECUTABLE"
    assert by_id["scheduling"]["coverageStatus"] == "TASK_LINKED"
    assert json.loads(corpus.read_text())["pmraClassification"]["primitiveDimensions"] == [
        "architectural", "evidence", "authority", "query", "policy", "evaluation", "topology"
    ]


def test_identical_fixture_runs_have_identical_identity_and_cells():
    first = run_experiment(PERSONA, FixtureControlModel(), conditions=("flat_information_matched",), seed=9)
    second = run_experiment(PERSONA, FixtureControlModel(), conditions=("flat_information_matched",), seed=9)
    assert first["experimentId"] == second["experimentId"]
    assert first["runs"] == second["runs"]


def test_provider_token_disagreement_prevents_verified_run_claim():
    class MismatchedUsageModel(FixtureControlModel):
        model_id = "mismatched-usage"
        tokenizer = DeterministicByteTokenizer()

        def infer(self, task, context, tools=None):
            result = super().infer(task, context, tools)
            return InferenceResult(result.output, self.model_id, usage={"prompt_tokens": 1}, confidence_ppm=result.confidence_ppm)

    result = run_experiment(PERSONA, MismatchedUsageModel(), conditions=("structured_assertions",))
    assert all(run["localTokenMatchingVerified"] for run in result["runs"])
    assert all(run["providerTokenMatchingVerified"] is False for run in result["runs"])
    assert all(run["tokenMatchingVerified"] is False for run in result["runs"])


def test_raw_retrieval_respects_task_privacy_ceiling():
    persona = json.loads(PERSONA.read_text())
    task = dict(persona["tasks"][0])
    task["queryTerms"] = ["fatigue"]
    task["maxPrivacyClass"] = "PERSONAL"
    from pwm_hpl_ref.research import build_condition, materialize_persona
    state, raw = materialize_persona(persona)
    projection = build_condition("retrieval_raw", state, raw, persona["personaId"], task)
    assert projection.content["memories"] == []


def test_non_applicable_topology_control_is_marked_outside_model_content():
    persona = ROOT / "experiments/data/personas/institutional-care-persona.json"
    result = run_experiment(persona, FixtureControlModel(), conditions=("shuffled_topology",))
    task = result["runs"][0]["tasks"][0]
    assert task["controlApplicable"] is False
    assert "ablationApplied" not in json.dumps(task["informationLedger"])
