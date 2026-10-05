# Conformance Guide

The normative levels are defined in `spec/conformance-levels.md`; this guide is explanatory.

1. Select one level and record the exact specification version.
2. Run every suite listed for that level in `conformance/manifest.json` using the declared suite version.
3. Preserve Wave01 as canonical-CBOR evidence. Do not convert its byte-level acceptance criteria into ordinary JSON comparisons.
4. For semantic vectors, document any adapter from `pwm-json-semantics-v1` events to native records and compare every stated outcome and invariant.
5. Publish per-case results, fixture digests, environment, implementation version, and supported extension manifests.
6. Label incomplete evidence as partial testing, not conformance.

Schema validation proves only structural validity. A conforming implementation also enforces temporal, lifecycle, contradiction, topology, privacy, world-isolation, and authorization semantics. The repository manifest intentionally contains no current implementation claims.
