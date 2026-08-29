---
status: RESEARCH
---
# Projection as constrained information minimization

Let `W` be an authorized source world state and `r` a candidate representation.

A projection compiler can be treated as a constrained optimization:

\[
r^*=\arg\min_r \left(\lambda_L L(W,r)+\lambda_P P(r)+\lambda_D D(r)\right)
\]

subject to:

\[
U(r,T)\ge u_{min},\quad A(r)=1,\quad C(r,R,E)=1
\]

where:

- `L` estimates disclosure/leakage;
- `P` estimates persistence/privacy risk of the artifact class;
- `D` estimates dependency cost (model/runtime/hardware lock-in);
- `U` is task utility;
- `A` is authority/policy validity;
- `C` is compatibility with recipient and environment.

This equation is a research objective, not a claim that leakage can presently be measured perfectly. The benchmark suite exists to operationalize approximations.
