---
status: PROPOSED
version: 0.1.0
---
# Human Projection Layer Core Specification

## Definition

The **Human Projection Layer (HPL)** is the policy-governed compilation and lifecycle system that determines what bounded representation of a person's or organization's sovereign intelligence may enter another intelligence, application, agent, vehicle, robot, machine, environment, or network.

It decides:

- **what** may leave;
- **why** it is needed;
- **who** may receive it;
- **under whose authority**;
- **for how long**;
- **in what representation**;
- **under what execution/safety constraints**;
- **what evidence must return**;
- and **what lifecycle assurance is required afterward**.

## Projection operator

\[
\mathcal{H}(W,T,A,R,E) \rightarrow \mathcal{R}
\]

`W` is an authorized world view, `T` the task/purpose, `A` composed authority, `R` recipient/runtime profile, `E` environment/trust evidence, and `R`-script output is the derived representation set.

The compiler seeks a representation that meets task utility while minimizing disclosure:

\[
\min_{r}\; \operatorname{Leakage}(W,r)
\]

subject to:

\[
\operatorname{Utility}(r,T) \ge u_{min},\quad
\operatorname{Allowed}(r,A,R,E)=1
\]

Physical execution adds the separate condition that the recipient's **local safety system** accepts the action. HPL cannot waive it.

## Invariants

1. The canonical PWM is not copied into ordinary foreign execution infrastructure.
2. Projection is purpose-bound and recipient-bound.
3. A capability description is not authorization.
4. A protocol endpoint is not identity.
5. Local safety authority remains local.
6. Foreign observations become learning candidates, not silent canonical mutations.
7. Departure is evidence-tiered; universal deletion is never implied.
8. Unknown external semantics remain unknown until grounded.
