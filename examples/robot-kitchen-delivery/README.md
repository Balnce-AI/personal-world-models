# Robot kitchen delivery — reference scenario

**Status:** REFERENCE_IMPLEMENTATION

Goal: deliver a sealed parcel from an entry point to an allowed kitchen surface while demonstrating that the recipient does not receive a sensitive private-zone assertion.

Pass conditions:
- required surface/accessibility context is present;
- private bedroom-zone assertion is absent;
- `map.export` is denied;
- Arranger signature verifies;
- departure receipt is explicitly only `PROTOCOL_DEPARTURE` unless stronger evidence exists.
