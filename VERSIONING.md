# Versioning And Stability

The repository release, normative profile, schema, ontology, conformance suite, language package, and extension versions advance independently. A repository tag does not silently change a published schema or protocol.

## Stability

| Level | Compatibility commitment |
|---|---|
| `EXPERIMENTAL` | May change incompatibly; must not be presented as interoperable without exact version pinning. |
| `PROVISIONAL` | Candidate interoperability contract with fixtures; breaking changes require a migration note and version change. |
| `STABLE` | Normative compatibility promise for the named major version and conformance suite. |
| `DEPRECATED` | Still readable for a declared period; replacement and removal policy required. |

## Version Axes

- Protocol/profile versions govern language-independent semantics and wire representations.
- JSON Schema IDs are immutable once marked `STABLE`; incompatible changes receive a new major schema URI.
- Ontology versions govern family definitions and constraints, not instance history.
- Conformance-suite versions pin fixtures and expected outcomes.
- SDK/package versions describe one implementation and do not redefine specifications.
- Extensions use independent semantic versions under an owned namespace.

Unknown normative event kinds, enum values, model families, and schema major versions fail closed. Additive optional fields require a profile that permits them; closed records do not accept undeclared fields. Experimental records may be migrated before stability, but migrations preserve source provenance and publish old/new schema identifiers.

See `spec/compatibility.md`, `spec/extensions-versioning.md`, `schemas/catalog.json`, and `conformance/manifest.json` for machine-facing details.
