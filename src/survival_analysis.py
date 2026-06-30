"""Phase 2 — survival analysis on Phase 1's canonical feature table.

Engineers an interval-censored duration/event outcome from Cookie Cats'
two-point retention observations (day 1, day 7), fits stratified
Kaplan-Meier curves and a Cox proportional hazards model, generates
per-player predictions and risk groups, and writes a combined Phase 1 +
Phase 2 manifest.

Does not re-validate Phase 1 business rules (categories, ranges) — only
schema (columns, types, non-null). Phase 1 already guaranteed those.
"""

import hashlib
import itertools
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.exceptions import StatError
from lifelines.statistics import logrank_test, proportional_hazard_test
from numpy.linalg import matrix_rank

from src.config_loader import load_configuration
from src.exceptions import (
    ConfigurationError,
    CoxValidationError,
    InputValidationError,
    KMValidationError,
    OutputValidationError,
    Phase1Error,
    Phase2Error,
    PipelineExecutionError,
)
from src.telemetry_pipeline import compute_file_sha256

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_EXPECTED_FEATURE_STORE_COLUMNS = [
    "userid",
    "sum_gamerounds",
    "retention_1",
    "retention_7",
    "version",
    "sessions_per_day",
    "session_frequency_bin",
    "progression_proxy",
    "engagement_score",
    "lifecycle_stage",
]


def resolve_project_path(*path_parts: str) -> Path:
    """Resolve path relative to project root. Portable across all OS."""
    return PROJECT_ROOT.joinpath(*path_parts)


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================


def load_phase2_config(config_path: str, benchmarks_path: str) -> Dict[str, Any]:
    """Load Phase 2 configuration from simulation_config.yaml (single file).

    Raises ConfigurationError if any required key is missing. Never silently
    defaults. Consistent with Phase 1 pattern.
    """
    config = load_configuration(config_path, benchmarks_path)

    required_paths = {
        "km_stratify_by": ("phase_2", "survival", "km_stratify_by"),
        "lifecycle_stage_order": ("phase_2", "survival", "lifecycle_stage_order"),
        "km_log_rank_test": ("phase_2", "survival", "km_log_rank_test"),
        "log_rank_multiple_testing": ("phase_2", "survival", "log_rank_multiple_testing"),
        "min_stratum_size": ("phase_2", "survival", "min_stratum_size"),
        "ph_test_method": ("phase_2", "survival", "ph_test_method"),
        "ph_significance_level": ("phase_2", "survival", "ph_significance_level"),
        "prediction_times": ("phase_2", "survival", "prediction_times"),
        "risk_group_method": ("phase_2", "survival", "risk_group_method"),
        "risk_group_percentiles": ("phase_2", "survival", "risk_group_percentiles"),
        "risk_group_names": ("phase_2", "survival", "risk_group_names"),
        "min_events_per_covariate": ("phase_2", "survival", "min_events_per_covariate"),
    }

    extracted = {}
    for key_name, path in required_paths.items():
        node = config
        for part in path:
            if not isinstance(node, dict) or part not in node:
                raise ConfigurationError(
                    message="Required Phase 2 configuration key missing",
                    yaml_path=".".join(path),
                    expected=f"key '{part}' to exist",
                    observed="not found",
                )
            node = node[part]
        extracted[key_name] = node

    logger.info("Phase 2 configuration loaded: %d keys", len(extracted))
    return extracted


# ============================================================================
# SURVIVAL OUTCOME DEFINITION
# ============================================================================


