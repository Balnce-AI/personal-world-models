# Calibration

**Status:** `REFERENCE_IMPLEMENTATION` for arithmetic; `EXPERIMENTAL` for interpretation

For resolved binary forecasts, the implementation computes Brier loss and emits it in parts-per-million. Calibration records are immutable derived artifacts over explicit prediction/outcome pairs. They do not retroactively alter forecast probabilities.

The current reference does not provide confidence intervals, binning, multiclass scores, censoring, or domain adaptation. One result cannot establish general calibration, and freshness cannot be converted into universal confidence decay.
