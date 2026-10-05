# Self-Model Formalism

**Status:** `PROPOSED`

Let the authorized PWM state at query time be an ecology \(E_t=(A_t,G_t,P_t,C_t)\), where \(A_t\) is assertion evidence, \(G_t\) is the typed model graph, \(P_t\) is policy/authority context, and \(C_t\) is provenance closure. This notation does not replace the existing PWM formal model.

A model \(m\in G_t\) is a tuple of subject and perspective, family and kind, state, valid interval, epistemic and lifecycle status, uncertainty, confidence, provenance, dependencies, and lineage. Derivation \(D(A)\to m^?\) yields a candidate. Governed reconciliation \(R(m^?,P,C)\) may accept, reject, defer, or dispute it. Only acceptance contributes to the default current model view.

Falsifier: a reducer that cannot reconstruct accepted state and lineage from its authorized event closure violates this profile.
