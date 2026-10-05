from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


SOURCE_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "json-schema"
INSTALLED_SCHEMA_DIR = Path(sys.prefix) / "share" / "pwm-hpl-ref" / "schemas"


def schema_dir() -> Path:
    return SOURCE_SCHEMA_DIR if SOURCE_SCHEMA_DIR.exists() else INSTALLED_SCHEMA_DIR


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    directory = schema_dir()
    path = directory / schema_name
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    resources = []
    for schema_path in directory.glob("*.json"):
        candidate = json.loads(schema_path.read_text(encoding="utf-8"))
        if "$id" in candidate:
            resources.append((candidate["$id"], Resource.from_contents(candidate)))
    registry = Registry().with_resources(resources)
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


def validate_record(schema_name: str, value: dict[str, Any]) -> None:
    """Validate a public record at the runtime boundary."""
    _validator(schema_name).validate(value)
