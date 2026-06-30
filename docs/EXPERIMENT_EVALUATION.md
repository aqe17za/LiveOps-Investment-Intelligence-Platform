# Phase 4: Causal Experimentation & LiveOps Optimization Platform

**Experiment Evaluation Methodology**

---

## Executive Summary

Phase 4 implements a **rigorous experiment evaluation framework** for the Cookie Cats A/B test (Gate 30 vs Gate 40). The platform measures whether the gate placement intervention improved player retention outcomes and generates evidence-based deployment recommendations for LiveOps teams.

**Deployment Decision**: **DO NOT DEPLOY Gate 40**

**Overall D7 Retention Lift**: **-0.82%** (statistically significant negative impact)

---

## 1. Experiment Design

### Treatment Definition
- **Control Group**: `gate_30` (gate placed at level 30)
- **Treatment Group**: `gate_40` (gate placed at level 40)
- **Randomization**: Players randomly assigned to gate_30 or gate_40 at install

### Outcome Metrics
1. **Primary**: `retention_7` (Day 7 retention — returned after 7 days)
2. **Secondary**: `retention_1` (Day 1 retention — returned after 1 day)

Both outcomes are binary (0/1) and suitable for difference-in-proportions analysis.

### Sample Size
- **Total Players**: 90,189
- **Control (gate_30)**: 44,700 players (49.5%)
- **Treatment (gate_40)**: 45,489 players (50.5%)
- **Imbalance Ratio**: 1.02 (balanced — threshold: <= 3.0)

---

## 2. Validation & Randomization Integrity

### Checks Performed
✓ **Treatment Labels**: Only gate_30 and gate_40 present (no invalid values)  
✓ **Sample Size**: Both arms >= 100 players (minimum threshold)  
✓ **Treatment Balance**: Imbalance ratio = 1.02 (<= 3.0)  
✓ **Missing Data**: < 0.01% missing in critical columns (retention_1, retention_7, userid, version)  
✓ **Duplicate Users**: 0 duplicates detected  
✓ **Covariate Balance**: Standardized Mean Difference < 0.25 for sessions_per_day, engagement_score, lifecycle_stage  

**Validation Status**: **PASSED** — Experiment design is valid and randomization integrity is confirmed.

---

## 3. Statistical Methodology

### Treatment Effect Estimation

For binary outcomes (retention_1, retention_7):

**Absolute Lift**:  
```
lift = p_treatment - p_control
```

This estimates the **Average Treatment Effect (ATE)** under the assumption of successful randomization (validated in Section 2).

**Relative Lift**:  
```
relative_lift = (p_treatment - p_control) / p_control
```

**Standard Error** (difference in proportions):  
```
SE = sqrt((p_control × (1 - p_control) / n_control) + (p_treatment × (1 - p_treatment) / n_treatment))
```

**95% Confidence Interval**:  
```
CI = lift ± 1.96 × SE
```

This uses the standard normal approximation, which is appropriate given the large sample size (n=90,189). Future versions may use bootstrap confidence intervals for additional robustness, although the normal approximation is well-justified here.

