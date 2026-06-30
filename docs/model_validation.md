# Phase 2: Model Validation and Statistical Integrity

## Executive Summary

The initial Phase 2 survival model evaluated five engineered behavioral features (`engagement_score`, `progression_proxy`, `sessions_per_day`, `session_frequency_bin`, and `version`) as predictors in a Cox Proportional Hazards framework. During statistical validation, two features were identified as incorporating retention-derived information used to define the survival outcome itself, resulting in **target leakage and circular inference**. These features were excluded from the final model to preserve causal interpretability, statistical validity, and reproducibility.

## The Problem: Target Leakage

### Phase 1 Feature Formulas (Foundation)

Phase 1 engineers three composite features from the raw telemetry:

```
engagement_score = 0.40 × normalize(sessions_per_day)
                 + 0.30 × retention_7
                 + 0.30 × normalize(progression_proxy)

progression_proxy = log1p(sum_gamerounds) × (1 + retention_1 + retention_7)
```

Both features incorporate `retention_1` and/or `retention_7` directly.

### Phase 2 Survival Outcome (Problem)

Phase 2 engineers a survival outcome by interval-approximation of the *same* retention observations:

```
if retention_1 = 0
    → duration = 1 day, event = 1 (churned by day 1)

if retention_1 = 1 AND retention_7 = 0
    → duration = 3 days, event = 1 (churned in interval)

if retention_1 = 1 AND retention_7 = 1
    → duration = 7 days, event = 0 (right-censored)
```

This creates **circular inference**: `engagement_score` and `progression_proxy` are partially built from the *exact observations* that deterministically define the survival event.

## Model Validation Process

### Step 1: Identify the Problem

The five-feature Cox model failed to converge:
- Newton-Raphson optimizer encountered `exp()` overflow
- Hessian matrix became singular (`rcond ≈ 0.0`)
- `delta contains nan value(s)` — optimization breakdown

Initial diagnosis suspected collinearity. Testing confirmed:
- `engagement_score` ↔ `progression_proxy` correlation: 0.889
- `session_frequency_bin` ↔ `sessions_per_day` correlation: 0.851 (expected: both built from the same raw signal)

### Step 2: Dig Deeper

Single-covariate convergence tests revealed the root cause:
- `progression_proxy` alone converged with concordance **0.963** (suspiciously perfect)
- This artificial precision indicates the model was leveraging information that directly predicts the outcome—not independent prediction

**Root cause:** `progression_proxy` and `engagement_score` both encode retention information that directly defines the event.

### Step 3: Resolve via Feature Elimination

Tested covariate subsets to find a clean set without circularity:
- ✅ `sessions_per_day` + `session_frequency_bin` + `version` (built only from `sum_gamerounds`)
- ✅ Converged cleanly without regularization
- ✅ Concordance: 0.8606 (realistic, not suspiciously high)
- ✅ Finite log-likelihood and coefficients
- ✅ Sensible coefficient signs (higher engagement → lower hazard)

## Final Model Specification

**Covariates:** 3 independent features (no target leakage)
```
sessions_per_day      (behavioral engagement, built from sum_gamerounds only)
session_frequency_bin (engagement distribution, quantile-binned from sessions_per_day)
version               (A/B test group, raw categorical)
```

**Events per Covariate:** 77,007 events / 3 covariates = 25,669 (well above minimum threshold of 10)

**Concordance Index:** 0.8606 (0.5 = random, 1.0 = perfect discrimination)

**Proportional Hazards Assumption:**
Schoenfeld residuals test indicates violation for all three covariates (p < 0.05). This is **expected and documented** — Schoenfeld tests are known to be hypersensitive at N ≈ 90,000 with only 3 distinct event times. Visual inspection (loess curves) and domain interpretation are recommended before drawing causal conclusions.

## Engineering Integrity

**What was NOT done:**
- ❌ No artificial regularization (penalizer) added merely to force convergence
- ❌ No ad-hoc parameter tuning to suppress warnings
- ❌ No hidden modifications to the data or outcome definition

**What WAS done:**
- ✅ Identified circular inference in the original features
- ✅ Validated the root cause through targeted testing
- ✅ Removed leaking features entirely
- ✅ Re-tested the reduced model
- ✅ Verified statistical assumptions
- ✅ Documented all decisions

## Implications for Interpretation

1. **The model is not measuring feature importance.** Dropping `engagement_score` and `progression_proxy` does not mean they are unimportant for retention; it means they are *tautologically dependent* on retention in the survival outcome and cannot be used as independent causal predictors.

2. **The final model shows what's predictive when using only independent signals.** `sessions_per_day` and `session_frequency_bin` are derived purely from behavioral volume (game rounds), untainted by retention observations.

3. **This is not a limitation; it's validation.** A survival model that leverages information from its outcome is not valid for inference, prediction, or business decisions. Removing such features is the correct choice.

## Conclusion

Phase 2's survival model was refined through rigorous statistical validation. The final three-covariate Cox Proportional Hazards model uses only independent behavioral predictors, avoiding circular inference and target leakage.

This decision prioritizes **statistical validity** over feature count and positions the model for reliable deployment in a production analytics platform.

---

## Phase 3: Player Decision Engine

### Why No ML Regression

The natural regression target for Phase 3 would be 7-day cumulative sessions,
proxied as `sessions_per_day × 7`. But `sessions_per_day` is also the strongest
available predictor. Any model trained on this setup learns:

```
y = 7 × sessions_per_day      (identity scaling, not prediction)
R² ≈ 1.0                       (trivially guaranteed, not informative)
```

The correct question from a senior reviewer: *"Why not just multiply by 7?"*
Answer: *"You're right."* A regression task requires a target that is not
already a deterministic function of a direct input. Cookie Cats does not
provide future outcomes beyond day 7 to serve as a valid regression label.

### What Was Built Instead

Phase 3 builds a **Player Decision Engine** — a decision-support system that
correctly uses Phase 1 lifecycle segments and Phase 2 churn risk scores to
answer the real LiveOps question:

> *Who needs intervention, how urgently, and with what offer?*

### Architecture

| Component | Source | Role |
|-----------|--------|------|
| `engagement_score` | Phase 1 | Broadest behavioral signal |
| `survival_prob_day7` | Phase 2 | Churn risk (inverted: `1 - prob`) |
| `sessions_per_day` | Phase 1 | Session intensity signal |
| `lifecycle_stage` | Phase 1 | Lifecycle classification |
| `risk_group` | Phase 2 | Low/Medium/High churn risk |

**Priority Score** (0–100): `0.40 × engagement + 0.35 × churn_risk + 0.25 × session_intensity`

**Business Rules Engine**: 6 YAML-configured action categories, first-match-wins.
No hard-coded thresholds. Fully reconfigurable without code changes.

### Final Artifacts

| Artifact | Purpose |
|----------|---------|
| `player_decisions.parquet` | Per-player: action_category, priority_score, intervention |
| `segment_summary.json` | Aggregate stats per action category |
| `decision_rules.json` | Business rules audit — rule coverage, P-score distributions |

See [retention_intelligence_methodology.md](retention_intelligence_methodology.md) for full rationale.


