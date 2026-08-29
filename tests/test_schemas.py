import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).parents[1]

def test_all_schemas_are_valid_draft_2020_12():
    for p in (ROOT/'schemas/json-schema').glob('*.json'):
        Draft202012Validator.check_schema(json.loads(p.read_text()))
