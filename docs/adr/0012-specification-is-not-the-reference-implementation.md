# ADR 0012: Specification Is Not The Reference Implementation

**Status:** `PROPOSED`

## Context
Independent Rust, TypeScript, Swift, Kotlin, C++, Zig, browser, and embedded implementations must not reverse-engineer Python behavior.

## Decision
Normative semantics live in `spec/`, public schemas, and conformance vectors. Rust and Python code are implementations with separately declared status. A behavior present only in implementation is not normative.

## Alternatives
Treating Python or Rust source as the specification was rejected.

## Consequences
Compatibility claims cite profile and suite versions. Experimental implementation behavior may change without changing stable protocols.