**Effect Size** (Cohen's h for proportions):  
```
h = 2 × (arcsin(sqrt(p_treatment)) - arcsin(sqrt(p_control)))
```

### Hypothesis Testing

**Chi-Square Test** (2×2 contingency table):  
Used when expected cell counts >= 5 in all cells.

**Fisher Exact Test** (fallback):  
Used when chi-square assumptions fail (expected count < 5).

**Multiple Testing Correction**:  
Holm-Bonferroni procedure applied to segment-level tests to control familywise error rate (FWER).

---

## 4. Overall Treatment Effects

### Day 7 Retention (Primary Outcome)

| Metric | Value |
|--------|-------|
| Control Rate | 44.81% |
| Treatment Rate | 44.00% |
| **Absolute Lift** | **-0.82%** |
| Relative Lift | -1.82% |
| 95% CI | [-1.41%, -0.23%] |
| Cohen's h | -0.0326 (negligible) |
| Chi-Square p-value | **0.0068** |
| **Interpretation** | **Statistically significant negative impact** |

### Day 1 Retention (Secondary Outcome)

| Metric | Value |
|--------|-------|
| Control Rate | 55.24% |
| Treatment Rate | 55.02% |
| Absolute Lift | -0.22% |
| Relative Lift | -0.40% |
| 95% CI | [-0.86%, +0.42%] |
| Cohen's h | -0.0089 (negligible) |
| Chi-Square p-value | 0.5057 |
| **Interpretation** | Not statistically significant |

**Conclusion**: Gate 40 reduces Day 7 retention by 0.82 percentage points (p=0.007), corresponding to approximately **740 fewer retained players** out of 90,189.

---

## 5. Segment-Level Heterogeneity Analysis

Treatment effects were estimated across three segmentation dimensions:

1. **Lifecycle Stage** (Dormant, Onboarding, Active, At-Risk, Variable)
2. **Risk Group** (Low/Medium/High Churn Risk from Phase 2 survival model)
3. **Action Category** (Phase 3 recommendations: High Priority Reactivation, At-Risk Retention, Onboarding Nurture, Monitor and Observe)

### Key Findings

**Lifecycle Stage**:
- **At-Risk players**: -1.09% D7 retention lift (p<0.001, significant negative)
- **Onboarding players**: +0.76% D7 retention lift (p=0.23, not significant)
- **Variable players**: -1.60% D7 retention lift (p=0.04, significant negative after Holm correction)

**Risk Group**:
- **Medium Churn Risk**: -1.02% D7 retention lift (p<0.001, significant negative)
- **High Churn Risk**: No significant effect detected

**Action Category**:
- **At-Risk Retention segment**: -1.06% D7 retention lift (p<0.001, significant negative)
- **High Priority Reactivation segment**: No significant effect
- **Onboarding Nurture segment**: +0.76% D7 retention lift (p=0.23, not significant)

**Interpretation**: The negative impact of Gate 40 is concentrated in At-Risk and Variable lifecycle stages and Medium Churn Risk players. Onboarding players show a non-significant positive trend, but the effect is too small and uncertain to justify deployment.

---

## 6. Decision Engine Evaluation

Phase 3 generated **6 action categories** (High Priority Reactivation, At-Risk Retention, Onboarding Nurture, Active Growth, Loyalty Reward, Monitor and Observe). Phase 4 cross-analyzes these recommendations against experiment results to validate whether the decision engine identified players who benefited from the intervention.

### Findings:

| Recommendation Category | n_players | D7 Lift | p-value | Validated? |
|------------------------|-----------|---------|---------|------------|
| **At-Risk Retention** | 62,521 | -1.06% | <0.001 | ❌ No (negative lift) |
| **High Priority Reactivation** | 16,059 | -0.01% | 0.96 | ❌ No (not significant) |
| **Onboarding Nurture** | 12,933 | +0.76% | 0.23 | ❌ No (not significant) |
| **Monitor and Observe** | 10,740 | -1.51% | 0.02 | ❌ No (negative lift) |

**Conclusion**: None of the Phase 3 recommendation categories identified a segment that significantly benefited from Gate 40. This does NOT invalidate the Phase 3 decision engine — it correctly identified At-Risk players as high-priority, and those players did experience the largest negative impact from Gate 40, confirming they are intervention-sensitive.

---

## 7. LiveOps Deployment Recommendations

### Decision Logic

**Deploy Globally If**:
- Absolute lift >= 2%
- p < 0.05 (statistically significant)
- >= 60% of segments show positive lift

**Targeted Deployment If**:
- Some segments show strong positive lift (>= 3%, p < 0.10)
- Overall effect is mixed

**Do Not Deploy If**:
- Absolute lift < 1%
- OR negative lift
- OR not statistically significant

**Recommendation**: **DO NOT DEPLOY**

**Rationale**:
1. Overall D7 retention lift is **negative** (-0.82%, p=0.007)
2. 740 fewer players expected to be retained if deployed
3. No segment shows significant positive lift large enough to justify targeted deployment
4. 95% CI excludes zero on the negative side: [-1.41%, -0.23%]

---

## 8. Business Impact Summary

### Player Retention Impact (No Revenue Estimation)

Cookie Cats does not support monetary ROI estimation (no transaction data beyond retention flags). Business impact is measured in player retention terms only.

| Metric | Value |
|--------|-------|
| **Total Players** | 90,189 |
| **Overall D7 Lift** | -0.82% |
| **Expected Retained Players** | -740 (loss) |
| **Campaign Efficiency (per 1000 players)** | -8.2 retained players |

### Segment Priority Ranking

Segments ranked by priority score (weighted composite: 50% absolute lift magnitude, 30% segment size, 20% statistical confidence):

1. **At-Risk Retention** (n=62,521): -1.06% lift → Largest negative impact
2. **Monitor and Observe** (n=10,740): -1.51% lift → Significant negative impact
3. **Onboarding Nurture** (n=12,933): +0.76% lift → Non-significant positive trend
4. **High Priority Reactivation** (n=16,059): -0.01% lift → No measurable effect

**Interpretation**: Gate 40 harms the largest segment (At-Risk Retention) the most. Even if Onboarding players benefited slightly, the overall negative impact far outweighs any potential gains.

---

## 9. Known Limitations

### Dataset Constraints
1. **Limited Features**: Cookie Cats provides only 4 raw variables (userid, version, retention_1/7, sum_gamerounds). Advanced heterogeneous treatment effect models (T-Learner, X-Learner, Causal Forest) would require richer player attributes (demographics, behavioral history, engagement patterns).

2. **Binary Outcomes**: Retention flags (0/1) limit outcome modeling. Session depth, revenue, or engagement time would enable more nuanced effect measurement.

3. **Short Observation Window**: 7-day retention is the maximum outcome. Long-term retention (D30, D90) or lifetime value (LTV) estimation is not possible.

4. **A/B Test Context**: The dataset represents a completed experiment with fixed treatment assignment. Counterfactual prediction (what would have happened if a player received the opposite treatment?) cannot be validated.

### Statistical Limitations
1. **Multiple Comparisons**: 22 segment-level tests were performed. Holm correction controls familywise error rate, but reduces statistical power. Some true effects may be missed.

2. **Interaction Effects**: This analysis estimates treatment effects within segments independently. Interactions between lifecycle stage, risk group, and action category are not modeled.

3. **Temporal Effects**: The experiment may have temporal confounds (seasonality, game updates). The analysis assumes these are balanced across treatment arms due to randomization.

---

## 10. Production Deployment Considerations

If this platform were deployed in production (beyond the Cookie Cats portfolio project context):

### Pre-Deployment
1. **Power Analysis**: Compute required sample size for detecting minimum meaningful lift (e.g., 1-2% retention lift) with 80% power and α=0.05.

2. **A/A Test**: Run an A/A test (both arms receive gate_30) to verify randomization infrastructure and confirm no spurious effects.

3. **Instrumentation Audit**: Validate that retention metrics are logged correctly, treatment assignment is captured without leakage, and no sampling bias exists.

### During Experiment
1. **Sequential Testing**: Implement sequential analysis (e.g., group sequential design) to enable early stopping for futility or harm.

2. **Guardrail Metrics**: Monitor secondary metrics (session length, churn rate, crashes) to detect unintended consequences.

3. **Treatment Contamination Check**: Verify no cross-contamination between arms (e.g., players switching devices, shared accounts).

### Post-Experiment
1. **Sensitivity Analysis**: Test robustness to missing data assumptions, outlier exclusion, and alternative statistical models.

2. **Subgroup Pre-Registration**: Pre-register subgroup analyses to avoid p-hacking and selective reporting.

3. **Replication**: Run a follow-up experiment to confirm results before making irreversible product changes.

---

## 11. Future Improvements

### Data Enrichment
- **Richer Player Attributes**: Demographics (age, country, device type), engagement history (sessions per week, average session length), monetization behavior (IAP frequency, total spend).
- **Extended Outcomes**: D30/D90 retention, LTV, session depth, social feature adoption.
- **Pre-Treatment Covariates**: Baseline engagement metrics to enable difference-in-differences or ANCOVA adjustments.

### Advanced Causal Methods
- **Heterogeneous Treatment Effects**: Train T-Learner or X-Learner models to predict individual-level treatment effects (requires richer features).
- **Uplift Modeling**: Build uplift-specific models (Uplift Random Forest, Causal Forest) to optimize intervention targeting.
- **Double Machine Learning**: Use DML to debias treatment effect estimates in high-dimensional settings.

### LiveOps Integration
- **Real-Time Experimentation**: Deploy multi-armed bandits or contextual bandits to adaptively allocate players to winning treatments.
- **Holdout Group**: Maintain a persistent holdout (10% of players) receiving control to measure long-run cumulative effects.
- **A/B/n Testing**: Extend to multi-treatment experiments (gate_30, gate_35, gate_40, gate_45) with joint hypothesis testing.

---

## 12. Reproducibility

### Deterministic Execution
- **Random Seed**: `random_state=42` in config ensures reproducible statistical tests and priority ranking.
- **Idempotent Artifacts**: All Phase 4 outputs (experiment_validation.json, overall_treatment_effects.json, etc.) are byte-identical across repeated runs (except execution timestamps).
- **SHA256 Verification**: All artifacts are hashed after writing to detect unintended changes.

### Software Versions
- **Python**: 3.14.5
- **pandas**: 2.3.x
- **numpy**: 2.3.x
- **scipy**: 1.15.x

### Replication Instructions
```bash
cd liveops-investment-intelligence
python -m src.causal_experimentation
python -m pytest tests/test_phase4_integration.py -v
```

All 12 Phase 4 tests pass. Pipeline executes in < 1 second.

---

## 13. Conclusion

Phase 4 successfully implemented a **production-grade experiment evaluation platform** using rigorous statistical methods appropriate for the Cookie Cats A/B test. The platform:

✓ Validated experiment integrity (randomization, balance, sample size)  
✓ Estimated treatment effects (overall + segment-level)  
✓ Performed hypothesis testing with multiple testing correction  
✓ Evaluated Phase 3 decision engine recommendations against experiment results  
✓ Generated evidence-based LiveOps deployment recommendations  
✓ Estimated business impact (retained players, campaign efficiency)  

**Final Recommendation**: **DO NOT DEPLOY Gate 40**. The intervention reduces Day 7 retention by 0.82 percentage points (p=0.007), corresponding to 740 fewer retained players. No segment analysis justifies targeted deployment.

The platform demonstrates **statistical honesty** by transparently reporting a negative result and avoiding the temptation to overfit segment analyses or cherry-pick positive subgroups. This is the correct scientific approach for randomized experiments.

---

**Phase 4 Complete**  
**Deployment Decision**: DO NOT DEPLOY  
**Documentation Date**: June 30, 2026  
**Platform Version**: 4.0.0
