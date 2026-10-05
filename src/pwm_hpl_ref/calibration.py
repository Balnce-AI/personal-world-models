from __future__ import annotations

from typing import Any, Iterable

from .canonical import sha256_urn
from .schema_validation import validate_record


def binary_calibration_record(
    predictions: Iterable[dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
    *,
    evaluated_at: str,
    procedure_ref: str = "pwm.calibration.binary-brier.v1",
) -> dict[str, Any]:
    pairs = []
    squared_error_sum = 0
    for prediction in sorted(predictions, key=lambda value: value["predictionId"]):
        outcome = outcomes.get(prediction["predictionId"])
        if outcome is None or not isinstance(prediction["predictedValue"], bool):
            continue
        observed_ppm = 1_000_000 if outcome["observedValue"] is prediction["predictedValue"] else 0
        error = prediction["probabilityPpm"] - observed_ppm
        squared_error_sum += error * error
        pairs.append({"predictionId": prediction["predictionId"], "outcomeId": outcome["outcomeId"]})
    if not pairs:
        raise ValueError("calibration requires at least one resolved binary prediction")
    brier_ppm = squared_error_sum // len(pairs) // 1_000_000
    body = {
        "metric": "BRIER_BINARY",
        "metricValuePpm": brier_ppm,
        "sampleCount": len(pairs),
        "pairs": pairs,
        "evaluatedAt": evaluated_at,
        "procedureRef": procedure_ref,
        "metricStatus": "EXPERIMENTAL",
        "schemaVersion": "1.0.0",
    }
    record = {"calibrationId": sha256_urn("pwm:calibration", body), **body}
    validate_record("pwm-calibration-record.schema.json", record)
    return record
