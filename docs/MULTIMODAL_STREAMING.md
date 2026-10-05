# Multimodal streaming

Status: `PROPOSED` architecture with `EXPERIMENTAL` Python value types.

## Reference, not blob

PWM events store a `MultimodalReference`: content-addressed or otherwise integrity-bound URI, media type, digest, provenance references, privacy segment and optional byte range/capture time. Audio, image, video, telemetry and embeddings remain in a declared external substrate. A URI alone is insufficient evidence.

## Streaming boundary

```text
device frames -> bounded ephemeral window -> evidence adapter
                                      | discard
                                      | authorized promote
                                      v
                            EventDraft -> public EventSink
```

A `StreamWindow` is not durable merely because it was observed, cached or inferred over. Durable promotion requires explicit authorization, a provenance-bearing event, a stable reference and retention/privacy policy. Models may return candidates; they cannot promote them implicitly.

Backpressure must bound window count, bytes, duration and inference concurrency. Dropped frames are represented as gaps rather than fabricated continuity. Replayed windows retain source sequence and are deduplicated. Raw sensor streams never imply actuator authority.

## Privacy and lifecycle

Minimize before storage; separate privacy segments; redact derived thumbnails/transcripts independently; revoke references and keys where supported; and report when external deletion is unverifiable. Consumers check digest, media limits, parser safety, provenance closure, authorization freshness and declared semantics before decoding.
