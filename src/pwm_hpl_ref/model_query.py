from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from copy import deepcopy

from .canonical import sha256_urn
from .privacy import PRIVACY_ORDER, privacy_rank
from .pwm import PWMState
from .topology import validate_topology


@dataclass(frozen=True)
class ModelQuery:
    subjects: tuple[str, ...]
    model_families: tuple[str, ...] = ()
    valid_at: str | None = None
    min_confidence_ppm: int = 0
    include_disputed: bool = False
    max_privacy_class: str = "PERSONAL"
    include_provenance: bool = True
    include_topology: bool = True
    purpose: str = "research"
    recipient: str = "local:researcher"
    world_id: str = "world:actual"


@dataclass(frozen=True)
class ModelQueryAuthorization:
    authorization_ref: str
    purpose: str
    recipient: str
    max_privacy_class: str
    subjects: tuple[str, ...]
    world_id: str
    issued_at: str
    expires_at: str
    evaluated_at: str
    model_families: tuple[str, ...] = ()


def _active_at(model: dict[str, Any], valid_at: str | None) -> bool:
    if not valid_at or not model.get("validTime"):
        return True
    point = datetime.fromisoformat(valid_at.replace("Z", "+00:00"))
    interval = model["validTime"]
    start = interval.get("start")
    end = interval.get("end")
    return (not start or datetime.fromisoformat(start.replace("Z", "+00:00")) <= point) and (
        not end or point < datetime.fromisoformat(end.replace("Z", "+00:00"))
    )


def execute_query(state: PWMState, query: ModelQuery, authorization: ModelQueryAuthorization) -> dict[str, Any]:
    if not authorization.authorization_ref:
        raise ValueError("model query requires an authority reference")
    if (query.purpose, query.recipient) != (authorization.purpose, authorization.recipient):
        raise ValueError("model query is not bound to the authorized purpose and recipient")
    if not set(query.subjects).issubset(authorization.subjects):
        raise ValueError("model query requests an unauthorized subject")
    if authorization.world_id != query.world_id or authorization.world_id != state.world_id:
        raise ValueError("model query world is not authorized")
    issued = datetime.fromisoformat(authorization.issued_at.replace("Z", "+00:00"))
    expires = datetime.fromisoformat(authorization.expires_at.replace("Z", "+00:00"))
    evaluated = datetime.fromisoformat(authorization.evaluated_at.replace("Z", "+00:00"))
    if not issued <= evaluated < expires:
        raise ValueError("model query authorization is not temporally valid")
    query_privacy = privacy_rank(query.max_privacy_class)
    authorization_privacy = privacy_rank(authorization.max_privacy_class)
    if query_privacy > authorization_privacy:
        raise ValueError("model query exceeds its authorized privacy class")
    if authorization.model_families and not set(query.model_families).issubset(authorization.model_families):
        raise ValueError("model query requests an unauthorized model family")
    family_filter = query.model_families or authorization.model_families
    if not 0 <= query.min_confidence_ppm <= 1_000_000:
        raise ValueError("min_confidence_ppm must be between 0 and 1,000,000")
    privacy_limit = query_privacy
    models = []
    for model in state.models.values():
        if not set(query.subjects).intersection(model["subjectIds"]):
            continue
        if not set(model["subjectIds"]).issubset(authorization.subjects):
            continue
        if model["modelKind"] == "POSSIBLE_WORLD" and model["state"].get("worldId") != query.world_id:
            continue
        if family_filter and model["familyId"] not in family_filter:
            continue
        if model["confidencePpm"] < query.min_confidence_ppm:
            continue
        if model["lifecycleStatus"] not in ({"ACCEPTED", "DISPUTED"} if query.include_disputed else {"ACCEPTED"}):
            continue
        try:
            model_privacy = privacy_rank(model["effectivePrivacyClass"])
        except (KeyError, ValueError):
            continue
        if model_privacy > privacy_limit:
            continue
        if not _active_at(model, query.valid_at):
            continue
        item = deepcopy(model)
        qualifying_boundaries = [
            boundary for boundary in item.get("privacyBoundaries", ())
            if boundary.get("approved")
            and boundary.get("outputPrivacyClass") == model["effectivePrivacyClass"]
            and privacy_rank(boundary["inputPrivacyClass"]) > privacy_rank(boundary["outputPrivacyClass"])
        ]
        declassified = bool(qualifying_boundaries)
        if not query.include_provenance or declassified:
            item.pop("provenanceRefs", None)
            item.pop("derivationRefs", None)
            item.pop("dependencyRefs", None)
        if declassified:
            released_fields = {
                field for boundary in qualifying_boundaries
                for field in boundary.get("releasedFields", ())
            }
            item["state"] = {key: value for key, value in item["state"].items() if key in released_fields}
            item["privacyBoundaries"] = [
                {key: boundary[key] for key in ("boundaryId", "boundaryKind", "outputPrivacyClass", "releasedFields")}
                for boundary in qualifying_boundaries
            ]
        models.append(item)
    models.sort(key=lambda model: (model["familyId"], model["modelId"]))
    selected_ids = {model["modelId"] for model in models}
    edges = []
    if query.include_topology:
        edges = sorted(
            (
                deepcopy(edge) for edge in state.model_edges.values()
                if edge["sourceModelId"] in selected_ids and edge["targetModelId"] in selected_ids
                and edge.get("effectivePrivacyClass") in PRIVACY_ORDER
                and PRIVACY_ORDER[edge["effectivePrivacyClass"]] <= privacy_limit
            ),
            key=lambda edge: edge["edgeId"],
        )
        validate_topology(state.models, edges)
    contradictions = []
    for contradiction in state.contradictions.values():
        if (contradiction.get("acceptanceStatus") != "ACCEPTED"
            or contradiction.get("subjectId") not in query.subjects
            or not set(contradiction.get("modelRefs", ())).issubset(selected_ids)
            or contradiction.get("effectivePrivacyClass") not in PRIVACY_ORDER
            or PRIVACY_ORDER[contradiction["effectivePrivacyClass"]] > privacy_limit):
            continue
        item = deepcopy(contradiction)
        if not query.include_provenance:
            item.pop("provenanceRefs", None)
            item.pop("assertionRefs", None)
        contradictions.append(item)
    contradictions.sort(key=lambda item: item["contradictionId"])
    body = {
        "purpose": query.purpose,
        "recipient": query.recipient,
        "authorizationRef": authorization.authorization_ref,
        "validAt": query.valid_at,
        "query": {
            "subjects": list(query.subjects),
            "modelFamilies": list(query.model_families),
            "minConfidencePpm": query.min_confidence_ppm,
            "includeDisputed": query.include_disputed,
            "maxPrivacyClass": query.max_privacy_class,
            "includeProvenance": query.include_provenance,
            "includeTopology": query.include_topology,
        },
        "models": models,
        "edges": edges,
        "contradictions": contradictions,
    }
    return {"projectionId": sha256_urn("pwm:model-projection", body), **body}
