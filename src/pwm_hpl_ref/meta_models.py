from __future__ import annotations

from typing import Any

from .self_models import ModelRecord


def model_quality_candidate(
    *,
    subject_id: str,
    target_model_id: str,
    quality_kind: str,
    assessment: dict[str, Any],
    confidence_ppm: int,
    provenance_refs: tuple[str, ...],
    record_time: str | None = None,
) -> ModelRecord:
    """Create an inspectable candidate about another model's quality or limits."""
    return ModelRecord.create(
        model_kind="META",
        family_id="fc.meta",
        subject_ids=(subject_id,),
        perspective=subject_id,
        state={"qualityKind": quality_kind, "targetModelId": target_model_id, **assessment},
        epistemic_status="INFERRED",
        confidence_ppm=confidence_ppm,
        uncertainty={"kind": "assessment", "targetModelId": target_model_id},
        provenance_refs=provenance_refs,
        dependency_refs=(target_model_id,),
        record_time=record_time,
    )
