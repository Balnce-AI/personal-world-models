# Portability Guide

PWM/HPL portability means preserving observable semantics across implementations, not sharing a database layout, programming language, or internal graph engine.

A portable export SHOULD identify the specification, schema, event/profile, suite, extension, and implementation versions separately. It SHOULD carry provenance, valid and record times, lifecycle state, privacy class, world scope, contradiction links, topology edges, and authority bindings whenever those concepts apply.

Importers MUST reject unsupported major versions and required extensions. Unknown optional extension data may be retained opaquely only when it cannot affect authorization, privacy, provenance, topology, or signatures. A namespace is not an identity or authority grant.

Wave01 portability is byte-sensitive and follows `pwm-public-provenance-v1`. Semantic fixture portability follows `pwm-json-semantics-v1` and compares outcomes rather than native storage representation. Translators SHOULD be deterministic and SHOULD disclose any information loss. A lossy translation MUST NOT claim round-trip preservation.

Private UOR/PLOG, storage, inference, and policy internals are outside the public interface. Implementations can differ internally while remaining portable if they satisfy the same declared profile and conformance invariants.
