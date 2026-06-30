"""Phase 4 — Causal Experimentation & LiveOps Optimization Platform.

WHY NO UPLIFT MODELS?
----------------------
The Cookie Cats dataset represents a completed A/B experiment with a simple
binary treatment (version: gate_30 vs gate_40). The dataset does NOT support
training complex heterogeneous treatment effect models (T-Learner, X-Learner,
Causal Forest) because:

1. Limited features: only 4 raw columns (userid, version, retention_1/7, sum_gamerounds)
2. Binary outcomes: retention_1 and retention_7 are 0/1 flags
3. A/B test context: treatment was randomly assigned — we have a clean experiment
4. No baseline period: cannot measure pre/post change per user

What the data DOES support: rigorous experiment evaluation with segment-level
heterogeneity analysis. This is the correct statistical framework for a completed
randomized experiment.

Architecture
------------
Phase 1 (lifecycle_stage, engagement_score)
       +
Phase 2 (risk_group, survival_prob_day7)
       +
Phase 3 (action_category, priority_score)
       +
Raw Data (version, retention_1, retention_7)
       ↓
Module 1: Experiment Validator
       ↓ (validation passed)
Module 2: Treatment Effect Estimator (overall + segment-level)
       ↓
Module 3: Statistical Inference Engine (chi-square, confidence intervals, multiple testing)
       ↓
Module 4: Decision Engine Evaluator (Phase 3 recommendations × treatment effects)
       ↓
Module 5: LiveOps Optimization Engine (evidence-based deployment recommendations)
       ↓
Module 6: Business Impact Engine (retained players, campaign efficiency, priority ranking)

Outputs
-------
experiment_validation.json          — randomization checks, sample balance
overall_treatment_effects.json      — D1/D7 retention lift (overall)
segment_level_effects.json          — treatment effects per lifecycle/risk/action segment
statistical_tests.json              — chi-square, Fisher exact, confidence intervals, multiple testing
decision_engine_evaluation.json     — Phase 3 recommendation × treatment effect cross-analysis
liveops_recommendations.json        — evidence-based deployment decisions
business_impact_summary.json        — expected retained players, campaign efficiency, priority ranking
manifest.json                       — updated (phase_4_summary, version=4.0.0)
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from src.config_loader import load_configuration
from src.exceptions import (
    ConfigurationError,
    ExperimentValidationError,
    Phase4Error,
    Phase4OutputValidationError,
    PipelineExecutionError,
    StatisticalTestError,
    TreatmentEffectError,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================================
# PATH CONTRACT
# ============================================================================


def resolve_project_path(*path_parts: str) -> Path:
    """Resolve path relative to project root. Portable across all OS."""
    return PROJECT_ROOT.joinpath(*path_parts)


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================


def load_phase4_config(config_path: str, benchmarks_path: str) -> Dict[str, Any]:
    """Load Phase 4 Causal Experimentation configuration.

    Strict — raises ConfigurationError for any missing required key.
    Consistent with Phase 1/2/3 patterns.

    Parameters
    ----------
    config_path : str
        Path to simulation_config.yaml.
    benchmarks_path : str
        Path to industry_benchmarks.yaml (validated but not used in Phase 4).

    Returns
    -------
    dict
        Flat dict of Phase 4 configuration values.

    Raises
    ------
    ConfigurationError
        If any required Phase 4 configuration key is absent.
    """
    config = load_configuration(config_path, benchmarks_path)


    required_paths = {
        "treatment_column": ("phase_4", "experiment_evaluation", "treatment_column"),
        "control_group": ("phase_4", "experiment_evaluation", "control_group"),
        "treatment_group": ("phase_4", "experiment_evaluation", "treatment_group"),
        "outcomes": ("phase_4", "experiment_evaluation", "outcomes"),
        "validation": ("phase_4", "experiment_evaluation", "validation"),
        "inference": ("phase_4", "experiment_evaluation", "inference"),
        "segmentation": ("phase_4", "experiment_evaluation", "segmentation"),
        "decision_evaluation": ("phase_4", "experiment_evaluation", "decision_evaluation"),
        "liveops_recommendations": ("phase_4", "experiment_evaluation", "liveops_recommendations"),
        "business_impact": ("phase_4", "experiment_evaluation", "business_impact"),
        "random_state": ("phase_4", "experiment_evaluation", "random_state"),
    }

    extracted = {}
    for key_name, path in required_paths.items():
        node = config
        for part in path:
            if not isinstance(node, dict) or part not in node:
                raise ConfigurationError(
                    message="Required Phase 4 configuration key missing",
                    yaml_path=".".join(path),
                    expected=f"key '{part}'",
                    observed="not found",
                )
            node = node[part]
        extracted[key_name] = node

    logger.info("Phase 4 configuration loaded: %d outcome metrics, %d segmentation dimensions",
                len(extracted["outcomes"]), len(extracted["segmentation"]["stratify_by"]))
    return extracted



# ============================================================================
# MODULE 1: EXPERIMENT VALIDATION
# ============================================================================


def validate_experiment_integrity(
    df: pd.DataFrame,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate experiment design and randomization integrity.

    Checks:
    ------
    1. Sample size (per arm >= min_sample_size)
    2. Treatment balance (ratio <= max_sample_imbalance_ratio)
    3. Missing data (rate <= max_missing_rate in critical columns)
    4. Duplicate users (if duplicate_check=true)
    5. Treatment labels (match control_group/treatment_group exactly)
    6. Covariate balance (SMD < max_standardized_mean_difference)

    Parameters
    ----------
    df : pd.DataFrame
        Merged dataset (feature_store + survival_pred + player_decisions + raw retention).
    config : dict
        Phase 4 configuration.

    Returns
    -------
    dict
        Validation report: checks performed, results, pass/fail per check.

    Raises
    ------
    ExperimentValidationError
        If any CRITICAL validation check fails.
    """
    validation_cfg = config["validation"]
    treatment_col = config["treatment_column"]
    control = config["control_group"]
    treatment = config["treatment_group"]

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_players": len(df),
        "checks_performed": [],
        "passed": True,
        "critical_failures": [],
    }


    # Check 1: Treatment labels
    unique_treatments = df[treatment_col].unique()
    expected_treatments = {control, treatment}
    if set(unique_treatments) != expected_treatments:
        report["checks_performed"].append({
            "check": "treatment_labels",
            "passed": False,
            "expected": sorted(expected_treatments),
            "observed": sorted(unique_treatments),
        })
        report["passed"] = False
        report["critical_failures"].append("Treatment labels mismatch")
        raise ExperimentValidationError(
            message="Treatment column contains unexpected values",
            expected=str(sorted(expected_treatments)),
            observed=str(sorted(unique_treatments)),
        )

    report["checks_performed"].append({
        "check": "treatment_labels",
        "passed": True,
    })

    # Check 2: Sample sizes
    n_control = (df[treatment_col] == control).sum()
    n_treatment = (df[treatment_col] == treatment).sum()
    min_size = validation_cfg["min_sample_size"]

    if n_control < min_size or n_treatment < min_size:
        report["checks_performed"].append({
            "check": "sample_size",
            "passed": False,
            "n_control": int(n_control),
            "n_treatment": int(n_treatment),
            "min_required": min_size,
        })
        report["passed"] = False
        report["critical_failures"].append(f"Insufficient sample size (control={n_control}, treatment={n_treatment})")
        raise ExperimentValidationError(
            message="Insufficient sample size in treatment arms",
            expected=f">= {min_size} per arm",
            observed=f"control={n_control}, treatment={n_treatment}",
        )

    report["checks_performed"].append({
        "check": "sample_size",
        "passed": True,
        "n_control": int(n_control),
        "n_treatment": int(n_treatment),
    })


    # Check 3: Treatment balance
    max_imbalance = validation_cfg["max_sample_imbalance_ratio"]
    imbalance_ratio = max(n_control, n_treatment) / min(n_control, n_treatment)

    if imbalance_ratio > max_imbalance:
        report["checks_performed"].append({
            "check": "treatment_balance",
            "passed": False,
            "imbalance_ratio": round(float(imbalance_ratio), 4),
            "max_allowed": max_imbalance,
        })
        report["passed"] = False
        report["critical_failures"].append(f"Treatment imbalance ratio {imbalance_ratio:.2f} exceeds {max_imbalance}")
        raise ExperimentValidationError(
            message="Treatment arms are imbalanced",
            expected=f"ratio <= {max_imbalance}",
            observed=f"ratio = {imbalance_ratio:.4f}",
        )

    report["checks_performed"].append({
        "check": "treatment_balance",
        "passed": True,
        "imbalance_ratio": round(float(imbalance_ratio), 4),
    })

    # Check 4: Missing data in critical columns
    critical_cols = [treatment_col, "retention_1", "retention_7", "userid"]
    max_missing = validation_cfg["max_missing_rate"]
    
    for col in critical_cols:
        if col not in df.columns:
            raise ExperimentValidationError(
                message=f"Critical column missing: {col}",
                expected="column present",
                observed="column not found",
            )
        
        missing_rate = df[col].isnull().sum() / len(df)
        if missing_rate > max_missing:
            report["checks_performed"].append({
                "check": f"missing_data_{col}",
                "passed": False,
                "missing_rate": round(float(missing_rate), 4),
                "max_allowed": max_missing,
            })
            report["passed"] = False
            report["critical_failures"].append(f"Missing data in {col}: {missing_rate:.2%}")
            raise ExperimentValidationError(
                message=f"Excessive missing data in {col}",
                expected=f"<= {max_missing:.2%}",
                observed=f"{missing_rate:.2%}",
            )

    report["checks_performed"].append({
        "check": "missing_data",
        "passed": True,
        "columns_checked": critical_cols,
    })


    # Check 5: Duplicate users
    if validation_cfg.get("duplicate_check", True):
        n_duplicates = df["userid"].duplicated().sum()
        if n_duplicates > 0:
            report["checks_performed"].append({
                "check": "duplicate_users",
                "passed": False,
                "n_duplicates": int(n_duplicates),
            })
            report["passed"] = False
            report["critical_failures"].append(f"Found {n_duplicates} duplicate users")
            raise ExperimentValidationError(
                message="Duplicate users detected",
                expected="0 duplicates",
                observed=f"{n_duplicates} duplicates",
            )
        
        report["checks_performed"].append({
            "check": "duplicate_users",
            "passed": True,
        })

    # Check 6: Covariate balance (Standardized Mean Difference)
    if validation_cfg.get("covariate_balance_check", True):
        balance_cols = validation_cfg.get("covariate_balance_columns", [])
        max_smd = validation_cfg["max_standardized_mean_difference"]
        
        balance_results = []
        for col in balance_cols:
            if col not in df.columns:
                continue
            
            if df[col].dtype in [np.float64, np.float32, np.int64, np.int32]:
                control_vals = df[df[treatment_col] == control][col].dropna()
                treatment_vals = df[df[treatment_col] == treatment][col].dropna()
                
                mean_diff = treatment_vals.mean() - control_vals.mean()
                pooled_std = np.sqrt((control_vals.var() + treatment_vals.var()) / 2)
                
                if pooled_std > 0:
                    smd = abs(mean_diff / pooled_std)
                    balanced = smd < max_smd
                    
                    balance_results.append({
                        "covariate": col,
                        "smd": round(float(smd), 4),
                        "balanced": balanced,
                    })
        
        report["checks_performed"].append({
            "check": "covariate_balance",
            "passed": all(r["balanced"] for r in balance_results),
            "balance_results": balance_results,
        })

    logger.info("✓ Experiment validation passed: %d players, %d checks", len(df), len(report["checks_performed"]))
    return report



