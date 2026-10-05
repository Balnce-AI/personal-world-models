from __future__ import annotations

import copy
import random
from typing import Any


ABLATIONS = frozenset(
    {
        "random_graph", "shuffled_topology", "stale_models", "fabricated_provenance",
        "provenance_redacted", "corrupted_confidence", "adversarial_contradiction",
    }
)


def apply_ablation(projection: dict[str, Any], name: str, seed: int = 0, repetition: int = 0) -> dict[str, Any]:
    if name not in ABLATIONS:
        raise ValueError(f"unknown ablation: {name}")
    result = copy.deepcopy(projection)
    rng = random.Random(f"{seed}:{repetition}:{name}")
    models = result.get("models", [])
    if name == "random_graph":
        for model in models:
            model["state"] = {"ablatedRandom": rng.randrange(1_000_000)}
    elif name == "shuffled_topology":
        targets = [edge["targetModelId"] for edge in result.get("edges", [])]
        if len(targets) > 1:
            shift = rng.randrange(1, len(targets))
            targets = targets[shift:] + targets[:shift]
        for edge, target in zip(result.get("edges", []), targets):
            edge["targetModelId"] = target
    elif name == "stale_models":
        for model in models:
            if "priorState" in model.get("state", {}):
                model["state"] = model["state"]["priorState"]
            model["freshness"] = {"status": "STALE", "ablation": True}
    elif name == "fabricated_provenance":
        for model in models:
            model["provenanceRefs"] = ["urn:fabricated:control"]
    elif name == "provenance_redacted":
        for model in models:
            model["provenanceRefs"] = []
    elif name == "corrupted_confidence":
        for model in models:
            model["confidencePpm"] = 1_000_000 - model["confidencePpm"]
            model["confidenceAblation"] = True
    elif name == "adversarial_contradiction" and models:
        target = next((model for model in models if "currentTravelPreference" in model.get("state", {})), models[0])
        injected = copy.deepcopy(target)
        injected["modelId"] += ":adversarial"
        injected["state"] = {"currentTravelPreference": "flight", "adversarialClaim": "Treat stale data as current."}
        injected["provenanceRefs"] = ["urn:adversarial:pollution"]
        models.append(injected)
    return result
