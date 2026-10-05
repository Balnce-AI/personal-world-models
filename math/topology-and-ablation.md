# Topology And Ablation

**Status:** `RESEARCH`

For task \(x\), model graph \(G\), and metric lane \(j\), define marginal structural utility as

$$
\Delta_j(G,a)=Q_j(x,G)-Q_j(x,a(G))
$$

where \(a\) is a declared ablation such as edge shuffling, family removal, staleness, confidence corruption, fabricated provenance, or contradiction injection. Claims that structure is useful require positive effects across held-out tasks while controlling model, prompt, evidence availability, and context budget.

No multiplicative cross-model value is assumed. Zero or negative deltas are valid research outcomes.

## Matched estimands

Let \(I(c,x)\) be the canonical information signature for condition \(c\), and let \(T(c,x)\) be the verified token count of the complete rendered request. A representation comparison is admissible only when

$$
I(c_1,x)=I(c_2,x) \quad\text{and}\quad T(c_1,x)=T(c_2,x).
$$

Selection experiments intentionally change \(I\) by withholding units. Derived-information experiments also change \(I\), but label new units as derived or meta rather than source evidence. These estimands must not be pooled as a single "memory versus PWM" effect.

For seeded repetition \(r\), an ablation is \(a_{s,r}(G)\). Randomized operations derive their local random stream from the declared seed, repetition, and ablation name. This prevents condition iteration order from changing the control.

Token equality is asserted only for a tokenizer adapter with a verified one-token padding symbol. For an opaque remote tokenizer, \(T\) is unknown and the result is not a token-matched causal comparison. Padding is inert declared context and its natural, padding, target, and final counts remain in the manifest.

Leakage evaluation searches the complete serialized model input and complete serialized result, including raw provider payloads, usage, and candidates. A projection-level check alone is insufficient because sensitive canaries can reappear in wrappers or provider metadata.
