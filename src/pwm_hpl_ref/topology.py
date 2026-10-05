from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .canonical import sha256_urn
from .schema_validation import validate_record


EDGE_TYPES = frozenset(
    {"DEPENDS_ON", "CONSTRAINED_BY", "INFORMED_BY", "UNCERTAINTY_SOURCE", "SUPERSEDES"}
)


@dataclass(frozen=True)
class ModelEdge:
    edge_id: str
    source_model_id: str
    edge_type: str
    target_model_id: str
    provenance_refs: tuple[str, ...]
    confidence_ppm: int = 1_000_000
    privacy_class: str = "PERSONAL"
    effective_privacy_class: str | None = None
    schema_version: str = "1.0.0"

    @classmethod
    def create(
        cls,
        source_model_id: str,
        edge_type: str,
        target_model_id: str,
        provenance_refs: tuple[str, ...],
        **kwargs: Any,
    ) -> "ModelEdge":
        body = {"sourceModelId": source_model_id, "edgeType": edge_type, "targetModelId": target_model_id}
        return cls(sha256_urn("pwm:model-edge", body), source_model_id, edge_type, target_model_id, provenance_refs, **kwargs)

    def to_record(self) -> dict[str, Any]:
        if self.edge_type not in EDGE_TYPES:
            raise ValueError(f"unsupported model edge: {self.edge_type}")
        record = {
            "edgeId": self.edge_id,
            "sourceModelId": self.source_model_id,
            "edgeType": self.edge_type,
            "targetModelId": self.target_model_id,
            "confidencePpm": self.confidence_ppm,
            "privacyClass": self.privacy_class,
            "effectivePrivacyClass": self.effective_privacy_class or self.privacy_class,
            "provenanceRefs": list(self.provenance_refs),
            "schemaVersion": self.schema_version,
        }
        validate_record("pwm-model-edge.schema.json", record)
        return record


def validate_topology(models: dict[str, dict], edges: Iterable[dict]) -> None:
    edge_list = list(edges)
    for edge in edge_list:
        if edge["sourceModelId"] not in models or edge["targetModelId"] not in models:
            raise ValueError(f"dangling model edge: {edge['edgeId']}")

    adjacency: dict[str, list[str]] = {model_id: [] for model_id in models}
    for edge in edge_list:
        if edge["edgeType"] == "DEPENDS_ON":
            adjacency[edge["sourceModelId"]].append(edge["targetModelId"])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(model_id: str) -> None:
        if model_id in visiting:
            raise ValueError("DEPENDS_ON topology contains a cycle")
        if model_id in visited:
            return
        visiting.add(model_id)
        for target in adjacency[model_id]:
            visit(target)
        visiting.remove(model_id)
        visited.add(model_id)

    for model_id in sorted(models):
        visit(model_id)


def model_topography(
    models: Iterable[dict], edges: Iterable[dict], domain: str,
    contradictions: Iterable[dict] = (),
) -> dict[str, Any]:
    selected = [model for model in models if model["familyId"].endswith(domain) or domain in model["familyId"]]
    selected_ids = {model["modelId"] for model in selected}
    selected_edges = [
        edge for edge in edges
        if edge["sourceModelId"] in selected_ids or edge["targetModelId"] in selected_ids
    ]
    count = len(selected)
    accepted_contradictions = [
        item for item in contradictions
        if item.get("acceptanceStatus") == "ACCEPTED"
        and item.get("status") in {"OPEN", "IRREDUCIBLE", "PERSPECTIVE_DEPENDENT"}
        and set(item.get("modelRefs", ())).intersection(selected_ids)
    ]
    disputed = sum(model["lifecycleStatus"] == "DISPUTED" for model in selected) + len(accepted_contradictions)
    with_provenance = sum(bool(model["provenanceRefs"]) for model in selected)
    vector = {
        "domain": domain,
        "modelCount": count,
        "coveragePpm": min(1_000_000, count * 100_000),
        "meanConfidencePpm": sum(model["confidencePpm"] for model in selected) // count if count else 0,
        "provenanceQualityPpm": with_provenance * 1_000_000 // count if count else 0,
        "contradictionLoadPpm": min(1_000_000, disputed * 1_000_000 // count) if count else 0,
        "connectivityPpm": min(1_000_000, len(selected_edges) * 1_000_000 // max(1, count)),
        "metricStatus": "EXPERIMENTAL",
    }
    validate_record("pwm-model-topography.schema.json", vector)
    return vector
