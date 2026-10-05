# Conformance Levels

Conformance is declared against a level ID, specification version, suite versions, and supported extensions. Levels are cumulative in the order below. A claim MUST satisfy every feature and suite at its level and all preceding levels. Partial results MAY be published as test evidence but MUST NOT be labeled conformance.

## `PWM-CORE-1`

Required features: canonical CBOR verification; CID verification; event and receipt signature verification; key-state enforcement; receipt verification.

Required suite: `PWM-PROVENANCE-WAVE01` version `1.0.0`. Wave01 remains authoritative for the `pwm-public-provenance-v1` profile.

## `PWM-MODEL-ECOLOGY-1`

Required features: model proposal/acceptance/supersession/revocation lifecycle; family-kind constraints; explicit contradiction retention; current/disputed query filtering; acyclic `DEPENDS_ON`; possible-world isolation from actual state.

Required suite: `PWM-MODEL-ECOLOGY-V1` version `1.0.0`.

## `PWM-SOVEREIGNTY-1`

Required features: monotonic privacy propagation; query authorization filtering; provenance retention after correction; deny-on-unknown authority semantics; principal, purpose, recipient, and expiry binding.

Required suites: `PWM-MODEL-ECOLOGY-V1` and `HPL-PROJECTION-V1`, both version `1.0.0`.

## `HPL-BOUNDARY-1`

Required features: least-disclosure projection; explicit authority resolution; projection authorization binding; recipient and purpose binding; expiration; withheld-endpoint edge removal; foreign observations isolated as learning candidates.

Required suite: `HPL-PROJECTION-V1` version `1.0.0`.

## `PWM-RESEARCH-1`

Required features: versioned model-family registry; uncertainty and evidence retention; inspectable derived-model lineage; evaluator-scoped calibration; experimental feature labeling; no authority derived from model capability or research status.

Required suites: all suites required by the preceding levels. A claim MUST additionally enumerate the research features evaluated and their stability levels; this level does not assert scientific validity or universal model quality.

The exact machine-readable feature and suite membership is in `conformance/manifest.json`. That manifest defines requirements, not current implementation claims.
