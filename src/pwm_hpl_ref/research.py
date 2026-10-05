from __future__ import annotations

import copy
import importlib.metadata
import json
import random
import subprocess
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .ablation import ABLATIONS, apply_ablation
from .canonical import canonical_json, sha256_urn
from .foundation_models import (
    DeterministicByteTokenizer,
    InferenceResult,
    ModelProjection,
    ReasoningModel,
    SYSTEM_PROMPT_TEMPLATE,
    Task,
    TokenizerAdapter,
    render_prompt,
)
from .model_query import ModelQuery, ModelQueryAuthorization, execute_query
from .model_registry import default_registry
from .plog import PLog
from .projection import PRIVACY_ORDER
from .pwm import Materializer, PWMState
from .self_models import ModelLifecycle, ModelRecord
from .schema_validation import schema_dir
from .topology import ModelEdge


CONDITIONS = (
    "no_memory", "flat_memory", "retrieval", "pwm", "pwm+self_models", "pwm+self_meta",
    "stateless", "transcript", "flat_normalized_source_facts", "retrieval_raw",
    "retrieval_normalized", "structured_assertions", "flat_derived",
    "flat_information_matched", "structured_information_matched",
    "structured_model_ecology", "structured_model_ecology_meta", "shuffled_topology",
    "provenance_redacted", "stale", "corrupt", "adversarial",
)

CANONICAL_CONDITIONS = (
    "stateless", "transcript", "flat_normalized_source_facts", "retrieval_raw",
    "retrieval_normalized", "structured_assertions", "flat_derived",
    "flat_information_matched", "structured_information_matched",
    "structured_model_ecology", "structured_model_ecology_meta", "shuffled_topology",
    "provenance_redacted", "stale", "corrupt", "adversarial",
)

CONDITION_ALIASES = {
    "no_memory": "stateless",
    "flat_memory": "transcript",
    "retrieval": "retrieval_raw",
    "pwm": "structured_assertions",
    "pwm+self_models": "structured_model_ecology",
    "pwm+self_meta": "structured_model_ecology_meta",
    "stale_models": "stale",
    "corrupted_confidence": "corrupt",
    "adversarial_contradiction": "adversarial",
    "fabricated_provenance": "provenance_fabricated",
    "random_graph": "random_graph",
}

CONDITION_TAXONOMY = {
    "stateless": ("none", "none", "none", "baseline"),
    "transcript": ("transcript", "all", "source", "baseline"),
    "flat_normalized_source_facts": ("flat", "all", "normalized", "representation"),
    "retrieval_raw": ("transcript", "retrieval", "source", "selection"),
    "retrieval_normalized": ("flat", "retrieval", "normalized", "selection"),
    "structured_assertions": ("structured-assertions", "all", "normalized", "representation"),
    "flat_derived": ("flat", "all", "derived", "derivation"),
    "structured_model_ecology": ("model-ecology", "all", "derived", "derivation"),
    "flat_information_matched": ("flat-information-units", "all", "derived", "representation"),
    "structured_information_matched": ("grouped-information-units", "all", "derived", "representation"),
    "structured_model_ecology_meta": ("model-ecology-meta", "all", "meta-derived", "derivation"),
    "shuffled_topology": ("model-ecology-meta", "all", "meta-derived", "topology"),
    "provenance_redacted": ("model-ecology-meta", "all", "meta-derived", "provenance"),
    "provenance_fabricated": ("model-ecology-meta", "all", "meta-derived", "provenance"),
    "stale": ("model-ecology-meta", "all", "stale-derived", "freshness"),
    "corrupt": ("model-ecology-meta", "all", "corrupt-derived", "confidence"),
    "adversarial": ("model-ecology-meta", "all", "adversarial-derived", "evidence"),
    "random_graph": ("model-ecology-meta", "all", "random-derived", "structure"),
}

EXPECTED_CONTROL_DIRECTION = {
    "baseline": "REFERENCE",
    "representation": "EQUIVALENT_INFORMATION",
    "selection": "LESS_OR_EQUAL_INFORMATION",
    "derivation": "ADDITIONAL_DERIVED_INFORMATION",
    "topology": "NON_POSITIVE",
    "provenance": "NON_POSITIVE",
    "freshness": "NON_POSITIVE",
    "confidence": "NON_POSITIVE",
    "evidence": "NON_POSITIVE",
    "structure": "NON_POSITIVE",
}


