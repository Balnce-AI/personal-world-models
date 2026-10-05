# Personal World Model Specifications

This directory contains the normative interoperability text for the public Personal World Model (PWM) and Human Projection Layer (HPL). The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described by RFC 2119 and RFC 8174 when, and only when, they appear in all capitals.

## Normative and reference material

Normative requirements are statements in this directory that use the key words above, together with the JSON Schemas and suite declarations identified as `NORMATIVE` in `schemas/catalog.json` and `conformance/manifest.json`. Examples, diagrams, implementation code, test runners, explanatory notes, and documents under `docs/` are non-normative reference material unless a normative document explicitly incorporates a named artifact.

If prose and a normative schema conflict, the prose defines semantic behavior and the schema defines the accepted JSON shape. The conflict is a specification defect and an implementation MUST NOT silently choose an interpretation when reporting conformance.

`spec/public-provenance-profile-v1.md` and the unchanged `conformance/vectors/wave01-*.json` files remain authoritative for the `pwm-public-provenance-v1` canonical-CBOR profile. The semantic vectors introduced by `conformance/manifest.json` use `pwm-json-semantics-v1`; they do not redefine Wave01 encoding, signatures, CIDs, or receipts.

## Specification map

- `pwm-core.md`: PWM concepts and base invariants.
- `compatibility.md`: independent version axes and compatibility rules.
- `extensions-versioning.md`: namespaces, extensions, and stability transitions.
- `conformance-levels.md`: staged feature levels and suite IDs.
- `hpl-core.md`: projection boundary and lifecycle invariants.
- `conformance/README.md`: language-neutral evidence procedure.

No document in this repository implies conformance merely because an implementation can parse its examples. Conformance requires an explicit implementation claim and evidence for every required suite at the claimed level.
