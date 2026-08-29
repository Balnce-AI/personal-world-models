---
status: PROPOSED
---
# Confidence, time and epistemic status

A generic confidence component may include source reliability, measurement quality, corroboration, context completeness and age:

\[
C(a,t)=F(c_{source},c_{measure},c_{agreement},c_{context},D_\tau(t-t_r))
\]

No universal decay function is permitted.

Examples that may decay: inferred preference, stale location, predicted availability.  
Examples that should not automatically decay: provenance, explicit contract, security incident, root identity claim, explicitly durable policy.

The important property is that **record age does not silently become truth loss**; decay is domain and policy specific.
