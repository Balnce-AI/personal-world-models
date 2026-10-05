# Schema Catalog

`catalog.json` is the language-independent index of public JSON Schemas. `NORMATIVE` entries define interchange or conformance envelope shapes. `REFERENCE` entries describe objects emitted or consumed by the reference implementation and do not, by themselves, standardize runtime internals.

All schemas use JSON Schema Draft 2020-12. Consumers SHOULD resolve a schema by its `$id` and MUST reject an unsupported major schema version. A catalog entry does not make an implementation conformant; see `conformance/manifest.json`.

The schemas under `conformance/schemas/` are cataloged here even though they are stored with the fixtures. This keeps the suite self-contained while preserving one discovery index.
