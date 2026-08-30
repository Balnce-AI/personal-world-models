# pwm-canonical

`pwm-canonical` implements the restricted deterministic CBOR and typed CID portions of the [public provenance profile](../../spec/public-provenance-profile-v1.md).

The crate accepts only the profile's bounded value model, rejects non-canonical input, and creates domain-separated CIDv1 raw SHA-256 identifiers. It does not implement UOR or private production identifiers.

Run `cargo test -p pwm-canonical`. Golden, malformed, resource-limit, property, and typed-CID tests are in `tests/`.
