# EA LiveOps Investment Intelligence Platform

A production-style player retention analytics platform featuring configurable data validation, feature engineering, survival analysis, ensemble regression, SHAP interpretability, artifact verification, statistical diagnostics, and reproducible analytics workflows for game player retention modeling.

## Project Status

✅ **Phase 1 Complete** — Telemetry pipeline, schema validation, feature engineering, profiling  
✅ **Phase 2 Complete** — Survival analysis, Kaplan-Meier curves, Cox Proportional Hazards, risk stratification  
✅ **Phase 3 Complete** — Player Decision Engine: priority scoring + YAML business rules, per-player action categories and intervention recommendations  
✅ **Phase 4 Complete** — Causal Experimentation & LiveOps Optimization: experiment validation, treatment effect estimation, statistical inference, deployment recommendations

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Raw Telemetry (Game Events)              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 1: Data Validation & Curation             │
│  • Schema validation (types, non-null)                       │
│  • Feature engineering (5 engineered features)               │
│  • Data profiling (20 statistics per feature)                │
│  • Artifact verification & manifest generation               │
└────────────────────────┬────────────────────────────────────┘
                         ↓
            ┌────────────────────────────┐
            │ Canonical Feature Store    │
            │ (90,189 players, 10 cols)  │
            └────────────┬───────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│      Phase 2: Survival Analysis & Risk Stratification        │
│  • Duration/event engineering (interval approximation)       │
│  • Kaplan-Meier curves (stratified by lifecycle stage)      │
│  • Cox Proportional Hazards (3-feature model, validated)     │
│  • Log-rank tests (pairwise stage comparisons)               │
│  • Individual risk predictions & risk groups                 │
└────────────────────────┬────────────────────────────────────┘
                         ↓
        ┌────────────────────────────────────┐
        │  Player Risk Segmentation & Scores │
        │  (Low/Medium/High churn risk)       │
        └────────────┬───────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│           Phase 3: Player Decision Engine                   │
│  • Priority score (engagement + churn risk + session rate)   │
│  • YAML business rules engine (6 action categories)          │
│  • Per-player: action_category, priority_score, intervention │
│  • No ML regression (data constraint — documented)           │
└────────────────────────┬────────────────────────────────────┘
                         ↓
         ┌──────────────────────────────────────┐
         │  Player Decisions                      │
         │  (player_decisions.parquet, N×9)       │
         └────────────┬─────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│     Phase 4: Causal Experimentation & LiveOps Optimization   │
│  • Experiment validation (randomization integrity)           │
│  • Treatment effect estimation (overall + segment-level)      │
│  • Statistical inference (chi-square, Holm correction)        │
│  • Decision engine evaluation (Phase 3 × experiment)         │
│  • LiveOps recommendations (deploy/targeted/do-not-deploy)   │
│  • Business impact (expected retained players)                │
└────────────────────────┬────────────────────────────────────┘
                         ↓
              ┌─────────────────────────┐
              │  Deployment Decision    │
              │  (DO NOT DEPLOY)        │
              └─────────────────────────┘
```

## Installation

```bash
python -m venv venv
source venv/bin/activate    # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Project Structure

```
liveops-investment-intelligence/
├── src/              ← Python modules (Phases 1+)
├── notebooks/        ← Jupyter notebooks (Phases 1+)
├── dashboard/        ← Streamlit app (Phase 6+)
├── data/             ← Input and processed data
├── models/           ← Trained ML models
├── config/           ← YAML configuration files
└── docs/             ← Documentation, ADRs, model cards
```

## Documentation

**Core Analysis:**
* [Feature Dictionary](docs/feature_dictionary.md) — Phase 1 feature definitions and schemas
* [Model Validation](docs/model_validation.md) — Phase 2+3 statistical validation and engineering decisions
* [Survival Assumptions](docs/SURVIVAL_ASSUMPTIONS.md) — Interval approximation, statistical assumptions, appropriateness
* [Retention Intelligence Methodology](docs/retention_intelligence_methodology.md) — Phase 3 design rationale, leakage prevention, model justification

**Coming in Later Phases:**
* `docs/adr/` — Architecture Decision Records
* `docs/model_cards/` — Model Cards (Phase 4+)
* `docs/evaluation/` — Model Evaluation Reports (Phase 3+)

## Phases

* [x] Phase 0: Setup + Config
* [x] Phase 1: Telemetry Pipeline
  - Schema validation, feature engineering, profiling, artifact verification
  - 7 tests passing, 100% artifact integrity verification
* [x] Phase 2: Survival Analysis
  - Kaplan-Meier curves, Cox Proportional Hazards, risk stratification
  - 5 tests passing, statistical validation completed
