from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .schema_validation import validate_record


MODEL_FAMILY_STATUSES = frozenset(
    {"REFERENCE_IMPLEMENTATION", "EXPERIMENTAL", "PROPOSED", "RESEARCH"}
)


@dataclass(frozen=True)
class ModelFamily:
    family_id: str
    label: str
    scope: str
    status: str
    description: str
    source_refs: tuple[str, ...] = ()
    allowed_model_kinds: tuple[str, ...] = ("SELF", "OTHER", "RELATIONSHIP", "WORLD", "META", "POSSIBLE_WORLD")
    min_subjects: int = 1
    max_subjects: int | None = None
    perspective_rule: str = "ANY"
    requires_meta_target: bool = False
    requires_parent_world: bool = False
    required_state_fields: tuple[str, ...] = ()

    def to_record(self) -> dict:
        record = {
            "familyId": self.family_id,
            "label": self.label,
            "scope": self.scope,
            "status": self.status,
            "description": self.description,
            "sourceRefs": list(self.source_refs),
            "constraints": {
                "allowedModelKinds": list(self.allowed_model_kinds),
                "subjectCardinality": {"min": self.min_subjects, "max": self.max_subjects},
                "perspectiveRule": self.perspective_rule,
                "requiresMetaTarget": self.requires_meta_target,
                "requiresParentWorld": self.requires_parent_world,
                "requiredStateFields": list(self.required_state_fields),
            },
        }
        validate_record("pwm-model-family.schema.json", record)
        return record


class ModelRegistry:
    def __init__(self, families: Iterable[ModelFamily] = ()):
        self._families: dict[str, ModelFamily] = {}
        for family in families:
            self.register(family)

    def register(self, family: ModelFamily) -> None:
        if family.status not in MODEL_FAMILY_STATUSES:
            raise ValueError(f"unsupported family status: {family.status}")
        if family.family_id in self._families:
            raise ValueError(f"duplicate model family: {family.family_id}")
        if family.max_subjects is not None and family.max_subjects < family.min_subjects:
            raise ValueError("model family maximum subjects cannot be less than its minimum")
        family.to_record()
        self._families[family.family_id] = family

    def get(self, family_id: str) -> ModelFamily:
        try:
            return self._families[family_id]
        except KeyError as exc:
            raise KeyError(f"unknown model family: {family_id}") from exc

    def records(self) -> list[dict]:
        return [self._families[key].to_record() for key in sorted(self._families)]

    def validate_model(self, model: dict[str, Any], resolvable_model_ids: Iterable[str] = ()) -> None:
        family = self.get(model["familyId"])
        kind = model["modelKind"]
        subjects = model["subjectIds"]
        perspective = model["perspective"]
        if kind not in family.allowed_model_kinds:
            raise ValueError(f"{family.family_id} does not allow model kind {kind}")
        if len(subjects) != len(set(subjects)) or len(subjects) < family.min_subjects:
            raise ValueError(f"{family.family_id} subject cardinality is invalid")
        if family.max_subjects is not None and len(subjects) > family.max_subjects:
            raise ValueError(f"{family.family_id} subject cardinality is invalid")
        if kind == "RELATIONSHIP" and len(set(subjects)) < 2:
            raise ValueError("RELATIONSHIP models require at least two distinct subjects")
        if kind == "OTHER" and perspective in subjects:
            raise ValueError("OTHER model perspective must be distinct from modeled subjects")
        if kind == "SELF" and perspective not in subjects:
            raise ValueError("SELF model perspective must be one of its subjects")
        if family.perspective_rule == "SUBJECT" and perspective not in subjects:
            raise ValueError(f"{family.family_id} requires a subject perspective")
        if family.perspective_rule == "OUTSIDE_SUBJECT" and perspective in subjects:
            raise ValueError(f"{family.family_id} requires an outside perspective")
        missing = set(family.required_state_fields) - model["state"].keys()
        if missing:
            raise ValueError(f"{family.family_id} is missing required state fields: {sorted(missing)}")
        if kind == "META" and family.requires_meta_target:
            target = model["state"].get("targetModelId")
            if not target or target not in set(resolvable_model_ids) or target not in model.get("dependencyRefs", []):
                raise ValueError("META model requires a resolvable, consistent targetModelId")
        if kind == "POSSIBLE_WORLD" and not model["state"].get("parentWorldId"):
            raise ValueError("POSSIBLE_WORLD model requires parentWorldId")
        if kind == "POSSIBLE_WORLD" and model["state"].get("worldId") == model["state"].get("parentWorldId"):
            raise ValueError("POSSIBLE_WORLD model must not identify its parent as itself")
        if kind == "POSSIBLE_WORLD" and model["state"].get("privacyClass") != model.get("privacyClass"):
            raise ValueError("POSSIBLE_WORLD state privacy must match model privacy")

    def to_record(self, ontology_version: str = "1.0.0-experimental") -> dict:
        record = {"ontologyVersion": ontology_version, "families": self.records()}
        validate_record("pwm-model-registry.schema.json", record)
        return record


