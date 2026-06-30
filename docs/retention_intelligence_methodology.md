# Phase 3: Player Decision Engine — Methodology

## Why This Approach (And Why Not ML Regression)

### The Problem With a Regression Model Here

Cookie Cats provides five raw columns: `userid`, `sum_gamerounds`, `retention_1`,
`retention_7`, `version`. Phase 1 engineers `sessions_per_day` from `sum_gamerounds`.

The natural regression target would be **7-day cumulative sessions** — proxied as
`sessions_per_day × 7`. But `sessions_per_day` is also the strongest available
predictor. The model learns:

```
y = sessions_per_day × 7
x = [sessions_per_day, ...]
→ Model learns: y ≈ 7 × x₁    (identity scaling, not prediction)
→ R² ≈ 1.0                     (trivially guaranteed, not impressively)
```

A senior data scientist's immediate question: *"Why didn't you just multiply by 7?"*

They would be right. This is not supervised learning. It is identity mapping.

The model comparison (Ridge vs RF vs LightGBM) is also meaningless here:
Ridge wins because it can represent `y = 7x` exactly. Trees approximate it.
The "comparison" measures approximation error of a linear function, not
predictive power over a meaningful outcome.

SHAP would simply confirm that `sessions_per_day` explains nearly all variance —
which is mathematically guaranteed when the target is `sessions_per_day × 7`.

**Conclusion:** The data does not justify a regression task. It justifies a
**decision-support system**. That is what Phase 3 builds.

---

## What the Data Does Justify

Phase 1 produces **lifecycle segmentation** (Dormant, Onboarding, Active, At-Risk, Variable).  
Phase 2 produces **churn risk stratification** (Low/Medium/High Churn Risk) via Cox PH.

Together, these define a complete picture of *who each player is* and *how at-risk they are*.
The correct LiveOps question is not "how many sessions will this player have?" — it is:

> **"Who should we act on, how urgently, and with what intervention?"**

---

## Architecture

```
Phase 1 outputs                    Phase 2 outputs
(lifecycle_stage,              +   (risk_group,
 engagement_score,                  survival_prob_day7,
 sessions_per_day)                  partial_hazard)
         ↓                                  ↓
         └──────────── merge ──────────────┘
                           ↓
              Priority Score (0–100)
         weighted composite formula
                           ↓
         Business Rules Engine (YAML)
         first-match-wins, 6 categories
                           ↓
    ┌──────────────────────────────────────────────────────────┐
    │ Per-Player Decisions (player_decisions.parquet, N × 9)   │
    │ action_category | priority_score | intervention          │
    │ lifecycle_stage | risk_group     | engagement_score      │
    └──────────────────────────────────────────────────────────┘
```

---

## Priority Score Formula

```
priority_score = (
    0.40 × normalize(engagement_score)      # Phase 1 composite
  + 0.35 × (1 - survival_prob_day7)         # Phase 2 churn risk
  + 0.25 × normalize(sessions_per_day)      # Phase 1 session intensity
) × 100
```

Score range: **[0, 100]**. Higher = player should receive intervention sooner.

### Weight Defensibility

The weights (0.40, 0.35, 0.25) are **configurable business priors defined in
YAML, not statistically learned coefficients.** In production, these weights
would be calibrated using historical intervention outcomes, A/B test lift
results, and business objectives (e.g., retention-first vs. revenue-first
strategy). Starting values follow an engagement-first philosophy: behavioral
signals outweigh survival risk signals to reduce false-positive interventions
on players who are at-risk on the survival model but still engaging normally.

To change the weighting strategy, edit `simulation_config.yaml →
phase_3.player_decision_engine.priority_score_weights`. No code change required.

### Priority Score Distribution (How to Read It)

Analytics teams communicate score distributions as **percentiles**, not just
mean/std. The full percentile profile per segment (P25, P50, P75, P90, P95, P99)
is written to `segment_summary.json`.

**How to use percentiles operationally:**
- **P90–P99**: The most urgent players within a segment. If the LiveOps budget
  allows treating only 10% of a segment, target players above P90.
- **P50 (median)**: The "typical" player in the segment — more robust than mean
  when the score distribution is skewed.
- **P25**: Lower-urgency players in the segment who may not need immediate intervention.

---

## Business Rules Engine

### Rule Evaluation: First-Match-Wins

Rules are evaluated in **strict priority order** (priority=1 highest,
priority=6 catch-all). When a player satisfies multiple rules:

```
Rule evaluation flow per player:
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. Check Rule priority=1 (High Priority Reactivation)       │
  │    lifecycle_stage ∈ {Dormant, At-Risk}                     │
  │    AND risk_group ∈ {High Churn Risk}  →  MATCH → ASSIGN    │
  │    ↓ if no match                                            │
  │ 2. Check Rule priority=2 (At-Risk Retention)                │
  │    lifecycle_stage ∈ {At-Risk}                              │
  │    AND risk_group ∈ {Medium, High Churn Risk} → MATCH → ASSIGN
  │    ↓ if no match                                            │
  │ 3. ... (rules 3–5 evaluated in order)                       │
  │    ↓ if no match                                            │
  │ 6. Rule priority=6 (Monitor and Observe)                    │
  │    lifecycle_stage ∈ ANY  AND  risk_group ∈ ANY → CATCH-ALL │
  └─────────────────────────────────────────────────────────────┘
```