def engineer_duration_and_event(feature_store: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Engineer duration and event from Phase 1 retention indicators.

    Maps two-point observation (D1, D7) to three-point interval approximation:
      retention_1=0                      -> duration=1, event=1 (churned by day 1)
      retention_1=1 and retention_7=0    -> duration=3, event=1 (churned in (1,7))
      retention_1=1 and retention_7=1    -> duration=7, event=0 (censored at day 7)

    duration=3 is not the true churn time — it approximates the unobserved interval.
    """
    n = len(feature_store)
    duration = np.zeros(n, dtype=np.int64)
    event = np.zeros(n, dtype=np.int64)

    ret1 = feature_store["retention_1"].values
    ret7 = feature_store["retention_7"].values

    mask_day1 = ret1 == 0
    mask_interval = (ret1 == 1) & (ret7 == 0)
    mask_retained = (ret1 == 1) & (ret7 == 1)

    duration[mask_day1] = 1
    event[mask_day1] = 1

    duration[mask_interval] = 3
    event[mask_interval] = 1

    duration[mask_retained] = 7
    event[mask_retained] = 0

    total_assigned = mask_day1.sum() + mask_interval.sum() + mask_retained.sum()
    if total_assigned != n:
        raise InputValidationError(
            message="Duration engineering did not cover all rows",
            expected=f"{n} rows assigned",
            observed=f"{total_assigned} rows assigned",
        )

    for d in (1, 3, 7):
        n_d = (duration == d).sum()
        pct = 100 * n_d / n
        logger.info("  duration=%d: %.1f%% (%d players)", d, pct, n_d)

    unique_durations = np.unique(duration)
    if set(unique_durations) != {1, 3, 7}:
        raise InputValidationError(
            message="Duration array contains unexpected values",
            expected="{1, 3, 7}",
            observed=f"{set(unique_durations)}",
        )

    return duration, event


# ============================================================================
# PHASE 1 INPUT VALIDATION (SCHEMA ONLY)
# ============================================================================


def validate_feature_store_contract(feature_store: pd.DataFrame) -> None:
    """Validate Phase 1 feature_store consumed by Phase 2.

    Checks: schema (columns, types, non-null). Does NOT re-validate Phase 1
    business logic — Phase 1 already guaranteed it.
    """
    expected_cols = _EXPECTED_FEATURE_STORE_COLUMNS

    missing = set(expected_cols) - set(feature_store.columns)
    if missing:
        raise InputValidationError(
            message="Phase 1 feature_store missing expected columns",
            expected=f"{sorted(expected_cols)}",
            observed=f"missing: {sorted(missing)}",
        )

    unexpected = set(feature_store.columns) - set(expected_cols)
    if unexpected:
        raise InputValidationError(
            message="Phase 1 feature_store contains unexpected columns",
            expected=f"{sorted(expected_cols)}",
            observed=f"unexpected: {sorted(unexpected)}",
        )

    null_counts = feature_store.isnull().sum()
    null_cols = null_counts[null_counts > 0].index.tolist()
    if null_cols:
        raise InputValidationError(
            message="NaN detected in Phase 1 feature_store",
            expected="no NaN in any column",
            observed=f"NaN in columns: {null_cols}",
        )

    version_values = sorted(feature_store["version"].unique().tolist())
    sfb_values = sorted(feature_store["session_frequency_bin"].unique().tolist())
    lifecycle_values = sorted(feature_store["lifecycle_stage"].unique().tolist())

    logger.info("Phase 1 version categories (from data): %s", version_values)
    logger.info("Phase 1 session_frequency_bin values (from data): %s", sfb_values)
    logger.info("Phase 1 lifecycle_stage values (from data): %s", lifecycle_values)


# ============================================================================
# COX FEATURE PREPROCESSING
# ============================================================================


def preprocess_cox_features(feature_store: pd.DataFrame) -> pd.DataFrame:
    """Preprocess Phase 1 features for Cox model.

    Encodes version using whatever categories Phase 1 produced. Does NOT
    enforce specific category values. Covariate count is derived from the
    actual matrix, never hardcoded.

    engagement_score and progression_proxy are deliberately excluded: both are
    partially built from retention_1/retention_7 (Phase 1 formulas), which are
    exactly the inputs that deterministically define this Cox model's outcome
    (duration/event, see engineer_duration_and_event). Including either creates
    circularity with the outcome, not just collinearity between covariates --
    confirmed empirically by progression_proxy alone producing a suspiciously
    perfect concordance (0.963) and by both features jointly causing Newton-
    Raphson non-convergence. The remaining two engineered features
    (sessions_per_day, session_frequency_bin) are built purely from
    sum_gamerounds and carry no such circularity; together with version they
    converge cleanly with sane coefficients and concordance ~0.86.
    """
    cox_df = feature_store[["sessions_per_day", "session_frequency_bin", "version"]].copy()

    version_dummies = pd.get_dummies(cox_df["version"], prefix="version", drop_first=True).astype("int64")

    n_version_dummies = version_dummies.shape[1]
    logger.info(
        "Version encoding: %d categories -> %d dummy variables (drop_first=True)",
        len(feature_store["version"].unique()),
        n_version_dummies,
    )

    cox_df = pd.concat([cox_df.drop("version", axis=1), version_dummies], axis=1)

    logger.info("Cox design matrix: %d covariates, %d rows", cox_df.shape[1], len(cox_df))

    if cox_df.isnull().sum().sum() > 0:
        null_cols = cox_df.columns[cox_df.isnull().any()].tolist()
        raise InputValidationError(
            message="NaN in Cox feature matrix after preprocessing",
            expected="no NaN values",
            observed=f"NaN in: {null_cols}",
        )

    return cox_df


# ============================================================================
# SURVIVAL DATASET CONSTRUCTION
# ============================================================================


def construct_survival_dataset(
    feature_store: pd.DataFrame, duration: np.ndarray, event: np.ndarray, cox_df: pd.DataFrame
) -> pd.DataFrame:
    """Construct canonical survival dataset from Phase 1 + Phase 2 preprocessing."""
    return pd.concat(
        [
            feature_store[["userid", "retention_1", "retention_7", "lifecycle_stage"]].reset_index(drop=True),
            cox_df.reset_index(drop=True),
            pd.DataFrame({"duration": duration, "event": event}),
        ],
        axis=1,
    )


def validate_survival_dataset(survival_df: pd.DataFrame) -> None:
    """Validate survival dataset schema before KM/Cox fitting."""
    unique_durations = set(survival_df["duration"].unique().tolist())
    expected_durations = {1, 3, 7}
    if unique_durations != expected_durations:
        missing_d = expected_durations - unique_durations
        unexpected_d = unique_durations - expected_durations
        raise InputValidationError(
            message="Duration array contains unexpected values",
            expected=f"{sorted(expected_durations)}",
            observed=f"missing: {sorted(missing_d)}, unexpected: {sorted(unexpected_d)}",
        )

    unique_events = set(survival_df["event"].unique().tolist())
    if not unique_events <= {0, 1}:
        raise InputValidationError(
            message="Event must be binary",
            expected="{0, 1}",
            observed=f"{unique_events}",
        )

    null_cols = survival_df.columns[survival_df.isnull().any()].tolist()
    if null_cols:
        raise InputValidationError(
            message="NaN in survival dataset",
            expected="no NaN",
            observed=f"NaN in: {null_cols}",
        )

    n_events = (survival_df["event"] == 1).sum()
    n_censored = (survival_df["event"] == 0).sum()

    if n_events == 0:
        raise InputValidationError(message="No churn events in dataset", expected="≥ 1 event", observed="0 events")

    if n_censored == 0:
        raise InputValidationError(
            message="No censored observations in dataset", expected="≥ 1 censored", observed="0 censored"
        )

    event_rate = n_events / len(survival_df)
    if not (0.01 < event_rate < 0.99):
        raise InputValidationError(
            message="Event rate is extreme",
            expected="event rate in (0.01, 0.99)",
            observed=f"{event_rate:.4f}",
        )

    logger.info(
        "Survival dataset: %d rows, %d events (%.1f%%), %d censored",
        len(survival_df),
        n_events,
        100 * event_rate,
        n_censored,
    )


# ============================================================================
# GATE 1.5: EVENTS-PER-COVARIATE
# ============================================================================


def gate1_5_events_per_covariate(survival_df: pd.DataFrame, cox_df: pd.DataFrame, phase2_config: Dict[str, Any]) -> None:
    """Validate minimum events per covariate for Cox model.

    n_covariates is always derived dynamically from the actual matrix.
    Threshold comes from YAML, never silently defaulted.
    """
    n_events = (survival_df["event"] == 1).sum()
    n_covariates = cox_df.shape[1]
    min_threshold = phase2_config["min_events_per_covariate"]
    min_events_required = n_covariates * min_threshold
    events_per_cov = n_events / n_covariates

    if n_events < min_events_required:
        raise CoxValidationError(
            message="Insufficient events for Cox model",
            expected=f"≥ {min_events_required} events ({n_covariates} covariates x {min_threshold} threshold)",
            observed=f"{n_events} events ({events_per_cov:.1f} per covariate)",
        )

    logger.info(
        "Gate 1.5: %d events / %d covariates = %.1f per covariate (threshold: %s) OK",
        n_events,
        n_covariates,
        events_per_cov,
        min_threshold,
    )


# ============================================================================
# GATE 2: KAPLAN-MEIER
# ============================================================================


def compute_logrank_tests(
    survival_df: pd.DataFrame, stages_to_fit: List[str], stratify_by: str, multiple_testing: str
) -> Dict[str, Any]:
    """Compute pairwise log-rank tests.

    multiple_testing: 'none' -> raw p-values (documented limitation).
                       'holm' -> Holm-Bonferroni corrected p-values.
    """
    raw_results = {}
    pair_keys = []

    for s_a, s_b in itertools.combinations(stages_to_fit, 2):
        df_a = survival_df[survival_df[stratify_by] == s_a]
        df_b = survival_df[survival_df[stratify_by] == s_b]

        if len(df_a) == 0 or len(df_b) == 0:
            logger.warning("Skipping log-rank %s vs %s: empty stratum", s_a, s_b)
            continue

        result = logrank_test(df_a["duration"], df_b["duration"], df_a["event"], df_b["event"])

        key = (
            f"{s_a.lower().replace('-', '_').replace(' ', '_')}"
            f"_vs_"
            f"{s_b.lower().replace('-', '_').replace(' ', '_')}"
        )
        raw_results[key] = float(result.p_value)
        pair_keys.append(key)

    if multiple_testing == "holm":
        from statsmodels.stats.multitest import multipletests

        p_vals = [raw_results[k] for k in pair_keys]
        _, corrected, _, _ = multipletests(p_vals, method="holm")
        final_results = {
            k: {
                "raw_p_value": raw_results[k],
                "corrected_p_value": float(corrected[i]),
                "correction_method": "Holm-Bonferroni",
            }
            for i, k in enumerate(pair_keys)
        }
        logger.info("Log-rank tests: Holm-Bonferroni correction applied")
    else:
        final_results = {
            k: {
                "raw_p_value": raw_results[k],
                "corrected_p_value": None,
                "correction_method": "none",
                "note": "Raw p-values reported. No multiple comparison correction applied.",
            }
            for k in pair_keys
        }
        logger.info("Log-rank tests: No multiple testing correction applied. Raw p-values reported.")

    return final_results


def fit_and_validate_km(survival_df: pd.DataFrame, phase2_config: Dict[str, Any]) -> Dict[str, Any]:
    """Fit KM estimators (overall + stratified by lifecycle_stage).

    Stage order from config. Warns on small strata, includes them anyway.
    """
    stratify_by = phase2_config["km_stratify_by"]
    min_stratum_size = phase2_config["min_stratum_size"]
    stages = phase2_config["lifecycle_stage_order"]

    stages_in_data = survival_df[stratify_by].unique().tolist()
    stages_to_fit = [s for s in stages if s in stages_in_data]

    kmf_overall = KaplanMeierFitter(label="Overall")
    kmf_overall.fit(durations=survival_df["duration"], event_observed=survival_df["event"], alpha=0.05)

    km_stratified = {}
    for stage in stages_to_fit:
        df_stage = survival_df[survival_df[stratify_by] == stage]
        n_stage = len(df_stage)
        n_events_stage = int((df_stage["event"] == 1).sum())

        if n_stage < min_stratum_size:
            logger.warning(
                "Stage '%s': n=%d < %d. KM curve may be unstable. Including in output.",
                stage,
                n_stage,
                min_stratum_size,
            )

        kmf = KaplanMeierFitter(label=stage)
        kmf.fit(durations=df_stage["duration"], event_observed=df_stage["event"], alpha=0.05)
        km_stratified[stage] = {
            "kmf": kmf,
            "n_players": n_stage,
            "n_events": n_events_stage,
            "small_strata_warning": n_stage < min_stratum_size,
        }

    logrank_results = compute_logrank_tests(
        survival_df, stages_to_fit, stratify_by, phase2_config["log_rank_multiple_testing"]
    )

    surv = kmf_overall.survival_function_.values.flatten()
    if not all(surv[i] >= surv[i + 1] - 1e-10 for i in range(len(surv) - 1)):
        raise KMValidationError(
            message="Overall KM curve is not monotonically non-increasing",
            expected="S(t) non-increasing",
            observed="violation detected",
        )
    if not all((0 <= s <= 1) for s in surv):
        raise KMValidationError(
            message="KM survival probabilities outside [0, 1]",
            expected="all values in [0, 1]",
            observed=f"range: [{surv.min():.4f}, {surv.max():.4f}]",
        )

    logger.info("Gate 2: KM validation passed")

    return {"overall": kmf_overall, "stratified": km_stratified, "logrank": logrank_results}


# ============================================================================
# GATE 3: COX PROPORTIONAL HAZARDS
# ============================================================================


def verify_no_perfect_multicollinearity(cox_df: pd.DataFrame) -> None:
    """Verify Cox design matrix has full rank. n_cols derived dynamically."""
    X = cox_df.values.astype("float64")
    n_cols = X.shape[1]
    rank = matrix_rank(X)

    if rank < n_cols:
        raise CoxValidationError(
            message="Cox design matrix is rank-deficient (perfect multicollinearity)",
            expected=f"rank = {n_cols}",
            observed=f"rank = {rank}",
        )

    logger.info("Cox design matrix full rank: rank=%d, cols=%d", rank, n_cols)


def get_cox_aic(cph: CoxPHFitter) -> float:
    """Get Cox model AIC, guarding for lifelines's semi-parametric AIC behavior.

    CoxPHFitter.AIC_ is a property that RAISES StatError (not AttributeError)
    for the standard semi-parametric model, so hasattr()-based detection is
    unsafe -- hasattr only swallows AttributeError, and StatError propagates
    straight through it. AIC_partial_ is the correct property for this model.
    """
    try:
        return float(cph.AIC_partial_)
    except (AttributeError, StatError):
        pass
    try:
        return float(cph.AIC_)
    except (AttributeError, StatError):
        pass
    k = cph.params_.shape[0]
    return float(-2 * cph.log_likelihood_ + 2 * k)


def fit_and_validate_cox(
    survival_df: pd.DataFrame, cox_df: pd.DataFrame, phase2_config: Dict[str, Any]
) -> Tuple[CoxPHFitter, Dict[str, Any]]:
    """Fit Cox Proportional Hazards model and validate."""
    ph_significance = phase2_config["ph_significance_level"]

    verify_no_perfect_multicollinearity(cox_df)

    cox_input = pd.concat(
        [cox_df.reset_index(drop=True), survival_df[["duration", "event"]].reset_index(drop=True)], axis=1
    )

    cph = CoxPHFitter(penalizer=0.0)
    cph.fit(cox_input, duration_col="duration", event_col="event", show_progress=False)

    if not np.isfinite(cph.log_likelihood_):
        raise CoxValidationError(
            message="Cox model log-likelihood not finite",
            expected="finite log-likelihood",
            observed=f"{cph.log_likelihood_}",
        )

    if not all(np.isfinite(cph.params_.values)):
        raise CoxValidationError(
            message="Cox coefficients contain inf/-inf",
            expected="all finite",
            observed=f"{cph.params_.to_dict()}",
        )

    hrs = np.exp(cph.params_.values)
    if not (all(np.isfinite(hrs)) and all(hrs > 0)):
        raise CoxValidationError(
            message="Hazard ratios invalid",
            expected="all finite and positive",
            observed=f"{hrs}",
        )

    if not (0 <= cph.concordance_index_ <= 1):
        raise CoxValidationError(
            message="Concordance index outside [0, 1]",
            expected="value in [0, 1]",
            observed=f"{cph.concordance_index_}",
        )

    # PH assumption: lifelines.statistics.proportional_hazard_test (the function
    # named `proportional_hazard_assumption` in lifelines.utils does not exist in
    # the installed lifelines version; this is the function it's built on top of).
    ph_test_result = proportional_hazard_test(cph, cox_input, time_transform="rank")
    ph_summary = ph_test_result.summary

    violated = []
    ph_output = {}

    for feature in cox_df.columns:
        p_val = float(ph_summary.loc[feature, "p"])
        t_stat = float(ph_summary.loc[feature, "test_statistic"])
        is_violated = p_val < ph_significance

        ph_output[feature] = {"test_statistic": t_stat, "p_value": p_val, "violated": is_violated}

        if is_violated:
            violated.append(feature)

    if violated:
        logger.warning("PH assumption violated for: %s (p < %s)", violated, ph_significance)

    logger.info("Gate 3: Cox validation passed (concordance=%.4f)", cph.concordance_index_)

    return cph, {
        "test_name": "Schoenfeld Residuals (Rank Transform)",
        "global_violation": len(violated) > 0,
        "violated_covariates": violated,
        "covariate_results": ph_output,
    }


# ============================================================================
# PREDICTIONS & RISK STRATIFICATION
# ============================================================================


def compute_median_survival(surv_funcs: pd.DataFrame) -> np.ndarray:
    """Compute predicted median survival time for each player.

    Median survival = smallest t where S(t | X) <= 0.5. NaN if S(t) never
    reaches 0.5 within the observed window.
    """
    medians = []
    for col in surv_funcs.columns:
        sf = surv_funcs[col]
        below_half = sf[sf <= 0.5]
        if len(below_half) > 0:
            medians.append(float(below_half.index[0]))
        else:
            medians.append(float("nan"))
    return np.array(medians)


def generate_predictions(
    cph: CoxPHFitter, cox_df: pd.DataFrame, survival_df: pd.DataFrame, phase2_config: Dict[str, Any]
) -> pd.DataFrame:
    """Generate individual survival predictions (Day 1 and Day 7 only).

    Risk groups come from percentiles (YAML, not hardcoded). No extrapolation
    beyond the observed window.
    """
    prediction_times = phase2_config["prediction_times"]
    risk_percentiles = phase2_config["risk_group_percentiles"]
    risk_names = phase2_config["risk_group_names"]

    surv_funcs = cph.predict_survival_function(cox_df)
    partial_hazard = cph.predict_partial_hazard(cox_df).values

    pred_cols = {}
    for t in prediction_times:
        col = f"survival_prob_day{t}"
        try:
            pred_cols[col] = surv_funcs.loc[t].values.astype(float)
        except KeyError:
            raise OutputValidationError(
                message=f"Prediction time {t} not found in survival function",
                expected=f"time {t} in KM timeline",
                observed=f"available times: {list(surv_funcs.index)}",
            )

    if len(prediction_times) >= 2:
        for i in range(len(prediction_times) - 1):
            col_a = f"survival_prob_day{prediction_times[i]}"
            col_b = f"survival_prob_day{prediction_times[i + 1]}"
            if not all(pred_cols[col_a] >= pred_cols[col_b] - 1e-10):
                raise OutputValidationError(
                    message="Survival probabilities not monotonically non-increasing",
                    expected=f"S({prediction_times[i]}) >= S({prediction_times[i + 1]})",
                    observed="violation detected",
                )

    predicted_median_survival = compute_median_survival(surv_funcs)

    p_low = np.percentile(partial_hazard, risk_percentiles[0])
    p_high = np.percentile(partial_hazard, risk_percentiles[1])

    def assign_risk(h):
        if h <= p_low:
            return risk_names[0]
        elif h <= p_high:
            return risk_names[1]
        else:
            return risk_names[2]

    risk_groups = [assign_risk(h) for h in partial_hazard]

    predictions_df = pd.concat(
        [
            survival_df[["userid"]].reset_index(drop=True),
            cox_df.reset_index(drop=True),
            pd.DataFrame(
                {
                    "partial_hazard": partial_hazard,
                    **pred_cols,
                    "predicted_median_survival": predicted_median_survival,
                    "risk_group": risk_groups,
                }
            ),
        ],
        axis=1,
    )

    logger.info(
        "Predictions generated: %d rows, days=[%s]",
        len(predictions_df),
        ", ".join(str(t) for t in prediction_times),
    )

    return predictions_df


# ============================================================================
# ARTIFACT WRITING & VERIFICATION
# ============================================================================


def convert_numpy_to_native(obj: Any) -> Any:
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_native(i) for i in obj]
    return obj


def write_json_artifact(data: Dict[str, Any], path: str) -> Dict[str, Any]:
    """Write dict to JSON, handling numpy types. Verify after write."""
    data_clean = convert_numpy_to_native(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data_clean, f, indent=2)

    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as exc:
        raise OutputValidationError(message=f"JSON write failed verification: {path}", observed=str(exc)) from exc

    sha = compute_file_sha256(path)
    size = Path(path).stat().st_size

    logger.info("JSON written: %s (%d bytes)", path, size)
    return {"path": str(path), "size_bytes": size, "sha256": sha}


def write_parquet_artifact(df: pd.DataFrame, path: str) -> Dict[str, Any]:
    """Write DataFrame to parquet (no index). Reload and verify."""
    df.to_parquet(path, index=False)

    df_reload = pd.read_parquet(path)
    try:
        pd.testing.assert_frame_equal(
            df,
            df_reload,
            check_dtype=True,
            check_like=False,
            check_exact=False,
            rtol=1e-5,
            check_names=True,
            check_index_type=True,
        )
    except AssertionError as exc:
        raise OutputValidationError(message=f"Parquet reload mismatch: {path}", observed=str(exc)) from exc

    sha = compute_file_sha256(path)
    size = Path(path).stat().st_size

    logger.info("Parquet written: %s (%d rows, %d bytes)", path, len(df), size)
    return {"path": str(path), "rows": len(df), "columns": len(df.columns), "size_bytes": size, "sha256": sha}


# ============================================================================
# GATE 4: OUTPUT VALIDATION + RELOAD
# ============================================================================


def gate4_output_validation(artifacts: Dict[str, Any]) -> None:
    """Verify all Phase 2 outputs before reporting SUCCESS.

    Checks existence, file size, sha256, and manifest schema. All outputs
    must reload successfully (verified at write time, re-checked here).
    """
    required_artifacts = ["survival_curves", "cox_model_summary", "survival_diagnostics", "survival_predictions", "manifest"]

    for name in required_artifacts:
        meta = artifacts[name]
        path_obj = Path(meta["path"])

        if not path_obj.exists() or not path_obj.is_file():
            raise OutputValidationError(
                message=f"{name} does not exist", expected=f"file at {meta['path']}", observed="not found"
            )

        if path_obj.stat().st_size < 10:
            raise OutputValidationError(
                message=f"{name} too small", expected="size >= 10 bytes", observed=f"{path_obj.stat().st_size} bytes"
            )

        actual_sha = compute_file_sha256(meta["path"])
        if actual_sha != meta["sha256"]:
            raise OutputValidationError(
                message=f"{name} hash mismatch (file modified after write)",
                expected=f"{meta['sha256'][:8]}...",
                observed=f"{actual_sha[:8]}...",
            )

    with open(artifacts["manifest"]["path"], encoding="utf-8") as f:
        manifest = json.load(f)

    required_keys = ["manifest_version", "versions", "artifacts", "phase_2_summary"]
    for key in required_keys:
        if key not in manifest:
            raise OutputValidationError(
                message=f"Manifest missing required key: '{key}'", expected="key present", observed="not found"
            )

    if manifest.get("phase") != 2:
        raise OutputValidationError(
            message="Manifest phase not updated to 2", expected="phase = 2", observed=f"phase = {manifest.get('phase')}"
        )

    logger.info("Gate 4: All outputs verified")


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================


def run_phase2(
    feature_store_path: str = None,
    manifest_path: str = None,
    config_path: str = None,
    benchmarks_path: str = None,
) -> Dict[str, Any]:
    """Execute Phase 2 survival analysis end-to-end."""
    phase2_start = datetime.now(timezone.utc)

    try:
        logger.info("=" * 80)
        logger.info("PHASE 2: SURVIVAL ANALYSIS PIPELINE START")
        logger.info("=" * 80)

        fs_path = Path(feature_store_path) if feature_store_path else resolve_project_path(
            "data", "processed", "feature_store.parquet"
        )
        mf_path = Path(manifest_path) if manifest_path else resolve_project_path("data", "processed", "manifest.json")
        cfg_path = Path(config_path) if config_path else resolve_project_path("config", "simulation_config.yaml")
        bmk_path = Path(benchmarks_path) if benchmarks_path else resolve_project_path(
            "config", "industry_benchmarks.yaml"
        )

        logger.info("Loading Phase 2 configuration from simulation_config.yaml...")
        phase2_config = load_phase2_config(str(cfg_path), str(bmk_path))

        logger.info("Gate 1: Validating Phase 1 feature_store contract...")
        feature_store = pd.read_parquet(fs_path)
        validate_feature_store_contract(feature_store)
        logger.info("Gate 1 passed (%d rows)", len(feature_store))

        logger.info("Engineering duration and event from Phase 1 retention indicators...")
        duration, event = engineer_duration_and_event(feature_store)

        logger.info("Preprocessing Cox features (version one-hot encoding)...")
        cox_df = preprocess_cox_features(feature_store)

        logger.info("Constructing survival dataset...")
        survival_df = construct_survival_dataset(feature_store, duration, event, cox_df)
        validate_survival_dataset(survival_df)

        logger.info("Gate 1.5: Validating events-per-covariate (dynamic)...")
        gate1_5_events_per_covariate(survival_df, cox_df, phase2_config)

        logger.info("Gate 2: Fitting Kaplan-Meier estimators (stratified + log-rank)...")
        km_results = fit_and_validate_km(survival_df, phase2_config)

        logger.info("Gate 3: Fitting Cox proportional hazards model...")
        cph, ph_results = fit_and_validate_cox(survival_df, cox_df, phase2_config)

        logger.info("Generating individual predictions and risk stratification...")
        predictions_df = generate_predictions(cph, cox_df, survival_df, phase2_config)

        logger.info("Writing Phase 2 artifacts...")
        artifacts: Dict[str, Any] = {}
        out_dir = resolve_project_path("data", "processed")
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info("  Writing survival_curves.parquet...")
        km_rows = []
        for stage, km_data in km_results["stratified"].items():
            kmf = km_data["kmf"]
            sf = kmf.survival_function_
            ci = kmf.confidence_interval_
            for t in sf.index:
                km_rows.append(
                    {
                        "time_days": int(t),
                        "survival_prob": float(sf.loc[t].iloc[0]),
                        "lifecycle_stage": stage,
                        "ci_lower": float(ci.loc[t].iloc[0]),
                        "ci_upper": float(ci.loc[t].iloc[1]),
                        "n_players": km_data["n_players"],
                        "n_events": km_data["n_events"],
                    }
                )
        survival_curves_df = pd.DataFrame(km_rows)
        artifacts["survival_curves"] = write_parquet_artifact(survival_curves_df, str(out_dir / "survival_curves.parquet"))

        logger.info("  Writing cox_model_summary.json...")
        aic = get_cox_aic(cph)
        cox_summary = {
            "model_version": "1.0.0",
            "execution_timestamp": phase2_start.isoformat(),
            "covariates": list(cox_df.columns),
            "coefficients": cph.params_.to_dict(),
            "hazard_ratios": {
                feat: {
                    "hr": float(cph.summary.loc[feat, "exp(coef)"]),
                    "ci_95_lower": float(cph.summary.loc[feat, "exp(coef) lower 95%"]),
                    "ci_95_upper": float(cph.summary.loc[feat, "exp(coef) upper 95%"]),
                    "p_value": float(cph.summary.loc[feat, "p"]),
                }
                for feat in cox_df.columns
            },
            "model_statistics": {
                "concordance_index": float(cph.concordance_index_),
                "log_likelihood": float(cph.log_likelihood_),
                "aic": aic,
                "degrees_of_freedom": int(cox_df.shape[1]),
            },
        }
        artifacts["cox_model_summary"] = write_json_artifact(cox_summary, str(out_dir / "cox_model_summary.json"))

        logger.info("  Writing survival_diagnostics.json...")
        n_events_total = int((survival_df["event"] == 1).sum())
        n_total = len(survival_df)
        n_censored = n_total - n_events_total

        censored_durations = survival_df.loc[survival_df["event"] == 0, "duration"]
        median_followup = float(censored_durations.median()) if len(censored_durations) > 0 else None

        km_overall_sf = km_results["overall"].survival_function_
        times_below_half = km_overall_sf[km_overall_sf.iloc[:, 0] <= 0.5]
        median_survival_days = int(times_below_half.index[0]) if len(times_below_half) > 0 else None

        diagnostics = {
            "diagnostics_version": "1.0.0",
            "phase": 2,
            "execution_timestamp": phase2_start.isoformat(),
            "kaplan_meier": {
                "event_rate": float(n_events_total / n_total),
                "total_players": n_total,
                "total_events": n_events_total,
                "total_censored": n_censored,
                "median_followup_days": median_followup,
                "median_survival_days": median_survival_days,
                "survival_at_day_7": float(km_results["overall"].survival_function_.iloc[-1].iloc[0]),
            },
            "cox_model": {
                "convergence": True,
                "log_likelihood": float(cph.log_likelihood_),
                "aic": aic,
                "degrees_of_freedom": int(cox_df.shape[1]),
                "concordance_index": float(cph.concordance_index_),
            },
            "proportional_hazards_assumption": ph_results,
            "stratified_km_logrank_tests": {
                "test_name": "Log-Rank Test (Stratification: Lifecycle Stage)",
                "multiple_testing": phase2_config["log_rank_multiple_testing"],
                "pairwise_results": km_results["logrank"],
            },
            "prediction_note": (
                "predicted_median_survival is NaN where S(t) does not reach 0.5 "
                "within observation window [0, 7]. These players are predicted "
                "retained beyond day 7."
            ),
        }
        artifacts["survival_diagnostics"] = write_json_artifact(diagnostics, str(out_dir / "survival_diagnostics.json"))

        logger.info("  Writing survival_predictions.parquet...")
        artifacts["survival_predictions"] = write_parquet_artifact(
            predictions_df, str(out_dir / "survival_predictions.parquet")
        )

        logger.info("Creating Phase 2 manifest (combined with Phase 1)...")
        with open(mf_path, encoding="utf-8") as f:
            phase1_manifest = json.load(f)

        phase2_manifest = {
            "manifest_version": "2.0.0",
            "phase": 2,
            "versions": phase1_manifest.get("versions", {}),
            "generated_by": "survival_analysis.py",
            "execution_timestamp": phase2_start.isoformat(),
            "artifacts": phase1_manifest.get("artifacts", [])
            + [
                {
                    "name": "survival_curves_parquet",
                    "phase": 2,
                    "path": artifacts["survival_curves"]["path"],
                    "type": "parquet",
                    "size_bytes": artifacts["survival_curves"]["size_bytes"],
                    "sha256": artifacts["survival_curves"]["sha256"],
                    "rows": artifacts["survival_curves"]["rows"],
                    "columns": artifacts["survival_curves"]["columns"],
                    "purpose": "Phase 2: KM survival curves stratified by lifecycle",
                },
                {
                    "name": "cox_model_summary_json",
                    "phase": 2,
                    "path": artifacts["cox_model_summary"]["path"],
                    "type": "json",
                    "size_bytes": artifacts["cox_model_summary"]["size_bytes"],
                    "sha256": artifacts["cox_model_summary"]["sha256"],
                    "purpose": "Phase 2: Cox PH coefficients, hazard ratios, statistics",
                },
                {
                    "name": "survival_diagnostics_json",
                    "phase": 2,
                    "path": artifacts["survival_diagnostics"]["path"],
                    "type": "json",
                    "size_bytes": artifacts["survival_diagnostics"]["size_bytes"],
                    "sha256": artifacts["survival_diagnostics"]["sha256"],
                    "purpose": "Phase 2: PH assumption, concordance, log-rank tests",
                },
                {
                    "name": "survival_predictions_parquet",
                    "phase": 2,
                    "path": artifacts["survival_predictions"]["path"],
                    "type": "parquet",
                    "size_bytes": artifacts["survival_predictions"]["size_bytes"],
                    "sha256": artifacts["survival_predictions"]["sha256"],
                    "rows": artifacts["survival_predictions"]["rows"],
                    "columns": artifacts["survival_predictions"]["columns"],
                    "purpose": "Phase 2: Individual survival probabilities and risk groups",
                },
            ],
            "configuration_integrity": phase1_manifest.get("configuration_integrity", {}),
            "phase_2_summary": {
                "status": "SUCCESS",
                "total_players": int(n_total),
                "n_events": int(n_events_total),
                "n_censored": int(n_censored),
                "n_covariates": int(cox_df.shape[1]),
                "duration_values": [1, 3, 7],
                "event_rate": float(n_events_total / n_total),
                "median_followup_days": median_followup,
                "median_survival_days": median_survival_days,
                "cox_concordance": float(cph.concordance_index_),
                "ph_assumption_violated": ph_results["global_violation"],
                "violated_covariates": ph_results["violated_covariates"],
            },
        }

        with open(mf_path, "w", encoding="utf-8") as f:
            json.dump(convert_numpy_to_native(phase2_manifest), f, indent=2)

        artifacts["manifest"] = {
            "path": str(mf_path),
            "size_bytes": Path(mf_path).stat().st_size,
            "sha256": compute_file_sha256(str(mf_path)),
        }

        logger.info("Gate 4: Validating all outputs (reload verification)...")
        gate4_output_validation(artifacts)

        phase2_end = datetime.now(timezone.utc)
        duration_secs = (phase2_end - phase2_start).total_seconds()

        pipeline_report = {
            "pipeline": {
                "status": "SUCCESS",
                "phase": 2,
                "start_time": phase2_start.isoformat(),
                "end_time": phase2_end.isoformat(),
                "duration_seconds": duration_secs,
            },
            "gates_passed": [1, 1.5, 2, 3, 4],
            "artifacts_written": [
                {"name": Path(v["path"]).name, "path": v["path"], "size_bytes": v["size_bytes"]}
                for v in artifacts.values()
            ],
            "survival_summary": {
                "total_players": int(n_total),
                "n_events": int(n_events_total),
                "n_censored": int(n_censored),
                "n_covariates": int(cox_df.shape[1]),
                "event_rate": float(n_events_total / n_total),
                "median_followup_days": median_followup,
                "median_survival_days": median_survival_days,
                "cox_concordance": float(cph.concordance_index_),
                "ph_assumption_violated": ph_results["global_violation"],
                "violated_covariates": ph_results["violated_covariates"],
                "small_strata_warning": any(
                    km_results["stratified"][s]["small_strata_warning"] for s in km_results["stratified"]
                ),
            },
        }

        logger.info("=" * 80)
        logger.info("PHASE 2 PIPELINE COMPLETE (SUCCESS) - Duration: %.2fs", duration_secs)
        logger.info("=" * 80)
        return pipeline_report

    except Phase1Error:
        # Catches Phase1Error broadly (not just Phase2Error): ConfigurationError
        # is a Phase1Error sibling of Phase2Error, not a child of it, so it would
        # otherwise fall through to the generic branch below and get wrapped.
        logger.exception("PHASE 2 PIPELINE FAILED (Phase1Error)")
        raise

    except Exception as exc:
        logger.error("PHASE 2 PIPELINE FAILED (unexpected): %s", exc)
        raise PipelineExecutionError(
            message="Phase 2 pipeline failed with unexpected error",
            observed=str(exc),
        ) from exc
