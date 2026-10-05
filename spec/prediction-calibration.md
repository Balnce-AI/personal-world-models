# Prediction And Calibration Profile

**Truth plane:** `EXPERIMENTAL`

A prediction records subject, predicate, predicted value, target time, record time, probability, model references, evidence provenance, privacy, and lifecycle status. Resolution creates a distinct outcome record. It MUST NOT overwrite the historical forecast.

The reference calibration procedure supports resolved binary predictions and reports a fixed-point Brier score:

$$
B = \frac{1}{N}\sum_{i=1}^{N}(p_i-o_i)^2
$$

where probabilities and output are represented in parts-per-million at record boundaries. A calibration record identifies every prediction/outcome pair, procedure version, evaluation time, and sample count. It is `EXPERIMENTAL`; small samples and domain shift MUST remain visible limitations.
