# Semantic Diff Format

Semantic diff compares two accepted normalized output envelopes or compares actual output with a suite expectation. It never compares diagnostic prose, JSON object-member order, whitespace, or source record order.

## Normalization

- Validate each output against `signed-semantic-output.schema.json` first.
- Sort object keys by UTF-8 bytes for display only.
- Preserve array order. Reducer outputs must already use the normative ordering for each array.
- Compare integers exactly. A JSON parser that rounds integers is unsuitable.
- Compare lowercase hexadecimal and CID text byte-for-byte; do not case-fold.
- Represent every CBOR byte string as exactly `{"$bytes_hex":"<lowercase hex>"}` before comparison.
- Compare absent and null as different values.

## Diff document

A diff document is a JSON object with exactly `format`, `equal`, and `differences`:

```json
{
  "format": "pwm-semantic-diff-v1",
  "equal": false,
  "differences": [
    {
      "path": "/result/models/0/status",
      "kind": "VALUE_MISMATCH",
      "expected": "ACCEPTED",
      "actual": "DISPUTED"
    }
  ]
}
```

Paths are RFC 6901 JSON Pointers. Kinds are `MISSING`, `UNEXPECTED`, `TYPE_MISMATCH`, `VALUE_MISMATCH`, and `ARRAY_ORDER_MISMATCH`. Differences sort by UTF-8 path bytes, then kind. `expected` is omitted for `UNEXPECTED`; `actual` is omitted for `MISSING`; both are present otherwise. `equal` is true exactly when `differences` is empty.

For rejected outputs, conformance comparison uses `decision` and `error.code`; implementations may compare `error.at_event_body_cid` when the expectation provides it. Human messages and private diagnostics are never conformance inputs.
