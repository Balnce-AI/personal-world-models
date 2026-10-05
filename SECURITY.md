# Security policy

The code and protocols in this repository are experimental/reference artifacts. They are not a safety-certified control system, production identity authority, custody service or permission to drive physical actuators. Local safety controls must remain independently able to veto actions.

## Reporting

Use GitHub's private vulnerability reporting form under the repository **Security** tab for projection over-disclosure, privilege escalation, signature or identity verification, replay, recipient/purpose binding, model/artifact extraction, policy bypass, malicious adapters or devices, prompt injection, poisoning, provider compromise, dependency leakage, stale authorization, schema confusion, unsafe tool/actuator behavior, supply-chain compromise, or misleading departure receipts.

Include the affected revision, minimal synthetic reproduction, expected security boundary and impact. Do not include secrets, production identifiers, personal world-model data, raw multimodal content or third-party data. If private reporting is unavailable, open a content-free issue requesting a secure contact path.

Maintainers should acknowledge a private report within seven days and coordinate disclosure after a fix or explicit risk disposition. This is a response target, not a service-level guarantee.

## Supported versions

Only the latest public branch revision receives security fixes. No released Python or Rust version is currently designated production-supported. The Wave 01 provenance profile has stable conformance fixtures, while model ecology, SDK, HPL, extension, synchronization, and research surfaces remain provisional or experimental.

## Expectations

- Adapters and capability descriptors are untrusted and confer no authority.
- Unknown semantics, schema versions and missing authorization fail closed.
- Queries, projections, transfers, tools, durable stream promotion and actuation require operation-bound authorization.
- Multimodal bytes remain outside model events; references require integrity and provenance checks.
- Offline and partial replicas enforce revocation freshness and privacy segments.
- Model/provider output is untrusted evidence or a candidate, never an automatic canonical write.
- Dependency telemetry, logs, prompts, exceptions and caches must not leak protected context.

See `security/THREAT_MODEL.md`. Security fixes may intentionally remove unsafe experimental behavior without backward compatibility.
