from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .canonical import sha256_urn
from .schema_validation import validate_record
from .self_models import ModelRecord, utc_now


@dataclass(frozen=True)
class DerivationResult:
    model: ModelRecord
    record: dict[str, Any]


def derive_numeric_capability(
    assertions: Iterable[dict[str, Any]],
    *,
    subject_id: str,
    evidence_predicate: str,
    family_id: str,
    output_key: str,
    lower_bound: Callable[[list[int]], int] = min,
    upper_bound: Callable[[list[int]], int] = max,
    record_time: str | None = None,
) -> DerivationResult:
    """A deterministic example derivation; it creates a candidate, never accepted state."""
    evidence = sorted(
        (
            item for item in assertions
            if item.get("subject") == subject_id
            and item.get("predicate") == evidence_predicate
            and isinstance(item.get("object"), int)
            and item.get("epistemicStatus") not in {"REVOKED", "SUPERSEDED"}
        ),
        key=lambda item: item["id"],
    )
    if not evidence:
        raise ValueError("numeric capability derivation requires matching evidence")
    values = [item["object"] for item in evidence]
    evidence_refs = tuple(item["id"] for item in evidence)
    now = record_time or utc_now()
    model = ModelRecord.create(
        model_kind="SELF",
        family_id=family_id,
        subject_ids=(subject_id,),
        perspective=subject_id,
        state={output_key: {"lower": lower_bound(values), "upper": upper_bound(values)}},
        epistemic_status="INFERRED",
        confidence_ppm=min(900_000, 400_000 + len(values) * 100_000),
        uncertainty={"kind": "sample-range", "sampleCount": len(values)},
        provenance_refs=evidence_refs,
        record_time=now,
    )
    body = {
        "method": "deterministic.numeric-sample-range",
        "methodVersion": "1.0.0",
        "evidenceRefs": list(evidence_refs),
        "candidateModelId": model.model_id,
        "parameters": {"predicate": evidence_predicate, "outputKey": output_key},
        "createdAt": now,
        "status": "CANDIDATE",
    }
    record = {"derivationId": sha256_urn("pwm:model-derivation", body), **body}
    validate_record("pwm-model-derivation.schema.json", record)
    return DerivationResult(model, record)
