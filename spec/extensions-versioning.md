# Extensions, Namespaces, and Stability

## Namespaces

The prefixes `pwm.`, `hpl.`, `fc.`, and `conformance.` are reserved for this specification and its attributed compatibility profiles. An extension MUST use a lowercase reverse-DNS identifier with at least two labels matching `^(?:[a-z][a-z0-9-]*\.)+[a-z][a-z0-9-]*$`, for example `org.example.preference-import` or `edu.mit.pwm-study`. Extension-defined event types, fields intended for shared interchange, and feature IDs MUST begin with the complete extension identifier followed by `.`.

Possession of a domain name does not convey authority inside a PWM. Namespace identity is collision avoidance, not principal identity, authentication, capability, consent, or authorization.

An extension MUST publish a manifest conforming to `schemas/json-schema/extension-manifest.schema.json`. An implementation MUST reject a required extension that it does not support. It MAY retain or ignore an unsupported optional extension only when doing so cannot change authorization, privacy, provenance, topology validity, or signed bytes. It MUST otherwise reject the containing operation.

Portable manifests use only exact `MAJOR.MINOR.PATCH`, caret, tilde, or greater-than-or-equal dependency expressions. `^M.m.p` permits versions with the same nonzero major, `~M.m.p` permits the same major and minor, and `>=M.m.p` sets only a lower bound. Prerelease dependencies require an exact version. Resolution selects the highest installed non-deprecated version satisfying every range; ambiguity or incompatible requirements fail closed. Conformance fixtures SHOULD use exact versions.

Extensions MUST NOT:

- redefine a standard field or event type;
- weaken a standard invariant;
- introduce a less restrictive privacy result than its inputs;
- convert capability or namespace recognition into authority;
- mutate actual-world state from a possible-world record without a standard governed acceptance event.

`extensions/registry.json` is a static discovery aid. Registration does not make an extension normative or trusted.

## Stability levels

- `EXPERIMENTAL`: behavior may change or be removed in any release; production portability MUST NOT be assumed.
- `PROVISIONAL`: the contract is testable and versioned, but compatible evolution is not yet guaranteed across a major specification release.
- `STABLE`: backward-incompatible changes require a new major extension or specification version and a migration statement.
- `DEPRECATED`: retained for bounded compatibility; the manifest MUST identify a replacement or explain why none exists and MUST state a removal policy.

Promotion MUST be explicit in a new registry revision. `EXPERIMENTAL` may become `PROVISIONAL`; `PROVISIONAL` may become `STABLE`; any level may become `DEPRECATED`. A stability change MUST NOT rewrite historical manifests. Deprecation is not revocation, and consumers MUST continue to apply the declared security and privacy semantics while accepting a deprecated extension.
