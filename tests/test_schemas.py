import json
from pathlib import Path
from jsonschema import Draft202012Validator
from jsonschema import FormatChecker

from pwm_hpl_ref.arranger import ArrangerIssuer
from pwm_hpl_ref.authority import AuthorityEngine, Constraint
from pwm_hpl_ref.crypto import generate_keypair
from pwm_hpl_ref.demo import build_fixture
from pwm_hpl_ref.departure import make_receipt
from pwm_hpl_ref.learning import learning_candidate
from pwm_hpl_ref.projection import ProjectionCompiler, ProjectionRequest
from pwm_hpl_ref.pwm import Materializer
from pwm_hpl_ref.web0 import issue_broadcast

ROOT=Path(__file__).parents[1]

def test_all_schemas_are_valid_draft_2020_12():
    for p in (ROOT/'schemas/json-schema').glob('*.json'):
        Draft202012Validator.check_schema(json.loads(p.read_text()))


def validate(schema_name, value):
    schema = json.loads((ROOT / "schemas/json-schema" / schema_name).read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def test_reference_runtime_outputs_validate_against_public_schemas():
    log, person = build_fixture()
    state = Materializer().materialize(log)
    for assertion in state.assertions.values():
        validate("pwm-assertion.schema.json", assertion)
    decision = AuthorityEngine().resolve(
        {"navigate.allowed_zone"},
        [Constraint(person, "ALLOW", frozenset({"navigate.allowed_zone"}), "PERSONAL")],
    )
    request = ProjectionRequest("delivery", "robot", ("delivery.preferred_surface",), tuple(decision.requested))
    projection = ProjectionCompiler().compile(state, request, decision)
    validate("projection-manifest.schema.json", projection)
    private, _ = generate_keypair()
    arranger = ArrangerIssuer().issue(private, person, "robot", "delivery", projection, ["CONTEXT"], projection["provenance"])
    validate("arranger-manifest.schema.json", arranger)
    candidate = learning_candidate("robot", {"subject": person}, {}, arranger["artifactId"], True)
    validate("learning-candidate.schema.json", candidate)
    validate("departure-receipt.schema.json", make_receipt("s", arranger["artifactId"], "robot", "UNVERIFIED", {}))
    validate("machine-broadcast.schema.json", issue_broadcast(private, "robot", "CAPABILITY", {"name": "delivery"}))
