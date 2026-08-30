# V1 File Ledger

**Status:** `IMPLEMENTED` forensic migration record

## Scope

- Archive tag: `public-v1-archive`
- Archive commit: `363fe941b6c71a0235b8479a33ea7a7286e7dbe2`
- Current archive tree: 97 files
- Initial published corpus commit: `a83ccf2f133dbf90611cbb636a1e42f10b35c5df`
- Current-plus-historical union: 116 files

The latest founder-approved public HEAD is the V1 archive baseline. Files removed before that commit remain `HISTORY_ONLY`; this ledger does not republish ignored local copies. `DELETE` means removal from the active V2 tree, never destruction of Git history.

## Counts

| Disposition | Files |
|---|---:|
| `KEEP` | 2 |
| `PORT` | 30 |
| `REWRITE` | 64 |
| `DELETE` | 0 |
| `HISTORY_ONLY` | 20 |

## File Dispositions

| Path | Archive | Initial corpus | Disposition | Rationale |
|---|:---:|:---:|---|---|
| `.github/workflows/test.yml` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `.gitignore` | yes | yes | `KEEP` | Retain unchanged as repository hygiene or licensing foundation, subject to normal review. |
| `CONTRIBUTING.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `CURRENT_STATE_AUDIT.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `EXECUTION_PLAN.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `GAP_ANALYSIS.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `IMPLEMENTATION_GRAPH.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `LICENSE` | yes | yes | `KEEP` | Retain unchanged as repository hygiene or licensing foundation, subject to normal review. |
| `PUBLIC_RELEASE_PLAN.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `README.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `ROADMAP.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `SECURITY.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `STATUS.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `adapters/covesa-vss/README.md` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `adapters/covesa-vss/adapter.py` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `adapters/hcp/README.md` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `adapters/hcp/adapter.py` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `adapters/mhs/README.md` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `adapters/ros2/README.md` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `adapters/sovd/README.md` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `adapters/wot/README.md` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `adapters/wot/adapter.py` | yes | yes | `PORT` | Retain boundary research where useful, but rebuild against pinned upstream versions and V2 contracts. |
| `architecture/adrs/0001-pwm-materialized-over-provenance.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `architecture/adrs/0002-arranger-is-artifact-hyperframe-is-carrier.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `architecture/adrs/0003-no-canonical-pwm-on-foreign-infra.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `architecture/adrs/0004-five-rung-crystallization.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `architecture/adrs/0005-hpl-not-safety-kernel.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `architecture/adrs/0006-departure-assurance.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `architecture/adrs/0007-standards-as-adapters.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `architecture/adrs/0008-uhr-name-protected.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `architecture/adrs/0009-edge-twin-extended-not-duplicated.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `benchmarks/README.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `benchmarks/hpl-context/run.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `benchmarks/results/hpl-context-smoke.txt` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/exports/multi-principal.svg` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/exports/projection-lifecycle.svg` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/exports/sovereign-grid.svg` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/exports/system-context.svg` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/01-system-context.mmd` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/02-projection-lifecycle.mmd` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/03-standards-map.mmd` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/04-multi-principal.mmd` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/05-learning-return.mmd` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/06-sovereign-grid.mmd` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/multi-principal.dot` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/projection-lifecycle.dot` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/sovereign-grid.dot` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `diagrams/source/system-context.dot` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `docs/GLOSSARY.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `examples/fleet-authority-conflict/README.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `examples/generated/demo-output.json` | yes | yes | `HISTORY_ONLY` | Nondeterministic generated V1 output; replace with reproducible signed result artifacts. |
| `examples/robot-kitchen-delivery/README.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `examples/vehicle-service-support/README.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `math/authority-algebra.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `math/confidence-and-time.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `math/projection-operator.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `math/pwm-formal-model.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `math/uor-proof-status.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `papers/01-personal-world-model/README.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `papers/02-human-projection-layer/README.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `pyproject.toml` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `research/evidence-ledger/README.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `research/evidence-ledger/seed.json` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `research/landscape/CLAIM_MATRIX.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `research/landscape/COMPETITOR_MAP.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `research/open-questions/README.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `research/prior-art/README.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `research/terminology-provenance/README.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `rfcs/0001-pwm-core-profile.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `rfcs/0002-hpl-projection-profile.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/arranger-manifest.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/authority-constraint.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/departure-receipt.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/learning-candidate.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/machine-broadcast.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/plog-event.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/projection-manifest.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/pwm-assertion.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/pwm-entity.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/json-schema/pwm-relation.schema.json` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `schemas/typescript/index.ts` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `security/THREAT_MODEL.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `security/TRUST_ASSUMPTIONS.md` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `site/AI_LAB_PAGE.md` | no | yes | `HISTORY_ONLY` | Explicitly removed from the current public branch before reconstruction; retain only in Git history unless separately adjudicated. |
| `spec/arranger.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `spec/departure-assurance.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `spec/hpl-core.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `spec/multi-principal-governance.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `spec/projection-lifecycle.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `spec/public-interface-profile.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `spec/pwm-core.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `spec/spatial-projection.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `src/pwm_hpl_ref/__init__.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/arranger.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/authority.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/canonical.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/crypto.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/demo.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/departure.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/learning.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/plog.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/projection.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/pwm.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `src/pwm_hpl_ref/web0.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `standards/README.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `standards/covesa-mapping.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `standards/hcp-mapping.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `standards/mhs-mapping.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `standards/ros2-mapping.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `standards/wot-mapping.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `tests/test_adapters.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `tests/test_markdown_math.py` | yes | no | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `tests/test_reference.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `tests/test_schemas.py` | yes | yes | `REWRITE` | Replace or substantially revise for the V2 architecture, evidence bar, and reproducibility contract. |
| `vision/category-thesis.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |
| `vision/ten-principles.md` | yes | yes | `PORT` | Preserve reviewed concepts and non-claims while translating them into the V2 contract and status system. |

## Machine-Readable Source

The authoritative machine-readable form is [`migration/v1_file_ledger.json`](v1_file_ledger.json).
