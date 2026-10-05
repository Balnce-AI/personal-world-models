# PWM Model Requirement Analysis

**Status:** `PROPOSED` method

PMRA asks which distinctions, variables, relationships, temporal context, perspectives, uncertainty, and authority evidence are minimally required for a scenario. The normalized table in `experiments/scenarios/corpus.json` maps all 25 scenarios to controlled category IDs, model-family IDs, model kinds, and primitive profiles. Model family answers "what domain is modeled"; model kind answers "whose or what level of model is represented." They are not interchangeable.

Every primitive profile has seven independent dimensions:

- `architectural`: state shape and computational organization.
- `evidence`: admissible observations or records.
- `authority`: who may decide or act; capability is not authority.
- `query`: selection and projection semantics.
- `policy`: disclosure and action constraints.
- `evaluation`: observable scoring criteria.
- `topology`: relations among models, facts, agents, or possible worlds.

Scenario records retain raw evidence, rubrics, leakage constraints, uncertainty, action constraints, and counterfactual variants. Executable persona tasks add `scenarioIds` plus a counterfactual declaration containing exactly the changed variables and invariants. `pwm-research coverage` derives coverage from the scenario corpus, persona tasks, and model registry; checked coverage is generated rather than manually scored.

Promotion from scenario requirement to registry family requires a distinct semantic role, evidence and falsifiers, a versioned schema, privacy analysis, and an executable test. Similar labels alone do not justify ontology growth.

The PMRA table is a research classification, not evidence that every listed family is necessary. Necessity requires matched ablation evidence, and unregistered family IDs remain visible in generated coverage rather than being silently treated as implemented.
