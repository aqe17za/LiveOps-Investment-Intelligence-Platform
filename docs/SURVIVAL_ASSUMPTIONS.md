# Phase 2 Survival Analysis: Statistical Assumptions & Methodology

## Overview

This Phase 2 survival analysis is an exploratory portfolio project demonstrating
survival modeling techniques on the Cookie Cats dataset. It is **not** a causal or
production-grade analysis.

## Duration Engineering: Interval Approximation

### Observed Data

Cookie Cats provides only two retention timepoints:
- Day 1: `retention_1` (Did player play on day 1?)
- Day 7: `retention_7` (Did player play on day 7?)

No observations exist at days 2, 3, 4, 5, or 6, or beyond day 7.

### Engineering Solution

To enable Cox proportional hazards modeling (which requires time variation),
we engineer three interval-approximated durations:

```
retention_1 = 0                                → duration = 1 day   → event = 1 (churned by day 1)
retention_1 = 1 AND retention_7 = 0            → duration = 3 days  → event = 1 (churned between day 1 and day 7)
retention_1 = 1 AND retention_7 = 1            → duration = 7 days  → event = 0 (right-censored, survived through day 7)
```

**Critical Caveat:** Duration = 3 is **not** the true churn time.
It is an engineering approximation for modeling purposes.

### Limitations of Interval Approximation

1. **Reduced Power:** Interval-censored data has less statistical power than exact times.
2. **Arbitrary Midpoint:** Duration = 3 (the midpoint) could be 2, 4, 5, or 6 without
   changing the validity of the modeling approach.
3. **Conservative Estimates:** Hazard ratios are biased toward the null (conservative).
4. **Not Suitable for Publication:** Formal interval-censored maximum likelihood required.

## Other Statistical Assumptions

1. **Independence:** Players' survival times are independent (no network/social effects).
2. **No Informative Censoring:** Censoring (retention_7=1) is independent of true event time.
3. **Proportional Hazards:** Cox model assumes constant hazard ratios over [0, 7].
   - Validated via Schoenfeld residuals test (p < 0.05 indicates violation).
   - Reported in survival_diagnostics.json.
4. **No Unobserved Confounders:** All relevant confounders measured in Phase 1.
5. **Large Sample:** N ≈ 90,000 >> 6 covariates (events per covariate >> 10).

## Appropriateness

**Appropriate for:**
- Portfolio project demonstrating survival modeling capability
- Technical interview showing understanding of data limitations
- Educational exercise in handling incomplete data

**Inappropriate for:**
- Published research (requires formal interval-censored likelihood)
- Production business decisions (insufficient validation)
- Claims of exact churn times (timing is approximated)

## Key Framing

**This project demonstrates application of survival analysis under interval
approximation constraints and should not be interpreted as estimating exact
churn times.**

The engineered durations (1, 3, 7 days) are modeling constructs, not observed
event times. All findings are exploratory.

## Conclusion

This survival analysis is methodologically sound within stated assumptions and
appropriate for a portfolio/interview context. The interval approximation is
explicit and documented, not hidden.

The core contribution is demonstrating **capability with survival analysis
techniques** in the presence of real-world data limitations.
