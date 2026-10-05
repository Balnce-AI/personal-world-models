# Research And Implementation Status Taxonomy

The repository uses two independent status axes. Every significant specification, module, benchmark, adapter, and claim declares an evidence/implementation status. Versioned profiles and suites additionally declare a compatibility stability level.

## Evidence And Implementation

| Status | Meaning |
|---|---|
| `IMPLEMENTED` | Working code, exercised by automated tests, within the stated scope. |
| `REFERENCE_IMPLEMENTATION` | Working demonstration of a specification; not a production or safety guarantee. |
| `EXPERIMENTAL` | Working prototype under evaluation; interfaces may change. |
| `PROPOSED` | Normative design proposal not yet implemented end-to-end. |
| `RESEARCH` | Open technical/scientific question with an experiment or proof obligation. |
| `HYPOTHESIS` | Unvalidated claim whose falsifier is explicitly stated. |

A status is not a marketing maturity label. It describes evidence.

## Compatibility Stability

| Status | Meaning |
|---|---|
| `EXPERIMENTAL` | May change incompatibly; exact version pinning is required. |
| `PROVISIONAL` | Candidate interoperability contract with fixtures; breaking changes require a migration note and version change. |
| `STABLE` | Normative compatibility promise for the named major profile and conformance suite. |
| `DEPRECATED` | Still readable for a declared period; replacement and removal policy are required. |

An implemented reference can exercise a provisional profile. `IMPLEMENTED` does not mean `STABLE`, and `STABLE` does not imply a production deployment. Machine-readable component records may represent evidence and assurance as separate fields. Historical composite labels such as `EXPERIMENTAL_REAL` mean an experimental surface with executable evidence; new documents should use the two axes explicitly.
