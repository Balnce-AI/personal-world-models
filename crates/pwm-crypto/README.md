# pwm-crypto

`pwm-crypto` implements raw Ed25519 verification for event-body and append-receipt CID domains in the [public provenance profile](../../spec/public-provenance-profile-v1.md).

It rejects malformed, non-canonical, and weak public keys. It deliberately excludes production key custody, recovery, trust routing, operational policy, and private identity internals.

Run `cargo test -p pwm-crypto`.