* [x] Phase 3: Player Decision Engine
  - Priority score (engagement + churn risk + session intensity, weighted composite)
  - YAML business rules engine: 6 action categories, first-match-wins
  - Per-player: action_category, priority_score, intervention — 90,189 players
  - 6 tests passing, 3 verified artifacts written
  - No ML regression (identity mapping documented and avoided)
* [ ] Phase 4: Uplift Estimation (A/B treatment effect)
* [ ] Phase 5: Budget Optimization
* [ ] Phase 6: Scenario Planning & Dashboard

## Known Dataset Limitations

This project uses the **Cookie Cats** dataset from Kaggle (90,189 real players) as a proof-of-concept. Important limitations:

* **A/B Test Context:** Cookie Cats data comes from a controlled A/B test, not production telemetry streams
* **Limited Variables:** Only five raw features available (`userid`, `sum_gamerounds`, `retention_1`, `retention_7`, `version`)
* **Snapshot Observations:** Survival outcome derived from Day-1 and Day-7 retention snapshots, not continuous event logs
* **Interval Approximation:** Duration engineered as {1, 3, 7} days from two-point observations — not true churn times
* **No Causal Features:** No economic data (purchases, balance), social data (friends, guilds), or skill progression

These limitations are **explicitly addressed in the design:**
- The telemetry pipeline is architected for richer production data
- Feature engineering framework accepts any engineered features
- Survival analysis uses general Cox model, not Cookie Cats-specific logic
- All assumptions are documented, not hidden

## Future Work

### In-Game Scope

* **Richer Telemetry:** Collect event-level logs (progression, purchases, social activity, skill metrics)
* **Extended Features:** Engineer engagement, economy, progression, skill, and social features from event streams
* **Time-Varying Covariates:** Extend Cox model to handle covariates that change over time
* **Model Comparison:** Benchmark Cox PH against Random Survival Forests and DeepSurv

### Deployment Scope

* **LiveOps Integration:** Wire predictions into intervention engine for real-time retention targeting
* **A/B Testing:** Measure causal impact of survival-informed interventions on retention and revenue
* **Feedback Loops:** Retrain models on production outcomes, measure model drift
* **Monitoring:** Track prediction accuracy, assumption violations, and fairness metrics by player segment

## Engineering Decisions

### Phase 3: Player Decision Engine

1. **ML regression dropped — correct decision** — `sessions_per_day × 7` as regression target with `sessions_per_day` as a predictor is identity mapping (`y = 7x`), not prediction. Any model achieves R²≈1.0 trivially. A senior DS immediately asks *"Why not just multiply by 7?"* This was the right question.
2. **Decision-support system instead** — Phase 1 lifecycle segmentation + Phase 2 churn risk stratification together define *who needs intervention, how urgently, and how*. This is what the data actually supports.
3. **Priority score** — Weighted composite: 0.40 × engagement + 0.35 × churn_risk + 0.25 × session_intensity. Scaled to [0, 100]. YAML-configurable weights.
4. **YAML business rules** — 6 action categories, fully configurable without code changes. First-match-wins semantics. Catch-all guarantees every player is assigned.
5. **Outputs** — `player_decisions.parquet` (N×9), `segment_summary.json`, `decision_rules.json` (audit trail).

See [Retention Intelligence Methodology](docs/retention_intelligence_methodology.md) for full rationale.

### Phase 2: Statistical Validation

The initial five-feature Cox model (`engagement_score`, `progression_proxy`, `sessions_per_day`, `session_frequency_bin`, `version`) exhibited Newton-Raphson non-convergence during fitting. Root-cause analysis revealed:

1. **Target Leakage:** `engagement_score` and `progression_proxy` both incorporate `retention_1`/`retention_7` — the exact observations used to define the survival outcome
2. **Circular Inference:** This circularity prevented valid model identification and inflated model performance (`progression_proxy` alone: concordance 0.963)
3. **Solution:** Removed both features, retaining only `sessions_per_day`, `session_frequency_bin`, and `version` (built from `sum_gamerounds` alone, no leakage)
4. **Result:** Final model converges cleanly (concordance 0.8606), with sane coefficients and no artificial regularization

**Decision:** Preserve statistical validity over feature count. A model with fewer independent predictors is superior to one that achieves apparent performance through target leakage.

See [Model Validation](docs/model_validation.md) for detailed analysis.

### Phase 1: Architecture Decisions

* **YAML as Single Source of Truth:** All configuration immutable during execution (no runtime defaults)
* **Schema Validation at Boundary:** Only Phase 2 validates Phase 1 output schema; does not re-check business rules
* **Deterministic Reproducibility:** All random operations seeded; identical outputs across runs (minus timestamps)
* **Manifest as Metadata Inventory:** Separate from profiling statistics; artifact hashes enable corruption detection

## Contact

Aqeel Khan  
[aqeelkhan17sept@gmail.com](mailto:aqeelkhan17sept@gmail.com)
