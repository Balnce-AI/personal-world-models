# Independent Implementation Guide

This guide is non-normative. Normative behavior is in the four signed-semantic specifications.

## Minimal architecture

Keep five boundaries visible in code:

1. A strict JSON suite loader that does not perform semantic evaluation.
2. A Wave01 verifier that returns immutable verified records, receipt sequence, and canonical payload bytes.
3. A semantic decoder that accepts only the five-member payload envelope and registered data maps.
4. A pure reducer receiving `(state, verified_record, authenticated_principal)` and returning either a new state or one stable error.
5. A command adapter that reads final state and emits a normalized output envelope, including the state digest on both acceptance and rejection.

Use arbitrary-precision or checked 64-bit integer APIs as required by the restricted CBOR profile. Do not pass nanoseconds, sequences, fixed-point coefficients, or scales through floating-point JSON APIs. Compare CIDs using decoded raw bytes and compare set-like payload arrays using canonical item CBOR.

## Command adapter contract

The adapter entry point is conceptually:

```text
evaluate(source: SignedSemanticSource) -> SignedSemanticOutput
```

It MUST be deterministic, side-effect free with respect to semantic state, and support exactly:

- `REDUCE`: return normalized complete reducer state.
- `QUERY`: execute the command's query object and return selected models and induced authorized edges.
- `PROJECT`: resolve the named HPL projection and return only its metadata, released field paths, and content digest; projection content is out of band.
- `EVALUATE`: return the named conformance evaluation record.

An adapter may use internal types, databases, or event buses, but the conformance invocation MUST begin from empty state and the supplied source only. Network, wall clock, locale, random values, and retained state from another case are forbidden inputs. `evaluation_log_sequence` is explicit in the command.

## Recommended implementation order

1. Pass standalone Wave01 valid and invalid vectors.
2. Decode the exact semantic payload and reject floats, unknown members, and non-normalized sets/fixed point.
3. Implement immutable trust-anchor bootstrap and grant lookup by receipt sequence.
4. Implement model lifecycle and retained history.
5. Add privacy, contradiction, topology, possible worlds, and query selection.
6. Add HPL request/authorization/projection/revocation.
7. Normalize output and run semantic diff.

For rejection, collect internal diagnostics if useful but select the public code by the normative precedence table. Never short-circuit on a later semantic error before all earlier cryptographic stages that are necessary to establish trusted input.

## Test isolation

Run every suite case in a fresh process or fresh store. Verify that rejection leaves the pre-event state digest unchanged. Include tests where one record contains both a bad signature and bad semantic reference; the expected result is cryptographic. Include grant boundary cases at exactly `valid_from_log_sequence` and `valid_to_log_sequence`.
