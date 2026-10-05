from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import sha256_urn
from .schema_validation import validate_record


@dataclass(frozen=True)
class Prediction:
    prediction_id: str
    subject_id: str
    predicate: str
    predicted_value: Any
    probability_ppm: int
    target_time: str
    record_time: str
    model_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    privacy_class: str = "PERSONAL"
    schema_version: str = "1.0.0"

    @classmethod
    def create(cls, **values: Any) -> "Prediction":
        identity = dict(values)
        return cls(prediction_id=sha256_urn("pwm:prediction", identity), **values)

    def to_record(self) -> dict[str, Any]:
        record = {
            "predictionId": self.prediction_id,
            "subjectId": self.subject_id,
            "predicate": self.predicate,
            "predictedValue": self.predicted_value,
            "probabilityPpm": self.probability_ppm,
            "targetTime": self.target_time,
            "recordTime": self.record_time,
            "modelRefs": list(self.model_refs),
            "provenanceRefs": list(self.provenance_refs),
            "privacyClass": self.privacy_class,
            "schemaVersion": self.schema_version,
            "status": "OPEN",
        }
        validate_record("pwm-prediction.schema.json", record)
        return record


def resolve_prediction(
    prediction: dict[str, Any], observed_value: Any, outcome_time: str, provenance_refs: tuple[str, ...]
) -> dict[str, Any]:
    body = {
        "predictionId": prediction["predictionId"],
        "observedValue": observed_value,
        "outcomeTime": outcome_time,
        "provenanceRefs": list(provenance_refs),
        "schemaVersion": "1.0.0",
    }
    record = {"outcomeId": sha256_urn("pwm:prediction-outcome", body), **body}
    validate_record("pwm-prediction-outcome.schema.json", record)
    return record