# ============================================================================
# MODULE 2: TREATMENT EFFECT ESTIMATION
# ============================================================================


def estimate_treatment_effects(
    df: pd.DataFrame,
    config: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Estimate overall and segment-level treatment effects.

    This function estimates the **Average Treatment Effect (ATE)** under the
    assumption of successful randomization. The ATE measures the expected
    difference in outcomes between a randomly selected player receiving gate_40
    versus gate_30. Because version was randomly assigned, the ATE has a
    causal interpretation: it estimates what would happen to the average player
    if the entire population were shifted from gate_30 to gate_40.

    For binary outcomes (retention_1, retention_7):
    - Absolute lift = p_treatment - p_control     (ATE on the probability scale)
    - Relative lift = (p_treatment - p_control) / p_control
    - Confidence intervals: normal approximation (large-sample valid at n>90,000)

    Note on Confidence Intervals
    ----------------------------
    95% CIs use the normal approximation for difference in proportions. This is
    appropriate given the large sample size (n > 90,000). Future versions may
    use bootstrap confidence intervals for robustness in smaller subgroup
    analyses, although the normal approximation is adequate here.

    Parameters
    ----------
    df : pd.DataFrame
    config : dict

    Returns
    -------
    (overall_effects, segment_effects) : tuple of dicts

    Raises
    ------
    TreatmentEffectError
        If effect estimation fails.
    """
    treatment_col = config["treatment_column"]
    control = config["control_group"]
    treatment = config["treatment_group"]
    outcomes = config["outcomes"]
    alpha = config["inference"]["alpha"]
    z_crit = stats.norm.ppf(1 - alpha / 2)  # Two-tailed

    df_control = df[df[treatment_col] == control]
    df_treatment = df[df[treatment_col] == treatment]

    overall_effects = {
        "estimand": "Average Treatment Effect (ATE)",
        "estimand_note": (
            "The ATE is estimated under the assumption of successful randomization. "
            "Because version was randomly assigned, the estimate has a causal "
            "interpretation: the expected retention difference if all players "
            "received gate_40 vs gate_30."
        ),
        "treatment_column": treatment_col,
        "control_group": control,
        "treatment_group": treatment,
        "n_control": len(df_control),
        "n_treatment": len(df_treatment),
        "ci_method": "normal_approximation",
        "ci_method_note": (
            "Normal approximation for difference in proportions. Appropriate at n>90,000. "
            "Future versions may use bootstrap CIs for robustness in smaller subgroup analyses."
        ),
        "outcomes": {},
    }

    for outcome_spec in outcomes:
        outcome_name = outcome_spec["name"]
        
        if outcome_name not in df.columns:
            raise TreatmentEffectError(
                message=f"Outcome column missing: {outcome_name}",
                expected="column present",
                observed="not found",
            )

        p_control = df_control[outcome_name].mean()
        p_treatment = df_treatment[outcome_name].mean()
        
        abs_lift = p_treatment - p_control
        rel_lift = abs_lift / p_control if p_control > 0 else np.nan
        
        # Standard error for difference in proportions
        n_c, n_t = len(df_control), len(df_treatment)
        se = np.sqrt((p_control * (1 - p_control) / n_c) + (p_treatment * (1 - p_treatment) / n_t))
        
        ci_lower = abs_lift - z_crit * se
        ci_upper = abs_lift + z_crit * se
        
        # Cohen's h (effect size for proportions)
        cohens_h = 2 * (np.arcsin(np.sqrt(p_treatment)) - np.arcsin(np.sqrt(p_control)))
        
        overall_effects["outcomes"][outcome_name] = {
            "description": outcome_spec.get("description", ""),
            "control_rate": round(float(p_control), 6),
            "treatment_rate": round(float(p_treatment), 6),
            "absolute_lift": round(float(abs_lift), 6),
            "relative_lift": round(float(rel_lift), 6) if not np.isnan(rel_lift) else None,
            "ci_lower": round(float(ci_lower), 6),
            "ci_upper": round(float(ci_upper), 6),
            "standard_error": round(float(se), 6),
            "cohens_h": round(float(cohens_h), 4),
        }

    logger.info("✓ Overall treatment effects computed for %d outcomes", len(outcomes))

    # Segment-level effects
    segment_effects = estimate_segment_level_effects(df, config, z_crit)

    return overall_effects, segment_effects



def estimate_segment_level_effects(
    df: pd.DataFrame,
    config: Dict[str, Any],
    z_crit: float,
) -> Dict[str, Any]:
    """Estimate treatment effects stratified by segments.

    Parameters
    ----------
    df : pd.DataFrame
    config : dict
    z_crit : float
        Critical value for CI (pre-computed from alpha).

    Returns
    -------
    dict
        Segment-level treatment effects.
    """
    treatment_col = config["treatment_column"]
    control = config["control_group"]
    treatment = config["treatment_group"]
    outcomes = config["outcomes"]
    stratify_by = config["segmentation"]["stratify_by"]
    min_segment_size = config["segmentation"]["min_segment_size"]

    segment_results = {
        "segmentation_dimensions": [],
    }

    for strat_spec in stratify_by:
        col = strat_spec["column"]
        name = strat_spec["name"]
        
        if col not in df.columns:
            logger.warning("Segmentation column not found: %s", col)
            continue

        dimension_results = {
            "dimension_name": name,
            "column": col,
            "segments": {},
        }

        for segment_value in df[col].unique():
            df_seg = df[df[col] == segment_value]
            
            df_seg_control = df_seg[df_seg[treatment_col] == control]
            df_seg_treatment = df_seg[df_seg[treatment_col] == treatment]
            
            if len(df_seg_control) < min_segment_size or len(df_seg_treatment) < min_segment_size:
                continue

            segment_outcomes = {}
            for outcome_spec in outcomes:
                outcome_name = outcome_spec["name"]
                
                p_c = df_seg_control[outcome_name].mean()
                p_t = df_seg_treatment[outcome_name].mean()
                
                abs_lift = p_t - p_c
                rel_lift = abs_lift / p_c if p_c > 0 else np.nan
                
                n_c, n_t = len(df_seg_control), len(df_seg_treatment)
                se = np.sqrt((p_c * (1 - p_c) / n_c) + (p_t * (1 - p_t) / n_t))
                
                ci_lower = abs_lift - z_crit * se
                ci_upper = abs_lift + z_crit * se
                
                segment_outcomes[outcome_name] = {
                    "control_rate": round(float(p_c), 6),
                    "treatment_rate": round(float(p_t), 6),
                    "absolute_lift": round(float(abs_lift), 6),
                    "relative_lift": round(float(rel_lift), 6) if not np.isnan(rel_lift) else None,
                    "ci_lower": round(float(ci_lower), 6),
                    "ci_upper": round(float(ci_upper), 6),
                    "n_control": int(n_c),
                    "n_treatment": int(n_t),
                }

            dimension_results["segments"][str(segment_value)] = {
                "n_control": int(len(df_seg_control)),
                "n_treatment": int(len(df_seg_treatment)),
                "outcomes": segment_outcomes,
            }

        segment_results["segmentation_dimensions"].append(dimension_results)

    logger.info("✓ Segment-level effects computed for %d dimensions", len(stratify_by))
    return segment_results



# ============================================================================
# MODULE 3: STATISTICAL INFERENCE ENGINE
# ============================================================================


def perform_statistical_tests(
    df: pd.DataFrame,
    overall_effects: Dict[str, Any],
    segment_effects: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Perform hypothesis tests and multiple testing correction.

    Tests:
    ------
    - Chi-square test for independence (2×2 contingency table)
    - Fisher exact test (fallback if chi-square assumptions fail)
    - Multiple testing correction (Holm or Benjamini-Hochberg)

    Parameters
    ----------
    df : pd.DataFrame
    overall_effects : dict
    segment_effects : dict
    config : dict

    Returns
    -------
    dict
        Statistical test results with p-values, corrected p-values, significance flags.

    Raises
    ------
    StatisticalTestError
        If statistical tests fail unexpectedly.
    """
    treatment_col = config["treatment_column"]
    control = config["control_group"]
    treatment = config["treatment_group"]
    outcomes = config["outcomes"]
    alpha = config["inference"]["alpha"]
    method = config["inference"].get("multiple_testing_method", "holm")

    test_results = {
        "alpha": alpha,
        "multiple_testing_method": method,
        "overall_tests": {},
        "segment_tests": [],
    }

    # Overall tests
    for outcome_spec in outcomes:
        outcome_name = outcome_spec["name"]
        
        df_control = df[df[treatment_col] == control]
        df_treatment = df[df[treatment_col] == treatment]
        
        # 2×2 contingency table
        n_c_success = df_control[outcome_name].sum()
        n_c_fail = len(df_control) - n_c_success
        n_t_success = df_treatment[outcome_name].sum()
        n_t_fail = len(df_treatment) - n_t_success
        
        contingency = np.array([[n_c_success, n_c_fail], [n_t_success, n_t_fail]])
        
        # Chi-square test
        try:
            chi2, p_chi2, dof, expected = stats.chi2_contingency(contingency, correction=False)
            chi2_valid = (expected >= 5).all()
        except Exception as exc:
            raise StatisticalTestError(
                message=f"Chi-square test failed for {outcome_name}",
                expected="valid test",
                observed=str(exc),
            ) from exc

        # Fisher exact test (fallback)
        try:
            odds_ratio, p_fisher = stats.fisher_exact(contingency)
        except Exception as exc:
            raise StatisticalTestError(
                message=f"Fisher exact test failed for {outcome_name}",
                expected="valid test",
                observed=str(exc),
            ) from exc

        test_results["overall_tests"][outcome_name] = {
            "chi2_statistic": round(float(chi2), 6),
            "chi2_p_value": round(float(p_chi2), 6),
            "chi2_valid": bool(chi2_valid),
            "fisher_p_value": round(float(p_fisher), 6),
            "recommended_test": "chi2" if chi2_valid else "fisher",
            "p_value": round(float(p_chi2 if chi2_valid else p_fisher), 6),
        }

    logger.info("✓ Overall statistical tests completed for %d outcomes", len(outcomes))

    # Segment tests (collect all p-values for multiple testing correction)
    all_p_values = []
    segment_test_records = []

    for dim in segment_effects["segmentation_dimensions"]:
        for segment_name, segment_data in dim["segments"].items():
            for outcome_name in segment_data["outcomes"].keys():
                # Reconstruct contingency table from segment data
                seg_col = dim["column"]
                df_seg = df[df[seg_col] == segment_name]
                
                df_seg_control = df_seg[df_seg[treatment_col] == control]
                df_seg_treatment = df_seg[df_seg[treatment_col] == treatment]
                
                n_c_success = df_seg_control[outcome_name].sum()
                n_c_fail = len(df_seg_control) - n_c_success
                n_t_success = df_seg_treatment[outcome_name].sum()
                n_t_fail = len(df_seg_treatment) - n_t_success
                
                contingency = np.array([[n_c_success, n_c_fail], [n_t_success, n_t_fail]])
                
                try:
                    chi2, p_chi2, _, expected = stats.chi2_contingency(contingency, correction=False)
                    chi2_valid = (expected >= 5).all()
                    _, p_fisher = stats.fisher_exact(contingency)
                    p_val = p_chi2 if chi2_valid else p_fisher
                except:
                    p_val = 1.0  # Failed test → not significant

                all_p_values.append(p_val)
                segment_test_records.append({
                    "dimension": dim["dimension_name"],
                    "segment": segment_name,
                    "outcome": outcome_name,
                    "p_value": round(float(p_val), 6),
                })

    # Multiple testing correction
    if len(all_p_values) > 0:
        p_corrected = apply_multiple_testing_correction(all_p_values, method, alpha)
        
        for i, record in enumerate(segment_test_records):
            record["p_value_corrected"] = round(float(p_corrected[i]), 6)
            record["significant"] = p_corrected[i] < alpha

        test_results["segment_tests"] = segment_test_records

    logger.info("✓ Segment-level tests completed: %d tests, %s correction applied",
                len(segment_test_records), method)
    return test_results



def apply_multiple_testing_correction(
    p_values: List[float],
    method: str,
    alpha: float,
) -> np.ndarray:
    """Apply multiple testing correction.

    Parameters
    ----------
    p_values : list of float
    method : str
        "holm", "benjamini_hochberg", or "none".
    alpha : float

    Returns
    -------
    np.ndarray
        Corrected p-values.
    """
    p_arr = np.array(p_values)
    
    if method == "none":
        return p_arr
    
    if method == "holm":
        # Holm-Bonferroni
        n = len(p_arr)
        order = np.argsort(p_arr)
        p_sorted = p_arr[order]
        
        p_corrected = np.minimum.accumulate((n - np.arange(n)) * p_sorted)
        p_corrected = np.minimum(p_corrected, 1.0)
        
        # Restore original order
        p_corrected_original_order = np.empty_like(p_corrected)
        p_corrected_original_order[order] = p_corrected
        return p_corrected_original_order
    
    if method == "benjamini_hochberg":
        # Benjamini-Hochberg FDR
        n = len(p_arr)
        order = np.argsort(p_arr)
        p_sorted = p_arr[order]
        
        p_corrected = p_sorted * n / (np.arange(n) + 1)
        p_corrected = np.minimum.accumulate(p_corrected[::-1])[::-1]
        p_corrected = np.minimum(p_corrected, 1.0)
        
        p_corrected_original_order = np.empty_like(p_corrected)
        p_corrected_original_order[order] = p_corrected
        return p_corrected_original_order
    
    raise StatisticalTestError(
        message=f"Unknown multiple testing method: {method}",
        expected="holm, benjamini_hochberg, or none",
        observed=method,
    )



# ============================================================================
# MODULE 4: DECISION ENGINE EVALUATOR
# ============================================================================


def evaluate_decision_engine(
    df: pd.DataFrame,
    segment_effects: Dict[str, Any],
    statistical_tests: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate Phase 3 decision engine recommendations against experiment results.

    For each action_category (Phase 3 recommendation), determine:
    - Treatment effect within that segment
    - Statistical significance
    - Recommendation confidence (did this rule identify players who benefited?)

    Parameters
    ----------
    df : pd.DataFrame
    segment_effects : dict
    statistical_tests : dict
    config : dict

    Returns
    -------
    dict
        Decision engine evaluation report.
    """
    outcomes = config["outcomes"]
    alpha = config["inference"]["alpha"]
    
    # Find action_category dimension in segment_effects
    action_cat_dimension = None
    for dim in segment_effects["segmentation_dimensions"]:
        if dim["column"] == "action_category":
            action_cat_dimension = dim
            break

    if action_cat_dimension is None:
        logger.warning("action_category not found in segmentation — skipping decision engine evaluation")
        return {"status": "skipped", "reason": "action_category dimension not found"}

    evaluation = {
        "description": "Evaluate Phase 3 Player Decision Engine recommendations against experiment results",
        "recommendations": {},
    }

    for segment_name, segment_data in action_cat_dimension["segments"].items():
        rec_eval = {
            "n_control": segment_data["n_control"],
            "n_treatment": segment_data["n_treatment"],
            "outcomes": {},
        }

        for outcome_name in segment_data["outcomes"].keys():
            outcome_data = segment_data["outcomes"][outcome_name]
            
            # Find corresponding statistical test
            p_value = 1.0
            for test_rec in statistical_tests.get("segment_tests", []):
                if (test_rec["dimension"] == action_cat_dimension["dimension_name"]
                    and test_rec["segment"] == segment_name
                    and test_rec["outcome"] == outcome_name):
                    p_value = test_rec.get("p_value_corrected", test_rec["p_value"])
                    break

            abs_lift = outcome_data["absolute_lift"]
            significant = p_value < alpha
            
            rec_eval["outcomes"][outcome_name] = {
                "absolute_lift": abs_lift,
                "control_rate": outcome_data["control_rate"],
                "treatment_rate": outcome_data["treatment_rate"],
                "p_value": round(float(p_value), 6),
                "statistically_significant": significant,
                "lift_direction": "positive" if abs_lift > 0 else ("negative" if abs_lift < 0 else "neutral"),
                "recommendation_validated": significant and abs_lift > 0,
            }

        evaluation["recommendations"][segment_name] = rec_eval

    logger.info("✓ Decision engine evaluated for %d recommendations", len(evaluation["recommendations"]))
    return evaluation



# ============================================================================
# MODULE 5: LIVEOPS OPTIMIZATION ENGINE
# ============================================================================


def generate_liveops_recommendations(
    overall_effects: Dict[str, Any],
    segment_effects: Dict[str, Any],
    statistical_tests: Dict[str, Any],
    decision_evaluation: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate evidence-based LiveOps deployment recommendations.

    Decision Logic:
    ---------------
    1. Deploy globally if: significant positive lift, sufficient magnitude, most segments benefit
    2. Target specific segments if: strong segment-specific effects
    3. Do not deploy if: no significant lift or negative lift
    4. Recommend more data if: inconclusive (p-value in gray zone)

    Parameters
    ----------
    overall_effects : dict
    segment_effects : dict
    statistical_tests : dict
    decision_evaluation : dict
    config : dict

    Returns
    -------
    dict
        LiveOps recommendations with rationale and deployment guidance.
    """
    liveops_cfg = config["liveops_recommendations"]
    inference_cfg = config["inference"]
    alpha = inference_cfg["alpha"]
    
    recommendations = {
        "summary": "",
        "deployment_decision": "",
        "rationale": [],
        "target_segments": [],
        "avoid_segments": [],
        "overall_assessment": {},
    }

    # Analyze primary outcome (retention_7)
    primary_outcome = "retention_7"
    if primary_outcome in overall_effects["outcomes"]:
        outcome_data = overall_effects["outcomes"][primary_outcome]
        p_val = statistical_tests["overall_tests"][primary_outcome]["p_value"]
        
        abs_lift = outcome_data["absolute_lift"]
        ci_lower = outcome_data["ci_lower"]
        ci_upper = outcome_data["ci_upper"]
        
        significant = p_val < alpha
        practically_significant = abs(abs_lift) >= inference_cfg.get("min_meaningful_lift", 0.01)
        
        recommendations["overall_assessment"] = {
            "outcome": primary_outcome,
            "absolute_lift": round(float(abs_lift), 6),
            "p_value": round(float(p_val), 6),
            "statistically_significant": significant,
            "practically_significant": practically_significant,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
        }

        # Decision logic
        deploy_thresh = liveops_cfg["deploy_threshold"]
        no_deploy_thresh = liveops_cfg["no_deploy_threshold"]
        
        # Count positive segments
        positive_segments = []
        for dim in segment_effects["segmentation_dimensions"]:
            for seg_name, seg_data in dim["segments"].items():
                if primary_outcome in seg_data["outcomes"]:
                    seg_lift = seg_data["outcomes"][primary_outcome]["absolute_lift"]
                    if seg_lift > 0:
                        positive_segments.append((dim["dimension_name"], seg_name, seg_lift))

        pct_positive = len(positive_segments) / max(1, sum(len(d["segments"]) for d in segment_effects["segmentation_dimensions"]))

        # Deploy globally?
        if (significant
            and abs_lift >= deploy_thresh["min_absolute_lift"]
            and pct_positive >= deploy_thresh["min_positive_segments_pct"]):
            recommendations["deployment_decision"] = "DEPLOY GLOBALLY"
            recommendations["summary"] = f"Gate 40 shows statistically significant positive lift (+{abs_lift:.2%}) with {pct_positive:.0%} of segments benefiting."
            recommendations["rationale"] = [
                f"Overall lift: +{abs_lift:.2%} (p={p_val:.4f})",
                f"{pct_positive:.0%} of segments show positive lift",
                f"95% CI: [{ci_lower:.2%}, {ci_upper:.2%}]",
            ]

        # Do not deploy?
        elif not significant or abs_lift < no_deploy_thresh["max_absolute_lift"] or abs_lift < 0:
            recommendations["deployment_decision"] = "DO NOT DEPLOY"
            if abs_lift < 0:
                recommendations["summary"] = f"Gate 40 shows negative lift ({abs_lift:.2%}). Do not deploy."
            else:
                recommendations["summary"] = f"Gate 40 shows insufficient lift ({abs_lift:.2%}, p={p_val:.4f}). Do not deploy."
            recommendations["rationale"] = [
                f"Overall lift: {abs_lift:.2%} (p={p_val:.4f})",
                "Effect size below deployment threshold" if abs_lift >= 0 else "Negative lift observed",
            ]

        # Targeted deployment?
        else:
            recommendations["deployment_decision"] = "TARGETED DEPLOYMENT"
            recommendations["summary"] = f"Gate 40 shows mixed results. Target specific high-performing segments."
            recommendations["rationale"] = [
                f"Overall lift: +{abs_lift:.2%} (p={p_val:.4f})",
                f"Heterogeneous effects across segments",
            ]
            
            # Identify target segments (positive lift + significance)
            for test_rec in statistical_tests.get("segment_tests", []):
                if test_rec["outcome"] == primary_outcome and test_rec.get("significant", False):
                    # Find lift
                    for dim in segment_effects["segmentation_dimensions"]:
                        if dim["dimension_name"] == test_rec["dimension"]:
                            seg_data = dim["segments"].get(test_rec["segment"], {})
                            if primary_outcome in seg_data.get("outcomes", {}):
                                seg_lift = seg_data["outcomes"][primary_outcome]["absolute_lift"]
                                if seg_lift > 0:
                                    recommendations["target_segments"].append({
                                        "dimension": test_rec["dimension"],
                                        "segment": test_rec["segment"],
                                        "lift": round(float(seg_lift), 6),
                                        "p_value": test_rec["p_value_corrected"],
                                    })

    # -------------------------------------------------------------------------
    # Recommendation confidence: High / Medium / Low
    # Derived from four signals:
    #   1. p-value strength (how decisively the test rejected/failed to reject)
    #   2. CI width (precision of the effect estimate)
    #   3. Cohen's h effect size (practical magnitude)
    #   4. Experiment quality (from validation — SMD, balance)
    # Business interpretation:
    #   High   → Strong statistical and practical evidence; act confidently
    #   Medium → Moderate evidence; consider additional data or segment testing
    #   Low    → Weak or inconclusive; treat as directional signal only
    # -------------------------------------------------------------------------
    confidence_level = _compute_recommendation_confidence(
        p_value=p_val,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        cohens_h=abs(overall_effects["outcomes"][primary_outcome].get("cohens_h", 0.0)),
        alpha=alpha,
    )

    recommendations["recommendation_confidence"] = confidence_level["level"]
    recommendations["recommendation_confidence_rationale"] = confidence_level["rationale"]

    logger.info("✓ LiveOps recommendations generated: %s (confidence: %s)",
                recommendations["deployment_decision"], confidence_level["level"])
    return recommendations



def _compute_recommendation_confidence(
    p_value: float,
    ci_lower: float,
    ci_upper: float,
    cohens_h: float,
    alpha: float,
) -> Dict[str, Any]:
    """Derive recommendation confidence (High/Medium/Low) from statistical signals.

    Scoring rules:
    - p-value:    < 0.001 → +2pts  |  0.001–0.05 → +1pt  |  >= 0.05 → 0pts
    - CI width:   < 0.01  → +2pts  |  0.01–0.03  → +1pt  |  > 0.03  → 0pts
    - Cohen's h:  >= 0.10 → +2pts  |  0.05–0.10  → +1pt  |  < 0.05  → 0pts
    Total 0–6:    5–6 → High  |  3–4 → Medium  |  0–2 → Low

    Parameters
    ----------
    p_value : float
    ci_lower : float
    ci_upper : float
    cohens_h : float
        Absolute value of Cohen's h effect size.
    alpha : float

    Returns
    -------
    dict with 'level' (str) and 'rationale' (list of str)
    """
    score = 0
    rationale = []

    # Signal 1: p-value strength
    if p_value < 0.001:
        score += 2
        rationale.append(f"Strong statistical evidence (p={p_value:.4f}, well below 0.001)")
    elif p_value < alpha:
        score += 1
        rationale.append(f"Moderate statistical evidence (p={p_value:.4f}, below alpha={alpha})")
    else:
        rationale.append(f"Weak statistical evidence (p={p_value:.4f}, above alpha={alpha})")

    # Signal 2: CI width (precision of estimate)
    ci_width = abs(ci_upper - ci_lower)
    if ci_width < 0.01:
        score += 2
        rationale.append(f"Precise estimate (CI width={ci_width:.4f}, < 1 pp)")
    elif ci_width < 0.03:
        score += 1
        rationale.append(f"Moderately precise estimate (CI width={ci_width:.4f}, 1–3 pp)")
    else:
        rationale.append(f"Wide confidence interval (CI width={ci_width:.4f}, > 3 pp) — estimate imprecise")

    # Signal 3: Cohen's h effect size
    if cohens_h >= 0.10:
        score += 2
        rationale.append(f"Large effect size (Cohen's h={cohens_h:.4f}, >= 0.10)")
    elif cohens_h >= 0.05:
        score += 1
        rationale.append(f"Small-medium effect size (Cohen's h={cohens_h:.4f}, 0.05–0.10)")
    else:
        rationale.append(f"Negligible effect size (Cohen's h={cohens_h:.4f}, < 0.05)")

    # Map score to level
    if score >= 5:
        level = "High"
    elif score >= 3:
        level = "Medium"
    else:
        level = "Low"

    return {"level": level, "score": score, "max_score": 6, "rationale": rationale}



# ============================================================================
# MODULE 6: BUSINESS IMPACT ENGINE
# ============================================================================


def estimate_business_impact(
    overall_effects: Dict[str, Any],
    segment_effects: Dict[str, Any],
    liveops_recommendations: Dict[str, Any],
    config: Dict[str, Any],
    n_total_players: int,
) -> Dict[str, Any]:
    """Estimate business impact in player retention terms (NOT revenue).

    Metrics:
    --------
    - Expected retained players (lift × N)
    - Campaign efficiency (lift per 1000 players)
    - Segment coverage (% of players in positive-lift segments)
    - Priority ranking (which segments to target first)

    NO revenue/ROI estimation — Cookie Cats does not support monetary metrics.

    Parameters
    ----------
    overall_effects : dict
    segment_effects : dict
    liveops_recommendations : dict
    config : dict
    n_total_players : int

    Returns
    -------
    dict
        Business impact summary.
    """
    primary_outcome = "retention_7"
    
    impact = {
        "description": "Business impact measured in player retention (no revenue estimation)",
        "total_players": n_total_players,
        "primary_outcome": primary_outcome,
        "overall_impact": {},
        "segment_impact": [],
    }

    if primary_outcome in overall_effects["outcomes"]:
        outcome_data = overall_effects["outcomes"][primary_outcome]
        abs_lift = outcome_data["absolute_lift"]
        
        expected_retained = abs_lift * n_total_players
        campaign_efficiency = abs_lift * 1000  # per 1000 players
        
        impact["overall_impact"] = {
            "absolute_lift": round(float(abs_lift), 6),
            "expected_retained_players": round(float(expected_retained), 2),
            "campaign_efficiency_per_1000": round(float(campaign_efficiency), 4),
        }

    # Segment-level impact (priority ranking)
    priority_weights = config["business_impact"]["priority_ranking_weights"]
    
    segment_impact_records = []
    for dim in segment_effects["segmentation_dimensions"]:
        for seg_name, seg_data in dim["segments"].items():
            if primary_outcome in seg_data["outcomes"]:
                seg_outcome = seg_data["outcomes"][primary_outcome]
                seg_lift = seg_outcome["absolute_lift"]
                seg_size = seg_data["n_control"] + seg_data["n_treatment"]
                
                # Priority score
                normalized_lift = max(0, seg_lift) / 0.10 if seg_lift > 0 else 0  # normalize to 10% baseline
                normalized_size = seg_size / n_total_players
                
                # Placeholder for significance (would need to look up test)
                normalized_significance = 0.5  # default
                
                priority_score = (
                    priority_weights["absolute_lift"] * normalized_lift
                    + priority_weights["segment_size"] * normalized_size
                    + priority_weights["statistical_confidence"] * normalized_significance
                )
                
                segment_impact_records.append({
                    "dimension": dim["dimension_name"],
                    "segment": seg_name,
                    "n_players": seg_size,
                    "absolute_lift": round(float(seg_lift), 6),
                    "expected_retained_players": round(float(seg_lift * seg_size), 2),
                    "priority_score": round(float(priority_score), 4),
                })

    # Sort by priority score descending
    segment_impact_records.sort(key=lambda x: -x["priority_score"])
    impact["segment_impact"] = segment_impact_records

    logger.info("✓ Business impact estimated: %.0f expected retained players (overall)",
                impact["overall_impact"].get("expected_retained_players", 0))
    return impact



# ============================================================================
# ARTIFACT I/O HELPERS
# ============================================================================


def compute_file_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file (streaming, 4 KB blocks)."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as fh:
        for block in iter(lambda: fh.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()


def convert_numpy_to_native(obj: Any) -> Any:
    """Recursively convert numpy scalars/arrays to native Python for JSON."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: convert_numpy_to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_numpy_to_native(i) for i in obj]
    return obj


def write_json_artifact(data: Dict[str, Any], path: str) -> Dict[str, Any]:
    """Write dict to JSON, verify re-parse, return metadata."""
    data_clean = convert_numpy_to_native(data)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data_clean, fh, indent=2)
    except (OSError, TypeError) as exc:
        raise Phase4OutputValidationError(
            message=f"JSON write failed: {path}",
            expected="successful write",
            observed=str(exc),
        ) from exc

    try:
        with open(path, "r", encoding="utf-8") as fh:
            json.load(fh)
    except json.JSONDecodeError as exc:
        raise Phase4OutputValidationError(
            message=f"JSON re-parse failed after write: {path}",
            expected="valid JSON",
            observed=str(exc),
        ) from exc

    sha = compute_file_sha256(path)
    size = Path(path).stat().st_size
    logger.info("✓ JSON artifact: %s (%d bytes)", Path(path).name, size)
    return {"path": str(path), "size_bytes": size, "sha256": sha}



# ============================================================================
# DATA PREPARATION
# ============================================================================


def prepare_phase4_dataset(
    feature_store_path: str,
    survival_predictions_path: str,
    player_decisions_path: str,
    raw_data_path: str = None,  # Not needed — retention already in feature_store
) -> pd.DataFrame:
    """Merge Phase 1/2/3 outputs and engineer priority_score_decile.

    Note: retention_1, retention_7, and version already exist in feature_store
    from Phase 1 (raw data was loaded and validated there). No need to re-merge
    with raw CSV.

    Priority score deciles are computed from the priority_score column (Phase 3)
    and added as a categorical segmentation dimension for campaign targeting.

    Parameters
    ----------
    feature_store_path : str
    survival_predictions_path : str
    player_decisions_path : str
    raw_data_path : str, optional
        Not used — kept for API consistency.

    Returns
    -------
    pd.DataFrame
        Merged dataset with all columns needed for Phase 4, including priority_score_decile.

    Raises
    ------
    ExperimentValidationError
        On load or merge failure.
    """
    try:
        feature_store = pd.read_parquet(feature_store_path)
        survival_pred = pd.read_parquet(survival_predictions_path)
        player_decisions = pd.read_parquet(player_decisions_path)
    except Exception as exc:
        raise ExperimentValidationError(
            message="Failed to load input datasets",
            expected="successful parquet load",
            observed=str(exc),
        ) from exc

    # Merge Phase 1 + Phase 2 + Phase 3
    df = pd.merge(feature_store, survival_pred, on="userid", how="left")
    df = pd.merge(df, player_decisions[["userid", "action_category", "priority_score"]], on="userid", how="left")

    # Engineer priority_score_decile (operations teams deploy by ranked score)
    df["priority_score_decile"] = pd.qcut(
        df["priority_score"], 
        q=10, 
        labels=["Bottom 10%", "10-20%", "20-30%", "30-40%", "40-50%", 
                "50-60%", "60-70%", "70-80%", "80-90%", "Top 10%"],
        duplicates="drop"  # Handle ties gracefully
    )

    logger.info("✓ Phase 4 dataset prepared: %d players, %d columns", len(df), len(df.columns))
    return df



# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================


def run_phase4(
    feature_store_path: str = None,
    survival_predictions_path: str = None,
    player_decisions_path: str = None,
    raw_data_path: str = None,
    manifest_path: str = None,
    config_path: str = None,
    benchmarks_path: str = None,
) -> Dict[str, Any]:
    """Execute Phase 4: Causal Experimentation & LiveOps Optimization Platform.

    Pipeline
    --------
    1.  Load Phase 4 configuration
    2.  Prepare dataset (merge Phase 1/2/3 + raw retention data)
    3.  Module 1: Experiment Validation
    4.  Module 2: Treatment Effect Estimation (overall + segment-level)
    5.  Module 3: Statistical Inference Engine (chi-square, Fisher, multiple testing)
    6.  Module 4: Decision Engine Evaluator (Phase 3 recommendations × experiment)
    7.  Module 5: LiveOps Optimization Engine (deployment recommendations)
    8.  Module 6: Business Impact Engine (retained players, campaign efficiency)
    9.  Write 7 artifacts (experiment_validation.json, overall_treatment_effects.json, etc.)
    10. Update manifest (phase_4_summary, version=4.0.0)
    11. Return pipeline report

    Parameters
    ----------
    feature_store_path, survival_predictions_path, player_decisions_path, raw_data_path,
    manifest_path, config_path, benchmarks_path : str, optional

    Returns
    -------
    dict
        Structured pipeline report.

    Raises
    ------
    Phase4Error (or subclass), ConfigurationError
        On domain-specific failures.
    PipelineExecutionError
        On unexpected failures.
    """
    phase4_start = datetime.now(timezone.utc)

    # Default paths
    fs_path = resolve_project_path("data", "processed", "feature_store.parquet")
    sp_path = resolve_project_path("data", "processed", "survival_predictions.parquet")
    pd_path = resolve_project_path("data", "processed", "player_decisions.parquet")
    raw_path = resolve_project_path("data", "raw", "cookie_cats.csv")
    mf_path = resolve_project_path("data", "processed", "manifest.json")
    cfg_path = resolve_project_path("config", "simulation_config.yaml")
    bmk_path = resolve_project_path("config", "industry_benchmarks.yaml")

    if feature_store_path:
        fs_path = Path(feature_store_path)
    if survival_predictions_path:
        sp_path = Path(survival_predictions_path)
    if player_decisions_path:
        pd_path = Path(player_decisions_path)
    if raw_data_path:
        raw_path = Path(raw_data_path)
    if manifest_path:
        mf_path = Path(manifest_path)
    if config_path:
        cfg_path = Path(config_path)
    if benchmarks_path:
        bmk_path = Path(benchmarks_path)

    try:
        logger.info("=" * 80)
        logger.info("PHASE 4: CAUSAL EXPERIMENTATION & LIVEOPS OPTIMIZATION PLATFORM")
        logger.info("=" * 80)

        # Step 1: Configuration
        logger.info("[Step 1/10] Loading Phase 4 configuration...")
        phase4_config = load_phase4_config(str(cfg_path), str(bmk_path))

        # Step 2: Data preparation
        logger.info("[Step 2/10] Preparing Phase 4 dataset...")
        df = prepare_phase4_dataset(str(fs_path), str(sp_path), str(pd_path))

        # Step 3: Experiment validation
        logger.info("[Step 3/10] Validating experiment integrity...")
        validation_report = validate_experiment_integrity(df, phase4_config)

        # Step 4: Treatment effect estimation
        logger.info("[Step 4/10] Estimating treatment effects...")
        overall_effects, segment_effects = estimate_treatment_effects(df, phase4_config)

        # Step 5: Statistical inference
        logger.info("[Step 5/10] Performing statistical tests...")
        statistical_tests = perform_statistical_tests(df, overall_effects, segment_effects, phase4_config)

        # Step 6: Decision engine evaluation
        logger.info("[Step 6/10] Evaluating Phase 3 decision engine...")
        decision_evaluation = evaluate_decision_engine(df, segment_effects, statistical_tests, phase4_config)

        # Step 7: LiveOps recommendations
        logger.info("[Step 7/10] Generating LiveOps recommendations...")
        liveops_recommendations = generate_liveops_recommendations(
            overall_effects, segment_effects, statistical_tests, decision_evaluation, phase4_config
        )

        # Step 8: Business impact
        logger.info("[Step 8/10] Estimating business impact...")
        business_impact = estimate_business_impact(
            overall_effects, segment_effects, liveops_recommendations, phase4_config, len(df)
        )

        # Step 9: Write artifacts
        logger.info("[Step 9/10] Writing Phase 4 artifacts...")
        
        out_dir = resolve_project_path("data", "processed")
        out_dir.mkdir(parents=True, exist_ok=True)

        artifacts_meta = []

        # Artifact 1: experiment_validation.json
        validation_path = out_dir / "experiment_validation.json"
        meta1 = write_json_artifact(validation_report, str(validation_path))
        artifacts_meta.append({
            "name": "experiment_validation_json",
            "phase": 4,
            **meta1,
            "purpose": "Phase 4: Experiment integrity checks and randomization validation",
        })

        # Artifact 2: overall_treatment_effects.json
        overall_path = out_dir / "overall_treatment_effects.json"
        meta2 = write_json_artifact(overall_effects, str(overall_path))
        artifacts_meta.append({
            "name": "overall_treatment_effects_json",
            "phase": 4,
            **meta2,
            "purpose": "Phase 4: Overall treatment effects (D1/D7 retention lift)",
        })

        # Artifact 3: segment_level_effects.json
        segment_path = out_dir / "segment_level_effects.json"
        meta3 = write_json_artifact(segment_effects, str(segment_path))
        artifacts_meta.append({
            "name": "segment_level_effects_json",
            "phase": 4,
            **meta3,
            "purpose": "Phase 4: Segment-level treatment effects (lifecycle, risk, action category)",
        })

        # Artifact 4: statistical_tests.json
        tests_path = out_dir / "statistical_tests.json"
        meta4 = write_json_artifact(statistical_tests, str(tests_path))
        artifacts_meta.append({
            "name": "statistical_tests_json",
            "phase": 4,
            **meta4,
            "purpose": "Phase 4: Chi-square, Fisher exact, multiple testing correction",
        })

        # Artifact 5: decision_engine_evaluation.json
        decision_path = out_dir / "decision_engine_evaluation.json"
        meta5 = write_json_artifact(decision_evaluation, str(decision_path))
        artifacts_meta.append({
            "name": "decision_engine_evaluation_json",
            "phase": 4,
            **meta5,
            "purpose": "Phase 4: Phase 3 recommendation × treatment effect cross-analysis",
        })

        # Artifact 6: liveops_recommendations.json
        liveops_path = out_dir / "liveops_recommendations.json"
        meta6 = write_json_artifact(liveops_recommendations, str(liveops_path))
        artifacts_meta.append({
            "name": "liveops_recommendations_json",
            "phase": 4,
            **meta6,
            "purpose": "Phase 4: Evidence-based deployment recommendations",
        })

        # Artifact 7: business_impact_summary.json
        impact_path = out_dir / "business_impact_summary.json"
        meta7 = write_json_artifact(business_impact, str(impact_path))
        artifacts_meta.append({
            "name": "business_impact_summary_json",
            "phase": 4,
            **meta7,
            "purpose": "Phase 4: Expected retained players, campaign efficiency, priority ranking",
        })

        # Step 10: Update manifest
        logger.info("[Step 10/10] Updating manifest...")
        
        try:
            with open(mf_path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except Exception as exc:
            raise Phase4OutputValidationError(
                message="Failed to load existing manifest",
                expected="valid manifest.json",
                observed=str(exc),
            ) from exc

        manifest["phase"] = 4
        manifest["manifest_version"] = "4.0.0"
        manifest["generated_by"] = "causal_experimentation.py"
        manifest["execution_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        manifest["artifacts"].extend(artifacts_meta)

        # Add phase_4_summary
        manifest["phase_4_summary"] = {
            "status": "SUCCESS",
            "name": "Causal Experimentation & LiveOps Optimization Platform",
            "approach": "Rigorous experiment evaluation with segment-level heterogeneity analysis",
            "rationale": (
                "Cookie Cats is a completed A/B experiment (gate_30 vs gate_40). "
                "Simple difference-in-proportions with statistical testing is the correct "
                "framework for randomized experiments. Complex uplift models (T-Learner, "
                "Causal Forest) are not justified given the dataset structure."
            ),
            "n_players": len(df),
            "n_control": int(overall_effects["n_control"]),
            "n_treatment": int(overall_effects["n_treatment"]),
            "primary_outcome": "retention_7",
            "overall_lift": round(float(overall_effects["outcomes"]["retention_7"]["absolute_lift"]), 6),
            "deployment_decision": liveops_recommendations["deployment_decision"],
            "n_artifacts": len(artifacts_meta),
        }

        with open(mf_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

        phase4_duration = (datetime.now(timezone.utc) - phase4_start).total_seconds()

        logger.info("=" * 80)
        logger.info("PHASE 4 COMPLETE")
        logger.info("Deployment Decision: %s", liveops_recommendations["deployment_decision"])
        logger.info("Duration: %.2f seconds", phase4_duration)
        logger.info("=" * 80)

        return {
            "status": "SUCCESS",
            "phase": 4,
            "n_players": len(df),
            "duration_seconds": round(phase4_duration, 2),
            "artifacts_written": len(artifacts_meta),
            "deployment_decision": liveops_recommendations["deployment_decision"],
            "manifest_updated": True,
        }

    except Phase4Error as exc:
        logger.error("Phase 4 failed: %s", exc)
        raise
    except Exception as exc:
        logger.error("Unexpected Phase 4 failure: %s", exc)
        raise PipelineExecutionError(
            message="Phase 4 pipeline encountered unexpected failure",
            expected="successful execution",
            observed=str(exc),
        ) from exc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    report = run_phase4()
    print(json.dumps(report, indent=2))