**Once a rule matches, all remaining rules are skipped.** A player who satisfies
both Rule 1 and Rule 3 is assigned Rule 1 — the more critical intervention wins.

The catch-all (priority=6) matches all lifecycle stages and risk groups, guaranteeing
every player is assigned exactly one category. The pipeline raises `DataPreparationError`
if any player remains unassigned — this prevents silent coverage gaps.

### Action Categories (6 Rules)

| Priority | Category | Lifecycle | Risk Group | Primary KPI | Owner |
|----------|----------|-----------|------------|-------------|-------|
| 1 | High Priority Reactivation | Dormant, At-Risk | High Churn Risk | D7 Retention | LiveOps |
| 2 | At-Risk Retention | At-Risk | Medium, High Churn | D7 Retention | LiveOps |
| 3 | Onboarding Nurture | Onboarding | Any | D1→D7 Retention conversion | Growth |
| 4 | Active Growth | Active | Medium, High Churn | Sessions/week | LiveOps |
| 5 | Loyalty Reward | Active | Low Churn | 30-day retention | CRM |
| 6 | Monitor and Observe | Any | Any (catch-all) | Natural retention rate | Analytics |

---

## Recommendation → Business Goal → KPI → Experiment

Each intervention flows into a measurable business outcome and connects
naturally to Phase 4 Uplift Estimation:

### High Priority Reactivation
```
Intervention:          Emergency reactivation — push notification + exclusive offer
         ↓
Expected Business Goal: Increase D7 Retention
         ↓
Primary KPI:           Retention lift vs. holdout control group
         ↓
Experiment (Phase 4):  Causal treatment effect via Uplift Estimation
                       (T-learner / X-learner on gate_30 vs gate_40 split)
```

### At-Risk Retention
```
Intervention:          Personalized reward + daily bonus streak reinstatement
         ↓
Expected Business Goal: Reduce churn rate in At-Risk cohort
         ↓
Primary KPI:           Churn rate reduction vs. control
         ↓
Experiment (Phase 4):  A/B test gate placement effect on At-Risk retention lift
```

### Onboarding Nurture
```
Intervention:          Tutorial completion bonus + first-week milestone reward
         ↓
Expected Business Goal: Improve new player D7 retention
         ↓
Primary KPI:           D1 → D7 retention conversion rate
         ↓
Experiment (Phase 4):  Gate placement may moderate onboarding friction — Phase 4 quantifies this
```

### Loyalty Reward
```
Intervention:          VIP recognition + exclusive content unlock
         ↓
Expected Business Goal: Maintain retention in highest-value stable cohort
         ↓
Primary KPI:           30-day retention vs. baseline
         ↓
Experiment (Phase 4):  Does VIP treatment causally lift long-run retention?
```

### Monitor and Observe
```
No intervention — passive monitoring only
         ↓
Role:                  Natural control baseline
         ↓
Primary KPI:           Natural churn rate
         ↓
Experiment (Phase 4):  This group provides the control reference for all causal estimates
```

This structure makes the project flow naturally: **Phase 3 identifies who and
what → Phase 4 measures whether it actually works**.

---

## Output Artifacts

| Artifact | Rows/Content | Purpose |
|----------|-------------|---------|
| `player_decisions.parquet` | N × 9 cols | Per-player: action_category, priority_score, intervention + context |
| `segment_summary.json` | Per category | n_players, %, P25/P50/P75/P90/P95/P99, KPIs, phase4_connection |
| `decision_rules.json` | Per rule | Rule coverage counts, priority score distributions (audit trail) |

---

## Known Limitations

1. **No causal identification** — Priority scores and category assignments are
   correlational. High-priority players *tend to* exhibit at-risk behavior, but
   the score does not guarantee that intervening will retain them. Phase 4
   (Uplift Estimation) addresses causality via A/B testing.

2. **Weights are business priors** — The 0.40/0.35/0.25 split is not derived
   from historical data. In production, calibrate weights against intervention
   outcome logs before deploying at scale.

3. **Static rules** — Business rules are defined once and applied uniformly.
   In production, rules would be personalized (player-level context, LTV tier,
   past intervention history).

4. **No monetization weighting** — Cookie Cats lacks IAP/revenue data. Priority
   score treats all players equally regardless of spend potential. A true LiveOps
   engine would weight high-spend players more heavily.

5. **A/B treatment not used here** — `version` (gate_30 vs gate_40) is available
   but the causal effect of gate placement is reserved for Phase 4 Uplift Estimation.
   Phase 3 correctly avoids making causal claims it cannot support.

---

## Future Work

| Phase | Capability | What's Needed |
|-------|-----------|--------------|
| Phase 4 | Uplift Estimation — causal A/B effect | Cookie Cats version column (available) |
| Phase 5+ | Weight calibration via intervention outcomes | Historical LiveOps campaign data |
| Phase 5+ | Revenue-weighted priority scoring | IAP transaction data |
| Phase 5+ | Personalised intervention selection | Player-level history, past interventions |
| Phase 5+ | Real-time scoring API | Event streaming infrastructure |

---

*See also: [model_validation.md](model_validation.md) for Phase 2 statistical decisions,
[SURVIVAL_ASSUMPTIONS.md](SURVIVAL_ASSUMPTIONS.md) for survival model assumptions.*