@dataclass(frozen=True)
class InformationUnit:
    unit_id: str
    role: str
    value_hash: str
    source_refs: tuple[str, ...]
    derivation_status: str
    privacy_class: str
    value: Any

    @classmethod
    def create(
        cls,
        unit_id: str,
        role: str,
        value: Any,
        source_refs: Iterable[str],
        derivation_status: str,
        privacy_class: str = "PERSONAL",
    ) -> InformationUnit:
        return cls(
            unit_id, role, sha256_urn("pwm:information-value", value),
            tuple(sorted(source_refs)), derivation_status, privacy_class, copy.deepcopy(value),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "unitId": self.unit_id,
            "role": self.role,
            "valueHash": self.value_hash,
            "sourceRefs": list(self.source_refs),
            "derivationStatus": self.derivation_status,
            "privacyClass": self.privacy_class,
            "value": self.value,
        }


class InformationLedger:
    def __init__(self, units: Iterable[InformationUnit] = ()):
        self.units = tuple(sorted(units, key=lambda unit: unit.unit_id))

    @property
    def signature(self) -> str:
        return sha256_urn("pwm:information-signature", [unit.to_record() for unit in self.units])

    def to_record(self) -> dict[str, Any]:
        return {"signature": self.signature, "units": [unit.to_record() for unit in self.units]}


class FixtureControlModel:
    """Deterministic plumbing control, not a model-capability benchmark."""

    model_id = "fixture-control-v1"
    experiment_parameters = {"adapter": "deterministic-fixture", "temperature": 0}
    tokenizer = DeterministicByteTokenizer()

    def infer(self, task: Task, context: ModelProjection, tools=None) -> InferenceResult:
        knowledge = dict(context.content.get("knowledge", {}))
        for fact in context.content.get("facts", []):
            knowledge[fact["predicate"]] = fact["value"]
        for memory in context.content.get("memories", []):
            assertion = memory["assertion"]
            knowledge[assertion["predicate"]] = assertion["object"]
        unit_groups = [context.content.get("informationUnits", [])]
        unit_groups.extend(context.content.get("informationByRole", {}).values())
        for units in unit_groups:
            for unit in units:
                value = unit.get("value")
                if isinstance(value, dict) and "predicate" in value and "value" in value:
                    knowledge[value["predicate"]] = value["value"]
        answer = {key: knowledge.get(key) for key in task.expected_keys}
        confidence = 900_000 if all(value is not None for value in answer.values()) else 100_000
        return InferenceResult(answer, self.model_id, confidence_ppm=confidence)


