# Compatibility and Version Axes

## Independent axes

An implementation MUST identify these axes independently:

1. **Specification version**: the semantic requirements being implemented.
2. **Schema version**: the JSON shape of one artifact type.
3. **Event/profile version**: canonicalization, signing, replay, and event semantics.
4. **Conformance-suite version**: the immutable set of tests and vectors used as evidence.
5. **Extension version**: the contract of one namespaced extension.
6. **Implementation version**: the release of a particular product or library.

A version on one axis MUST NOT be used as evidence of compatibility on another. In particular, JSON `schemaVersion: "1.0.0"` does not imply support for `pwm-public-provenance-v1`, and passing a semantic JSON suite does not imply canonical-CBOR interoperability.

Versions use Semantic Versioning `MAJOR.MINOR.PATCH`. A major change may be incompatible. A minor change adds backward-compatible behavior. A patch change clarifies or repairs behavior without changing accepted semantics. Extension and implementation versions MAY use prerelease identifiers and compare them according to Semantic Versioning. Published normative specification and conformance-suite versions MUST use release versions so fixture schemas and prose accept the same version language.

## Compatibility rules

- A consumer MUST reject an unsupported major version.
- A consumer MAY accept a newer minor version only when the governing schema permits unknown members or the extension contract defines their handling.
- A consumer MUST NOT discard an unknown member and then attest that the original object was preserved or authorized.
- Producers MUST emit one declared version for each relevant axis and MUST NOT infer an event profile from a filename or transport media type alone.
- Replay MUST pin the event profile, schema set, conflict policy, privacy ordering, and extension set. Changing any pin creates a distinct materialization.
- Suite IDs and vector case IDs are stable identifiers. Published suite contents MUST NOT be changed in place; corrections require a new suite version and SHOULD retain supersession metadata.

## V1 profiles

`pwm-public-provenance-v1` is the Wave01 canonical-CBOR provenance profile. Its authoritative fixtures are `conformance/vectors/wave01-valid.json` and `conformance/vectors/wave01-invalid.json`.

`pwm-json-semantics-v1` is defined by `pwm-json-semantics-v1.md` as a language-neutral JSON representation for semantic conformance inputs and expected outcomes. It is not a signed event serialization. Implementations MAY translate these fixtures into native records, but evidence MUST document the adapter and MUST compare the resulting semantics, not byte identity.
