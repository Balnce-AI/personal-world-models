---
status: REFERENCE_IMPLEMENTATION
---
# Authority Composition

Let an action request contain capability set `Q` and each principal emit a constraint set `Γ_i`.

The public reference model uses:

$$
Q_{allowed}=Q \cap G - D
$$

where `G` is the union of valid scoped grants and `D` the union of applicable denials. Mandatory physical/legal denials always dominate grants.

This is intentionally conservative. Real legal/contractual systems may contain obligations, exceptions, appeals, emergency powers and human adjudication that cannot be reduced to set subtraction.

The benchmark question is not whether this algebra models every law. It is whether a proposed HPL authorization can be reduced to a bounded capability envelope that is explicit, explainable and testable.