def load_persona(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def materialize_persona(persona: dict[str, Any]) -> tuple[PWMState, list[dict[str, Any]]]:
    log = PLog(clock=lambda: "2026-10-01T00:00:00+00:00")
    actor = persona["personaId"]
    raw = persona["evidence"]
    evidence_events = {}
    for item in raw:
        event = log.append("assertion.put", item["assertion"], actor, record_time=item["assertion"]["recordTime"])
        evidence_events[item["assertion"]["id"]] = event.event_id
    lifecycle = ModelLifecycle(default_registry())
    accepted: dict[str, ModelRecord] = {}
    for source in persona["models"]:
        state_value = copy.deepcopy(source["state"])
        dependency_refs = tuple(source.get("dependencyRefs", ()))
        if source["modelKind"] == "META" and source.get("targetModel"):
            target_id = accepted[source["targetModel"]].model_id
            state_value["targetModelId"] = target_id
            dependency_refs = tuple(sorted(set(dependency_refs + (target_id,))))
        model = ModelRecord.create(
            model_kind=source["modelKind"], family_id=source["familyId"], subject_ids=tuple(source["subjectIds"]),
            perspective=source["perspective"], state=state_value, epistemic_status=source["epistemicStatus"],
            confidence_ppm=source["confidencePpm"], uncertainty=source["uncertainty"],
            provenance_refs=tuple(evidence_events[ref] for ref in source["provenanceRefs"]), record_time=source["recordTime"],
            dependency_refs=dependency_refs, valid_time=source.get("validTime"), freshness=source.get("freshness"),
            privacy_class=source.get("privacyClass", "PERSONAL"),
        )
        proposal = lifecycle.propose(log, model, source.get("proposedBy", actor))
        lifecycle.accept(log, model, actor, proposal)
        accepted[source["name"]] = replace(model, lifecycle_status="ACCEPTED", provenance_refs=tuple(sorted(set(model.provenance_refs + (proposal.event_id,)))))
    for source in persona.get("edges", []):
        edge = ModelEdge.create(
            accepted[source["source"]].model_id, source["edgeType"], accepted[source["target"]].model_id,
            tuple(evidence_events[ref] for ref in source["provenanceRefs"]),
        )
        log.append("model.edge.put", edge.to_record(), actor)
    return Materializer().materialize(log), raw


def _assertions(state: PWMState, max_privacy_class: str) -> list[dict[str, Any]]:
    limit = PRIVACY_ORDER[max_privacy_class]
    return [
        assertion for assertion in sorted(state.assertions.values(), key=lambda item: (item["recordTime"], item["id"]))
        if assertion["epistemicStatus"] not in {"REVOKED", "SUPERSEDED", "DISPUTED"}
        and PRIVACY_ORDER.get(assertion.get("privacyClass", "PERSONAL"), PRIVACY_ORDER["HIGHLY_SENSITIVE"]) <= limit
    ]


def _assertion_knowledge(state: PWMState, max_privacy_class: str = "PERSONAL") -> dict[str, Any]:
    return {item["predicate"]: item["object"] for item in _assertions(state, max_privacy_class)}


def _model_knowledge(models: list[dict[str, Any]], include_meta: bool) -> dict[str, Any]:
    values = {}
    for model in models:
        if model["modelKind"] == "META" and not include_meta:
            continue
        if model["confidencePpm"] < 500_000 or not model["provenanceRefs"]:
            continue
        values.update(model["state"])
    return values


def _topology_knowledge(models: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {model["modelId"]: model for model in models}
    constrained = []
    for edge in edges:
        source = by_id.get(edge["sourceModelId"])
        target = by_id.get(edge["targetModelId"])
        if source and target and source["familyId"] == "fc.goals" and edge["edgeType"] == "CONSTRAINED_BY":
            constrained.append(target["familyId"])
    return {"goalConstraintFamilies": sorted(constrained)} if constrained else {}


def _source_ledger(items: Iterable[dict[str, Any]], status: str) -> InformationLedger:
    units = []
    for item in items:
        assertion = item["assertion"] if "assertion" in item else item
        units.append(InformationUnit.create(
            f"assertion:{assertion['id']}", "SOURCE_FACT", {"predicate": assertion["predicate"], "value": assertion["object"]},
            assertion.get("provenance", ()), status, assertion.get("privacyClass", "PERSONAL"),
        ))
    return InformationLedger(units)


def _derived_ledger(
    assertions: list[dict[str, Any]], models: list[dict[str, Any]], edges: list[dict[str, Any]], include_meta: bool,
) -> InformationLedger:
    units = list(_source_ledger(assertions, "NORMALIZED").units)
    for model in models:
        if model["modelKind"] == "META" and not include_meta:
            continue
        status = "ADVERSARIAL" if model["modelId"].endswith(":adversarial") else "STALE" if (model.get("freshness") or {}).get("status") == "STALE" else "CORRUPT" if model.get("confidenceAblation") else "REDACTED" if not model.get("provenanceRefs") else "DERIVED"
        for key, value in sorted(model.get("state", {}).items()):
            if key == "priorState":
                continue
            units.append(InformationUnit.create(
                f"model:{model['modelId']}:{key}", "META" if model["modelKind"] == "META" else "DERIVED_FACT",
                {"predicate": key, "value": value}, model.get("provenanceRefs", ()), status, model.get("privacyClass", "PERSONAL"),
            ))
        units.append(InformationUnit.create(
            f"model:{model['modelId']}:confidence", "META", model["confidencePpm"], model.get("provenanceRefs", ()), status,
            model.get("privacyClass", "PERSONAL"),
        ))
    for edge in edges:
        units.append(InformationUnit.create(
            f"edge:{edge['edgeId']}", "TOPOLOGY", {key: edge[key] for key in ("sourceModelId", "edgeType", "targetModelId")},
            edge.get("provenanceRefs", ()), "DERIVED",
        ))
    return InformationLedger(units)


def _query_projection(state: PWMState, persona_id: str, task: dict[str, Any]) -> dict[str, Any]:
    privacy_class = task.get("maxPrivacyClass", "PERSONAL")
    query = ModelQuery((persona_id,), include_disputed=True, max_privacy_class=privacy_class)
    authorization = ModelQueryAuthorization(
        authorization_ref=f"fixture-authorization:{task['taskId']}", purpose=query.purpose, recipient=query.recipient,
        max_privacy_class=privacy_class,
        subjects=tuple(task.get("authorizedSubjects", (persona_id,))),
        world_id=state.world_id,
        issued_at="2026-01-01T00:00:00+00:00",
        expires_at="2027-01-01T00:00:00+00:00",
        evaluated_at="2026-10-01T00:00:00+00:00",
    )
    return execute_query(state, query, authorization)


def _with_provenance(state: PWMState, projection: dict[str, Any], knowledge: dict[str, Any]) -> dict[str, Any]:
    referenced_events = {ref for model in projection["models"] for ref in model["provenanceRefs"]}
    for ref in tuple(referenced_events):
        event_payload = state.applied_event_payloads.get(ref, {})
        referenced_events.update(event_payload.get("provenanceRefs", []))
        if event_payload.get("proposalEventId"):
            referenced_events.add(event_payload["proposalEventId"])
    return {
        **projection,
        "knowledge": knowledge,
        "provenance": {model["modelId"]: model["provenanceRefs"] for model in projection["models"]},
        "provenanceEvents": {
            event_id: {"eventType": state.applied_event_types[event_id], "payload": state.applied_event_payloads[event_id]}
            for event_id in sorted(referenced_events) if event_id in state.applied_event_types
        },
    }


def build_condition(
    condition: str,
    state: PWMState,
    raw_evidence: list[dict[str, Any]],
    persona_id: str,
    task: dict[str, Any],
    *,
    seed: int = 0,
    repetition: int = 0,
) -> ModelProjection:
    if condition not in CONDITIONS and condition not in ABLATIONS:
        raise ValueError(f"unknown research condition: {condition}")
    canonical = CONDITION_ALIASES.get(condition, condition)
    control_applicable: bool | None = None
    privacy_class = task.get("maxPrivacyClass", "PERSONAL")
    assertions = _assertions(state, privacy_class)
    selected_raw = [
        item for item in raw_evidence
        if PRIVACY_ORDER.get(item["assertion"].get("privacyClass", "PERSONAL"), PRIVACY_ORDER["HIGHLY_SENSITIVE"])
        <= PRIVACY_ORDER[privacy_class]
    ]
    if canonical in {"retrieval_raw", "retrieval_normalized"}:
        terms = set(task["queryTerms"])
        selected_raw = [item for item in selected_raw if terms.intersection(item["text"].lower().split())]
    if canonical == "stateless":
        content, ledger = {"knowledge": {}, "provenance": {}}, InformationLedger()
    elif canonical in {"transcript", "retrieval_raw"}:
        content, ledger = {"knowledge": {}, "memories": copy.deepcopy(selected_raw), "provenance": {}}, _source_ledger(selected_raw, "SOURCE")
    elif canonical in {"flat_normalized_source_facts", "retrieval_normalized", "structured_assertions"}:
        selected = assertions if canonical != "retrieval_normalized" else [item["assertion"] for item in selected_raw]
        knowledge = {item["predicate"]: item["object"] for item in selected}
        content = {"knowledge": knowledge, "provenance": {}} if canonical == "structured_assertions" else {
            "facts": [{"predicate": key, "value": value} for key, value in sorted(knowledge.items())], "provenance": {}
        }
        ledger = _source_ledger(selected, "NORMALIZED")
    else:
        projection = _query_projection(state, persona_id, task)
        ablation_name = {
            "shuffled_topology": "shuffled_topology", "provenance_redacted": "provenance_redacted",
            "provenance_fabricated": "fabricated_provenance", "stale": "stale_models", "corrupt": "corrupted_confidence",
            "adversarial": "adversarial_contradiction", "random_graph": "random_graph",
        }.get(canonical)
        if ablation_name:
            control_applicable = (
                len(projection.get("edges", [])) > 1
                if ablation_name == "shuffled_topology" else True
            )
            projection = apply_ablation(projection, ablation_name, seed, repetition)
        include_meta = canonical not in {"structured_model_ecology", "flat_derived"}
        if not include_meta:
            retained_ids = {model["modelId"] for model in projection["models"] if model["modelKind"] != "META"}
            projection["models"] = [model for model in projection["models"] if model["modelId"] in retained_ids]
            projection["edges"] = [edge for edge in projection["edges"] if edge["sourceModelId"] in retained_ids and edge["targetModelId"] in retained_ids]
        knowledge = {
            **_assertion_knowledge(state, privacy_class),
            **_model_knowledge(projection["models"], include_meta),
            **_topology_knowledge(projection["models"], projection["edges"]),
        }
        ledger = _derived_ledger(assertions, projection["models"], projection["edges"], include_meta)
        if canonical in {"flat_information_matched", "structured_information_matched"}:
            records = ledger.to_record()["units"]
            if canonical == "flat_information_matched":
                content = {"informationUnits": records}
            else:
                grouped: dict[str, list[dict[str, Any]]] = {}
                for record in records:
                    grouped.setdefault(record["role"], []).append(record)
                content = {"informationByRole": grouped}
        elif canonical == "flat_derived":
            content = {"facts": [{"predicate": key, "value": value} for key, value in sorted(knowledge.items())], "provenance": {}}
        else:
            content = _with_provenance(state, projection, knowledge)
    return ModelProjection(
        condition, content, content.get("projectionId"),
        information_ledger=ledger.units, control_applicable=control_applicable,
    )


def _taxonomy(condition: str) -> dict[str, str]:
    canonical = CONDITION_ALIASES.get(condition, condition)
    representation, selection, derivation, experiment = CONDITION_TAXONOMY[canonical]
    return {"canonicalCondition": canonical, "representation": representation, "selection": selection, "derivation": derivation, "experimentClass": experiment}


def _ledger(projection: ModelProjection) -> InformationLedger:
    return InformationLedger(InformationUnit(
        item["unitId"], item["role"], item["valueHash"], tuple(item["sourceRefs"]),
        item["derivationStatus"], item["privacyClass"], item["value"]
    ) if isinstance(item, dict) else item for item in projection.information_ledger)


def _scan_canaries(value: Any, canaries: Iterable[str]) -> list[str]:
    serialized = canonical_json(value).decode("utf-8").casefold()
    return sorted({canary for canary in canaries if canary.casefold() in serialized})


def score_result(task: dict[str, Any], result: InferenceResult, projection: ModelProjection, rendered_input: str = "") -> dict[str, Any]:
    output = result.output if isinstance(result.output, dict) else {}
    required = task["expected"]
    correct = sum(output.get(key) == value for key, value in required.items())
    canaries = tuple(task.get("prohibitedDisclosureKeys", ())) + tuple(task.get("leakageCanaries", ()))
    input_leaks = _scan_canaries(rendered_input, canaries)
    output_leaks = _scan_canaries({"output": result.output, "raw": result.raw, "usage": result.usage, "candidates": result.candidates}, canaries)
    provenance_values = projection.content.get("provenance", {}).values()
    events = projection.content.get("provenanceEvents", {})
    provenance_total = sum(1 for _ in provenance_values)
    provenance_valid = 0
    for model_id, refs in projection.content.get("provenance", {}).items():
        proposals = [ref for ref in refs if events.get(ref, {}).get("eventType") == "model.proposed" and events[ref]["payload"].get("modelId") == model_id]
        if len(proposals) == 1:
            evidence_refs = events[proposals[0]]["payload"].get("provenanceRefs", [])
            if evidence_refs and all(events.get(ref, {}).get("eventType") == "assertion.put" for ref in evidence_refs):
                provenance_valid += 1
    return {
        "correctPpm": correct * 1_000_000 // max(1, len(required)),
        "inputCanaryHitCount": len(input_leaks),
        "outputCanaryHitCount": len(output_leaks),
        "inputLeakageCanaries": input_leaks,
        "outputLeakageCanaries": output_leaks,
        "provenanceCoveragePpm": provenance_valid * 1_000_000 // max(1, provenance_total),
        "contextBytes": len(canonical_json(projection.content)),
        "calibrationErrorPpm": abs((result.confidence_ppm if result.confidence_ppm is not None else 500_000) - (correct * 1_000_000 // max(1, len(required)))),
    }


def _tokenizer_for(model: ReasoningModel, tokenizer: TokenizerAdapter | None) -> TokenizerAdapter | None:
    return tokenizer if tokenizer is not None else getattr(model, "tokenizer", None)


def _match_token_budgets(
    task: Task, projections: list[ModelProjection], model_id: str, tokenizer: TokenizerAdapter | None,
) -> tuple[list[ModelProjection], list[dict[str, Any]], list[str]]:
    natural_prompts = [render_prompt(task, projection, model_id) for projection in projections]
    if tokenizer is None:
        records = [{"tokenizerId": "provider-opaque", "exact": False, "verified": False, "paddingToken": None, "naturalTokenCount": None, "paddingTokenCount": 0, "finalTokenCount": None, "targetTokenCount": None} for _ in projections]
        return projections, records, natural_prompts
    natural = [tokenizer.count(prompt) for prompt in natural_prompts]
    if not tokenizer.exact or not getattr(tokenizer, "verified", False) or not tokenizer.padding_token or tokenizer.count(tokenizer.padding_token) != 1:
        records = [{"tokenizerId": tokenizer.tokenizer_id, "exact": tokenizer.exact, "verified": False, "paddingToken": None, "naturalTokenCount": count, "paddingTokenCount": 0, "finalTokenCount": count, "targetTokenCount": None} for count in natural]
        return projections, records, natural_prompts
    target = max(natural)
    matched, records, prompts = [], [], []
    for projection, count in zip(projections, natural):
        padding_count = target - count
        padded = replace(projection, padding=tokenizer.padding_token * padding_count)
        prompt = render_prompt(task, padded, model_id)
        final = tokenizer.count(prompt)
        if final != target:
            raise AssertionError(f"token matching failed for {projection.condition}: {final} != {target}")
        matched.append(padded)
        prompts.append(prompt)
        records.append({"tokenizerId": tokenizer.tokenizer_id, "exact": True, "verified": True, "paddingToken": tokenizer.padding_token, "naturalTokenCount": count, "paddingTokenCount": padding_count, "finalTokenCount": final, "targetTokenCount": target})
    return matched, records, prompts


def generate_coverage(corpus_path: Path, persona_paths: Iterable[Path]) -> dict[str, Any]:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    personas = [load_persona(path) for path in sorted(persona_paths)]
    registry_ids = {record["familyId"] for record in default_registry().records()}
    task_links = {}
    for persona in personas:
        for task in persona.get("tasks", []):
            for scenario_id in task.get("scenarioIds", []):
                task_links.setdefault(scenario_id, []).append(f"{persona['personaId']}:{task['taskId']}")
    scenarios = []
    classifications = corpus["pmraClassification"]["scenarios"]
    for scenario in corpus["scenarios"]:
        classification = classifications[scenario["id"]]
        family_ids = sorted(classification["modelFamilies"])
        links = sorted(task_links.get(scenario["id"], []))
        coverage_status = (
            "EXECUTABLE" if links and scenario["executionStatus"] == "IMPLEMENTED"
            else "TASK_LINKED" if links
            else "CORPUS_ONLY"
        )
        scenarios.append({
            "scenarioId": scenario["id"],
            "categoryId": classification["categoryId"],
            "modelKinds": classification["modelKinds"],
            "primitiveProfileId": classification["primitiveProfileId"],
            "taskRefs": links,
            "registeredFamilyIds": sorted(set(family_ids) & registry_ids),
            "unregisteredFamilyIds": sorted(set(family_ids) - registry_ids),
            "coverageStatus": coverage_status,
            "declaredExecutionStatus": scenario["executionStatus"],
        })
    body = {
        "schemaVersion": "1.0.0",
        "scenarioCount": len(scenarios),
        "taskCount": sum(len(persona.get("tasks", [])) for persona in personas),
        "scenarioTaskLinkCount": sum(len(item["taskRefs"]) for item in scenarios),
        "scenarios": scenarios,
    }
    return {**body, "coverageHash": sha256_urn("pwm:scenario-coverage", body)}


def run_experiment(
    persona_path: Path,
    model: ReasoningModel,
    *,
    conditions: tuple[str, ...] = CONDITIONS + tuple(sorted(ABLATIONS)),
    seed: int = 0,
    repetitions: int = 1,
    tokenizer: TokenizerAdapter | None = None,
) -> dict[str, Any]:
    if repetitions < 1:
        raise ValueError("repetitions must be at least one")
    conditions = tuple(dict.fromkeys(conditions))
    persona = load_persona(persona_path)
    if not persona.get("tasks"):
        raise ValueError(f"persona has no executable tasks: {persona['personaId']}")
    state, raw = materialize_persona(persona)
    selected_tokenizer = _tokenizer_for(model, tokenizer)
    runs_by_key: dict[tuple[str, int], list[dict[str, Any]]] = {(condition, repetition): [] for repetition in range(repetitions) for condition in conditions}
    failures = []
    for repetition in range(repetitions):
        condition_order = list(conditions)
        random.Random(seed + repetition).shuffle(condition_order)
        for task_data in persona["tasks"]:
            task = Task(task_data["taskId"], task_data["instruction"], tuple(task_data["expected"]))
            projections = [build_condition(condition, state, raw, persona["personaId"], task_data, seed=seed, repetition=repetition) for condition in condition_order]
            projections, budgets, prompts = _match_token_budgets(task, projections, model.model_id, selected_tokenizer)
            for condition, projection, budget, prompt in zip(condition_order, projections, budgets, prompts):
                try:
                    result = model.infer(task, projection)
                    metrics = score_result(task_data, result, projection, prompt)
                    failure = None
                except Exception as exc:  # Preserve failed cells in the experiment manifest.
                    result = InferenceResult({}, model.model_id)
                    metrics = score_result(task_data, result, projection, prompt)
                    failure = {"condition": condition, "repetition": repetition, "taskId": task.task_id, "errorType": type(exc).__name__, "message": str(exc)}
                    failures.append(failure)
                provider_tokens = result.usage.get("prompt_tokens", result.usage.get("input_tokens"))
                budget = {
                    **budget,
                    "providerPromptTokenCount": provider_tokens,
                    "providerTokenTolerance": 0,
                    "providerCountAgreement": (
                        None if provider_tokens is None or budget["finalTokenCount"] is None
                        else abs(provider_tokens - budget["finalTokenCount"]) <= 0
                    ),
                }
                runs_by_key[(condition, repetition)].append({
                    "taskId": task.task_id,
                    "scenarioIds": task_data.get("scenarioIds", []),
                    "counterfactual": task_data.get("counterfactual"),
                    "output": result.output,
                    "usage": result.usage,
                    "informationSignature": _ledger(projection).signature,
                    "informationLedger": _ledger(projection).to_record(),
                    "tokenBudget": budget,
                    "controlApplicable": projection.control_applicable,
                    "failure": failure,
                    **metrics,
                })
    runs = []
    for repetition in range(repetitions):
        for condition in conditions:
            task_metrics = runs_by_key[(condition, repetition)]
            taxonomy = _taxonomy(condition)
            provider_agreements = [
                item["tokenBudget"]["providerCountAgreement"] for item in task_metrics
                if item["tokenBudget"]["providerCountAgreement"] is not None
            ]
            local_token_match = bool(
                selected_tokenizer and selected_tokenizer.exact
                and getattr(selected_tokenizer, "verified", False)
            )
            runs.append({
                "condition": condition,
                "repetition": repetition,
                "scenarioIds": sorted({scenario for item in task_metrics for scenario in item["scenarioIds"]}),
                "conditionTaxonomy": taxonomy,
                "expectedControlDirection": EXPECTED_CONTROL_DIRECTION[taxonomy["experimentClass"]],
                "informationSignatures": sorted({item["informationSignature"] for item in task_metrics}),
                "tokenizerId": selected_tokenizer.tokenizer_id if selected_tokenizer else "provider-opaque",
                "tokenMatchingVerified": local_token_match and all(provider_agreements),
                "localTokenMatchingVerified": local_token_match,
                "providerTokenMatchingVerified": all(provider_agreements) if provider_agreements else None,
                "taskCount": len(task_metrics),
                "metrics": {
                    "correctPpm": sum(item["correctPpm"] for item in task_metrics) // len(task_metrics),
                    "inputCanaryHitCount": sum(item["inputCanaryHitCount"] for item in task_metrics),
                    "outputCanaryHitCount": sum(item["outputCanaryHitCount"] for item in task_metrics),
                    "provenanceCoveragePpm": sum(item["provenanceCoveragePpm"] for item in task_metrics) // len(task_metrics),
                    "contextBytes": sum(item["contextBytes"] for item in task_metrics) // len(task_metrics),
                    "calibrationErrorPpm": sum(item["calibrationErrorPpm"] for item in task_metrics) // len(task_metrics),
                },
                "tasks": task_metrics,
            })
    dataset_hash = sha256_urn("pwm:dataset", persona)
    package_dir = Path(__file__).parent
    source_root = package_dir.parents[1]
    implementation_inputs = {
        **{f"python/{path.name}": path.read_text(encoding="utf-8") for path in sorted(package_dir.glob("*.py"))},
        **{f"schema/{path.name}": path.read_text(encoding="utf-8") for path in sorted(schema_dir().glob("*.json"))},
        "dataset/persona.json": persona_path.read_text(encoding="utf-8"),
    }
    pyproject = source_root / "pyproject.toml"
    if pyproject.is_file():
        implementation_inputs["package/pyproject.toml"] = pyproject.read_text(encoding="utf-8")
    implementation_hash = sha256_urn("pwm:research-implementation", implementation_inputs)
    execution_root = Path.cwd()
    try:
        git_commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=execution_root).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        git_commit = "unavailable"
    try:
        git_dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True, cwd=execution_root).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        git_dirty = True
    prompt_hash = sha256_urn("pwm:prompt-profile", SYSTEM_PROMPT_TEMPLATE)
    model_parameters = getattr(model, "experiment_parameters", {"adapter": type(model).__name__})
    tokenizer_record = {
        "tokenizerId": selected_tokenizer.tokenizer_id if selected_tokenizer else "provider-opaque",
        "revision": getattr(selected_tokenizer, "revision", "unknown") if selected_tokenizer else "unknown",
        "chatTemplateHash": getattr(selected_tokenizer, "chat_template_hash", prompt_hash) if selected_tokenizer else prompt_hash,
        "exact": bool(selected_tokenizer and selected_tokenizer.exact),
        "verified": bool(selected_tokenizer and selected_tokenizer.exact and getattr(selected_tokenizer, "verified", False)),
        "providerTokenTolerance": 0,
    }
    experiment_identity = {"dataset": dataset_hash, "model": model.model_id, "seed": seed, "repetitions": repetitions, "conditions": list(conditions), "promptProfileHash": prompt_hash, "implementationHash": implementation_hash, "modelParameters": model_parameters, "tokenizer": tokenizer_record}
    return {
        "experimentId": sha256_urn("pwm:experiment", experiment_identity),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "gitCommit": git_commit,
        "gitDirty": git_dirty,
        "implementationHash": implementation_hash,
        "datasetHash": dataset_hash,
        "ontologyVersion": "pwm-model-registry-1.0.0-experimental",
        "foundationModel": model.model_id,
        "promptProfileHash": prompt_hash,
        "evaluatorVersion": "exact-key-rubric-v2",
        "modelParameters": model_parameters,
        "dependencyVersions": {name: importlib.metadata.version(name) for name in ("cryptography", "jsonschema")},
        "seed": seed,
        "repetitions": repetitions,
        "tokenizer": tokenizer_record,
        "conditionTaxonomy": {condition: _taxonomy(condition) for condition in conditions},
        "scenarioIds": sorted({scenario for task in persona["tasks"] for scenario in task.get("scenarioIds", [])}),
        "runs": runs,
        "failures": failures,
        "metricStatus": "EXPERIMENTAL",
        "limitations": [
            "The fixture control validates experimental plumbing; it is not evidence of foundation-model cognitive gain.",
            "Scores are scenario-rubric measurements and are not consciousness or psychometric measures.",
            "Opaque provider tokenizers are not reported as exact unless a verified adapter is supplied.",
            "Canary-hit counts detect declared literal disclosures only; they are not semantic privacy-leakage estimates.",
        ],
        "artifacts": [str(persona_path.resolve().relative_to(execution_root.resolve())) if persona_path.resolve().is_relative_to(execution_root.resolve()) else persona_path.name],
    }


def write_result(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