def default_registry() -> ModelRegistry:
    fc = (
        "embodied", "spatial", "action-capability", "goals", "cognitive",
        "informational-epistemic", "affective", "social", "meta", "ethical",
    )
    native = (
        "identity-persona", "relationship", "temporal-life-trajectory",
        "economic-resources", "professional-work", "health-wellness",
        "digital-life", "physical-environment", "institutional",
        "ownership-assets", "commitments-obligations", "permissions-authority",
        "imagination-possible-worlds", "other-mind", "organization", "machine-agent",
        "group-social-field", "trust", "risk", "accessibility", "preference",
        "narrative", "predictive", "models-of-models",
    )
    special = {
        "fc.embodied": dict(allowed_model_kinds=("SELF",)),
        "fc.spatial": dict(allowed_model_kinds=("SELF", "WORLD")),
        "fc.action-capability": dict(allowed_model_kinds=("SELF", "OTHER")),
        "fc.goals": dict(allowed_model_kinds=("SELF", "OTHER")),
        "fc.cognitive": dict(allowed_model_kinds=("SELF", "OTHER")),
        "fc.informational-epistemic": dict(allowed_model_kinds=("SELF", "OTHER", "META")),
        "fc.affective": dict(allowed_model_kinds=("SELF", "OTHER")),
        "fc.social": dict(allowed_model_kinds=("SELF", "OTHER", "RELATIONSHIP")),
        "fc.meta": dict(allowed_model_kinds=("META",), requires_meta_target=True,
                         required_state_fields=("targetModelId",)),
        "fc.ethical": dict(allowed_model_kinds=("SELF", "OTHER", "META")),
        "pwm.identity-persona": dict(allowed_model_kinds=("SELF", "OTHER")),
        "pwm.relationship": dict(allowed_model_kinds=("RELATIONSHIP",), min_subjects=2),
        "pwm.temporal-life-trajectory": dict(allowed_model_kinds=("SELF", "OTHER", "WORLD")),
        "pwm.economic-resources": dict(allowed_model_kinds=("SELF", "OTHER", "WORLD")),
        "pwm.professional-work": dict(allowed_model_kinds=("SELF", "OTHER", "RELATIONSHIP")),
        "pwm.health-wellness": dict(allowed_model_kinds=("SELF", "OTHER")),
        "pwm.digital-life": dict(allowed_model_kinds=("SELF", "OTHER", "WORLD")),
        "pwm.physical-environment": dict(allowed_model_kinds=("WORLD",)),
        "pwm.institutional": dict(allowed_model_kinds=("WORLD", "OTHER")),
        "pwm.ownership-assets": dict(allowed_model_kinds=("SELF", "WORLD", "RELATIONSHIP")),
        "pwm.commitments-obligations": dict(allowed_model_kinds=("SELF", "RELATIONSHIP")),
        "pwm.permissions-authority": dict(allowed_model_kinds=("SELF", "OTHER", "RELATIONSHIP", "META")),
        "pwm.models-of-models": dict(allowed_model_kinds=("META",), requires_meta_target=True,
                                     required_state_fields=("targetModelId",)),
        "pwm.other-mind": dict(allowed_model_kinds=("OTHER",), perspective_rule="OUTSIDE_SUBJECT"),
        "pwm.organization": dict(allowed_model_kinds=("OTHER", "WORLD")),
        "pwm.machine-agent": dict(allowed_model_kinds=("OTHER", "WORLD")),
        "pwm.group-social-field": dict(allowed_model_kinds=("RELATIONSHIP", "WORLD")),
        "pwm.trust": dict(allowed_model_kinds=("RELATIONSHIP",), min_subjects=2),
        "pwm.risk": dict(allowed_model_kinds=("META", "WORLD")),
        "pwm.accessibility": dict(allowed_model_kinds=("SELF", "RELATIONSHIP", "WORLD")),
        "pwm.preference": dict(allowed_model_kinds=("SELF", "OTHER")),
        "pwm.narrative": dict(allowed_model_kinds=("SELF", "OTHER", "RELATIONSHIP")),
        "pwm.predictive": dict(allowed_model_kinds=("META",)),
        "pwm.imagination-possible-worlds": dict(allowed_model_kinds=("POSSIBLE_WORLD",),
                                                requires_parent_world=True,
                                                required_state_fields=("worldId", "parentWorldId", "baseStateId",
                                                                       "baseTime", "privacyClass")),
    }
    general_kinds = ("SELF", "OTHER", "RELATIONSHIP", "WORLD")
    families = [
        ModelFamily(
            f"fc.{name}",
            name.replace("-", " ").title(),
            "SELF_COMPATIBILITY_PROFILE",
            "RESEARCH",
            "Seed family imported for Functional Consciousness compatibility research.",
            ("profiles/functional-consciousness/provenance.md",),
            **special.get(f"fc.{name}", {"allowed_model_kinds": general_kinds}),
        )
        for name in fc
    ]
    families.extend(
        ModelFamily(
            f"pwm.{name}",
            name.replace("-", " ").title(),
            "PWM_MODEL_ECOLOGY",
            "EXPERIMENTAL",
            "PWM-native experimental family; not a claim of ontology completeness.",
            ("spec/self-models.md",),
            **special.get(f"pwm.{name}", {"allowed_model_kinds": general_kinds}),
        )
        for name in native
    )
    return ModelRegistry(families)
