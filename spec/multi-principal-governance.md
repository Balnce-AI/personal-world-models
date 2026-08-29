---
status: PROPOSED
version: 0.1.0
---
# Multi-Principal Governance

A physical system may legitimately be constrained by a person, owner, employer, OEM, fleet operator, regulator, insurer, site operator, passenger, technician, or safety controller.

HPL MUST NOT assume that "the user always wins."

Each authority input is normalized to a typed constraint:

$$
\Gamma_i = \langle principal, mandate, scope, time, jurisdiction, class, effect, evidence \rangle
$$

Constraint classes include:

- `PHYSICAL` — current machine/geometry/energy/safety limits;
- `LEGAL` — jurisdictional constraints;
- `COMMERCIAL` — contractual/ownership/service constraints;
- `PERSONAL` — consent, preference and personal policy;
- `CONTEXTUAL` — conditional mandate;
- `ADVISORY` — planning input without hard veto.

The reference engine uses **deny-overrides + scoped grants**. Production systems may require richer policy algebra, but any resolution MUST be explainable and provenance-bearing.

This profile is intentionally compatible with richer Covenant-Atom implementations without defining a second canonical permission system.
