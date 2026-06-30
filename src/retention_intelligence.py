"""Phase 3 — Player Decision Engine.

WHY NO ML MODEL?
----------------
Cookie Cats provides only: retention_1, retention_7, sum_gamerounds, version.

The natural regression target would be sessions_per_day × 7 (a 7-day session
proxy). However, sessions_per_day is also the strongest available predictor.
Any regression model trained on this setup learns y = 7x — identity mapping,
not prediction. A linear model achieves R² ≈ 1.0 trivially; tree-based models
approximate the same linear function less precisely and lose. SHAP then shows
that sessions_per_day dominates, which is mathematically guaranteed. None of
this is analytically meaningful.

The correct question is not "can we predict sessions_per_day × 7 from
sessions_per_day?" (trivially yes), but "given what we know about each player,
who should we act on, how urgently, and with what intervention?"

Cookie Cats does justify this: Phase 1 provides lifecycle segmentation.
Phase 2 provides churn risk stratification. Together, they define a complete
decision-support framework for LiveOps targeting.

Architecture
------------
Phase 1 (lifecycle_stage, engagement_score, sessions_per_day)
       +
Phase 2 (risk_group, survival_prob_day7, partial_hazard)
       ↓
Priority Score (weighted composite: engagement × risk × session intensity)
       +
Business Rules Engine (YAML-configured action categories, first-match-wins)
       ↓
Player Decisions (action_category, priority_score, intervention per player)
       +
Segment Summary (aggregate stats per category)
       +
Decision Rules Audit (rule coverage, priority distributions)

Outputs
-------
player_decisions.parquet  — per-player assignments (N × 9 columns)
segment_summary.json      — per-category aggregated statistics
decision_rules.json       — audit trail: rule coverage, P-score distributions
manifest.json             — updated (phase_3_summary, version=3.0.0)
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from src.config_loader import load_configuration
from src.exceptions import (
    ConfigurationError,
    DataPreparationError,
    ModelValidationError,
    Phase3Error,
    PipelineExecutionError,
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


def load_phase3_config(config_path: str, benchmarks_path: str) -> Dict[str, Any]:
    """Load Phase 3 Player Decision Engine configuration.

    Strict — raises ConfigurationError for any missing required key.
    Never silently defaults. Consistent with Phase 1 and Phase 2 patterns.

    Parameters
    ----------
    config_path : str
        Path to simulation_config.yaml.
    benchmarks_path : str
        Path to industry_benchmarks.yaml (validated but not returned).

    Returns
    -------
    dict
        Flat dict of Phase 3 configuration values.

    Raises
    ------
    ConfigurationError
        If any required Phase 3 configuration key is absent.
    """
    config = load_configuration(config_path, benchmarks_path)

    required_paths = {
        "priority_score_weights": (
            "phase_3", "player_decision_engine", "priority_score_weights"
        ),
        "action_categories": (
            "phase_3", "player_decision_engine", "action_categories"
        ),
        "random_state": (
            "phase_3", "player_decision_engine", "random_state"
        ),
        "min_samples": (
            "phase_3", "player_decision_engine", "min_samples"
        ),
    }

    extracted = {}
    for key_name, path in required_paths.items():
        node = config
        for part in path:
            if not isinstance(node, dict) or part not in node:
                raise ConfigurationError(
                    message="Required Phase 3 configuration key missing",
                    yaml_path=".".join(path),
                    expected=f"key '{part}'",
                    observed="not found",
                )
            node = node[part]
        extracted[key_name] = node

    # Validate priority score weights sum to 1.0
    weights = extracted["priority_score_weights"]
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 1e-6:
        raise ConfigurationError(
            message="priority_score_weights must sum to 1.0",
            yaml_path="phase_3.player_decision_engine.priority_score_weights",
            expected="sum = 1.0",
            observed=f"sum = {weight_sum:.6f}",
        )

    # Validate action_categories is a non-empty list
    categories = extracted["action_categories"]
    if not isinstance(categories, list) or len(categories) == 0:
        raise ConfigurationError(
            message="action_categories must be a non-empty list",
            yaml_path="phase_3.player_decision_engine.action_categories",
            expected="list with at least one entry",
            observed=type(categories).__name__,
        )

    logger.info("Phase 3 configuration loaded: %d action categories", len(categories))
    return extracted


# ============================================================================
# INPUT VALIDATION (SCHEMA ONLY)
# ============================================================================


def validate_phase2_outputs(
    survival_predictions_path: str,
    feature_store_path: str,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Validate Phase 1 feature store and Phase 2 survival predictions.

    Schema-only: checks columns and null values in critical fields.
    Does not re-validate Phase 1 business rules — Phase 1 already guaranteed those.

    Returns
    -------
    (feature_store, survival_pred) : tuple of DataFrames

    Raises
    ------
    DataPreparationError
        If either file is missing, unreadable, or fails schema validation.
    """
    try:
        survival_pred = pd.read_parquet(survival_predictions_path)
    except Exception as exc:
        raise DataPreparationError(
            message="Failed to load survival_predictions.parquet",
            expected="valid parquet file",
            observed=str(exc),
        ) from exc

    try:
        feature_store = pd.read_parquet(feature_store_path)
    except Exception as exc:
        raise DataPreparationError(
            message="Failed to load feature_store.parquet",
            expected="valid parquet file",
            observed=str(exc),
        ) from exc

    # Phase 2 schema
    expected_p2 = [
        "userid", "partial_hazard", "survival_prob_day7",
        "predicted_median_survival", "risk_group",
    ]
    missing_p2 = set(expected_p2) - set(survival_pred.columns)
    if missing_p2:
        raise DataPreparationError(
            message="Phase 2 survival_predictions columns missing",
            expected=str(sorted(expected_p2)),
            observed=f"missing: {sorted(missing_p2)}",
        )

    # Phase 1 schema (need lifecycle_stage and engagement_score for decision engine)
    expected_p1 = [
        "userid", "sessions_per_day", "session_frequency_bin",
        "version", "engagement_score", "lifecycle_stage",
    ]
    missing_p1 = set(expected_p1) - set(feature_store.columns)
    if missing_p1:
        raise DataPreparationError(
            message="Phase 1 feature_store columns missing",
            expected=str(sorted(expected_p1)),
            observed=f"missing: {sorted(missing_p1)}",
        )

    # Non-null checks on critical columns
    for col in ["userid", "partial_hazard", "risk_group", "survival_prob_day7"]:
        if survival_pred[col].isnull().any():
            raise DataPreparationError(
                message=f"NaN values in critical Phase 2 column: {col}",
                expected="no NaN",
                observed=f"NaN count: {survival_pred[col].isnull().sum()}",
            )

    for col in ["userid", "sessions_per_day", "engagement_score", "lifecycle_stage"]:
        if feature_store[col].isnull().any():
            raise DataPreparationError(
                message=f"NaN values in critical Phase 1 column: {col}",
                expected="no NaN",
                observed=f"NaN count: {feature_store[col].isnull().sum()}",
            )

    logger.info(
        "✓ Inputs validated — Phase 1: %d rows | Phase 2: %d rows",
        len(feature_store),
        len(survival_pred),
    )
    return feature_store, survival_pred


# ============================================================================
# PROFILE BUILDER
# ============================================================================


def build_player_profiles(
    feature_store: pd.DataFrame,
    survival_pred: pd.DataFrame,
    min_samples: int,
) -> pd.DataFrame:
    """Merge Phase 1 and Phase 2 into a unified player profile table.

    Parameters
    ----------
    feature_store : pd.DataFrame
        Phase 1 output (N × 10).
    survival_pred : pd.DataFrame
        Phase 2 output.
    min_samples : int
        Minimum rows required to proceed.

    Returns
    -------
    pd.DataFrame
        Merged profile with columns:
        userid, lifecycle_stage, risk_group, engagement_score,
        sessions_per_day, survival_prob_day7, partial_hazard, version

    Raises
    ------
    DataPreparationError
        On merge failure, unexpected NaN, or insufficient samples.
    """
    if len(feature_store) < min_samples:
        raise DataPreparationError(
            message="Insufficient players for Phase 3",
            expected=f">= {min_samples}",
            observed=f"{len(feature_store)} rows",
        )

    p1_cols = [
        "userid", "lifecycle_stage", "engagement_score",
        "sessions_per_day", "session_frequency_bin", "version",
    ]
    p2_cols = [
        "userid", "risk_group", "survival_prob_day7", "partial_hazard",
    ]

    profiles = pd.merge(
        feature_store[p1_cols],
        survival_pred[p2_cols],
        on="userid",
        how="left",
    )

    if len(profiles) != len(feature_store):
        raise DataPreparationError(
            message="Merge produced unexpected row count",
            expected=f"{len(feature_store)} rows",
            observed=f"{len(profiles)} rows",
        )

    null_check = profiles.isnull().sum()
    null_cols = null_check[null_check > 0].index.tolist()
    if null_cols:
        raise DataPreparationError(
            message="NaN values after merge",
            expected="no NaN",
            observed=f"NaN in: {null_cols}",
        )

    logger.info(
        "Player profiles built: %d players | lifecycle stages: %s | risk groups: %s",
        len(profiles),
        profiles["lifecycle_stage"].value_counts().to_dict(),
        profiles["risk_group"].value_counts().to_dict(),
    )
    return profiles


# ============================================================================
# PRIORITY SCORE
# ============================================================================


def compute_priority_scores(
    profiles: pd.DataFrame,
    weights: Dict[str, float],
) -> pd.Series:
    """Compute a 0–100 priority score for each player.

    Formula
    -------
    priority_score = (
        w_engagement  × normalize(engagement_score)     [Phase 1]
      + w_churn_risk  × churn_risk                      [Phase 2: 1 - survival_prob_day7]
      + w_session     × normalize(sessions_per_day)     [Phase 1]
    ) × 100

    Normalization: min-max per column (range [0,1]).
    churn_risk = 1 − survival_prob_day7 (already ∈ [0,1]).

    Higher score = player should receive intervention sooner.

    Weight Defensibility
    --------------------
    The weights (w_engagement, w_churn_risk, w_session) are configurable
    business priors defined in YAML, not statistically learned coefficients.
    In production they would be calibrated using historical intervention
    outcomes, A/B test lift results, and business strategy (e.g.,
    retention-first vs. revenue-first). Starting values follow an
    engagement-first philosophy: behavioral signals outweigh risk signals
    to reduce false-positive intervention triggers.

    Parameters
    ----------
    profiles : pd.DataFrame
        Output of build_player_profiles().
    weights : dict
        Keys: engagement_score, churn_risk, session_intensity.

    Returns
    -------
    pd.Series
        Priority scores in [0, 100], aligned with profiles.index.
    """
    def minmax_norm(series: pd.Series) -> pd.Series:
        rng = series.max() - series.min()
        if rng < 1e-12:
            return pd.Series(0.5, index=series.index)
        return (series - series.min()) / rng

    eng_norm = minmax_norm(profiles["engagement_score"])
    churn_risk = 1.0 - profiles["survival_prob_day7"]      # higher = worse
    sess_norm = minmax_norm(profiles["sessions_per_day"])

    w_eng = weights.get("engagement_score", 0.40)
    w_churn = weights.get("churn_risk", 0.35)
    w_sess = weights.get("session_intensity", 0.25)

    priority = (w_eng * eng_norm + w_churn * churn_risk + w_sess * sess_norm) * 100.0

    logger.info(
        "Priority scores computed: mean=%.2f  std=%.2f  min=%.2f  max=%.2f",
        priority.mean(), priority.std(), priority.min(), priority.max(),
    )
    return priority.rename("priority_score")


# ============================================================================
# BUSINESS RULES ENGINE
# ============================================================================


def assign_action_categories(
    profiles: pd.DataFrame,
    action_categories: List[Dict[str, Any]],
) -> Tuple[pd.Series, pd.Series]:
    """Assign each player an action category and intervention via business rules.

    Rules are evaluated in REVERSE priority order so the highest-priority rule
    (priority=1) overwrites everything. This implements "first-match-wins"
    semantics: the most critical rule wins for each player.

    The final rule (highest priority number) is the catch-all and is applied
    first, then overwritten by more specific rules.

    Parameters
    ----------
    profiles : pd.DataFrame
        Player profiles (must contain lifecycle_stage and risk_group).
    action_categories : list of dicts
        From YAML: name, priority, lifecycle_stages, risk_groups, intervention.

    Returns
    -------
    (action_series, intervention_series) : tuple of pd.Series
        Action category and intervention string per player.

    Raises
    ------
    DataPreparationError
        If no catch-all rule exists (would leave players unassigned).
    """
    # Sort by priority descending — catch-all (highest priority number) applied first
    sorted_cats = sorted(action_categories, key=lambda c: c["priority"], reverse=True)

    action_col = pd.Series("Unassigned", index=profiles.index, dtype=str)
    intervention_col = pd.Series("", index=profiles.index, dtype=str)

    rules_fired: Dict[str, int] = {}

    for cat in sorted_cats:
        mask = (
            profiles["lifecycle_stage"].isin(cat["lifecycle_stages"])
            & profiles["risk_group"].isin(cat["risk_groups"])
        )
        action_col[mask] = cat["name"]
        intervention_col[mask] = cat["intervention"]
        rules_fired[cat["name"]] = int(mask.sum())

    # Verify all players are assigned
    unassigned = (action_col == "Unassigned").sum()
    if unassigned > 0:
        raise DataPreparationError(
            message="Business rules failed to assign all players",
            expected="0 unassigned players",
            observed=f"{unassigned} players remain 'Unassigned' — add a catch-all rule",
        )

    # Log assignment distribution
    assignment_counts = action_col.value_counts().to_dict()
    total = len(profiles)
    logger.info("Action category assignment complete:")
    for name, count in sorted(assignment_counts.items(), key=lambda x: -x[1]):
        logger.info("  %-35s %6d players (%5.1f%%)", name, count, count / total * 100)

    return action_col, intervention_col, rules_fired


# ============================================================================
# SEGMENT SUMMARY
# ============================================================================


def generate_segment_summary(
    decisions: pd.DataFrame,
    action_categories: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate per-segment aggregate statistics.

    Parameters
    ----------
    decisions : pd.DataFrame
        Full player decisions table (output of run_phase3 before writing).
    action_categories : list of dicts
        From YAML (for metadata: color_code, rationale, intervention).

    Returns
    -------
    dict
        segment_summaries: per-category stats.
        total_players: N.
        generated_at: ISO timestamp.
    """
    total = len(decisions)
    cat_meta = {c["name"]: c for c in action_categories}
    summaries = {}

    for cat_name, group in decisions.groupby("action_category"):
        n = len(group)
        meta = cat_meta.get(cat_name, {})

        summaries[cat_name] = {
            "n_players": int(n),
            "pct_of_total": round(n / total * 100, 2),
            "priority": int(meta.get("priority", 99)),
            "color_code": meta.get("color_code", ""),
            "intervention": meta.get("intervention", ""),
            "rationale": meta.get("rationale", ""),
            # Operational KPIs — passed through from YAML business rules config
            "objective": meta.get("objective", ""),
            "primary_kpi": meta.get("primary_kpi", ""),
            "secondary_kpi": meta.get("secondary_kpi", ""),
            "owner": meta.get("owner", ""),
            "expected_business_goal": meta.get("expected_business_goal", ""),
            "measurement_kpi": meta.get("measurement_kpi", ""),
            "phase4_connection": meta.get("phase4_connection", ""),
            # Priority score distribution — full percentile profile
            # Analytics teams communicate score distributions as percentiles,
            # not just mean/std. P90/P95/P99 identify the most urgent players
            # within each segment for budget prioritization.
            "priority_score": {
                "mean": round(float(group["priority_score"].mean()), 4),
                "std": round(float(group["priority_score"].std()), 4),
                "min": round(float(group["priority_score"].min()), 4),
                "p25": round(float(group["priority_score"].quantile(0.25)), 4),
                "p50": round(float(group["priority_score"].quantile(0.50)), 4),
                "p75": round(float(group["priority_score"].quantile(0.75)), 4),
                "p90": round(float(group["priority_score"].quantile(0.90)), 4),
                "p95": round(float(group["priority_score"].quantile(0.95)), 4),
                "p99": round(float(group["priority_score"].quantile(0.99)), 4),
                "max": round(float(group["priority_score"].max()), 4),
            },
            "engagement_score": {
                "mean": round(float(group["engagement_score"].mean()), 4),
                "std": round(float(group["engagement_score"].std()), 4),
            },
            "survival_prob_day7": {
                "mean": round(float(group["survival_prob_day7"].mean()), 4),
                "std": round(float(group["survival_prob_day7"].std()), 4),
            },
            "sessions_per_day": {
                "mean": round(float(group["sessions_per_day"].mean()), 4),
                "std": round(float(group["sessions_per_day"].std()), 4),
            },
            "risk_group_distribution": group["risk_group"].value_counts().to_dict(),
            "lifecycle_stage_distribution": group["lifecycle_stage"].value_counts().to_dict(),
        }

    # Sort by priority for readability
    sorted_summaries = dict(
        sorted(summaries.items(), key=lambda kv: kv[1]["priority"])
    )

    return {
        "total_players": int(total),
        "n_segments": len(sorted_summaries),
        "segment_summaries": sorted_summaries,
    }


# ============================================================================
# DECISION RULES AUDIT
# ============================================================================


def generate_decision_rules_audit(
    decisions: pd.DataFrame,
    action_categories: List[Dict[str, Any]],
    rules_fired: Dict[str, int],
) -> Dict[str, Any]:
    """Generate audit trail of which rules fired and coverage statistics.

    Parameters
    ----------
    decisions : pd.DataFrame
    action_categories : list of dicts
    rules_fired : dict
        {rule_name: n_players_matched} from assign_action_categories.

    Returns
    -------
    dict
        Structured audit report for decision_rules.json.
    """
    total = len(decisions)
    cat_meta = {c["name"]: c for c in action_categories}
    rules_audit = []

    for cat_name in sorted(rules_fired.keys(), key=lambda k: cat_meta.get(k, {}).get("priority", 99)):
        n = rules_fired[cat_name]
        group = decisions[decisions["action_category"] == cat_name]
        meta = cat_meta.get(cat_name, {})

        rules_audit.append({
            "rule_name": cat_name,
            "priority": int(meta.get("priority", 99)),
            "conditions": {
                "lifecycle_stages": meta.get("lifecycle_stages", []),
                "risk_groups": meta.get("risk_groups", []),
            },
            "n_players_matched": int(n),
            "pct_of_total": round(n / total * 100, 2),
            "priority_score_distribution": {
                "mean": round(float(group["priority_score"].mean()), 4) if n > 0 else 0.0,
                "std": round(float(group["priority_score"].std()), 4) if n > 1 else 0.0,
                "min": round(float(group["priority_score"].min()), 4) if n > 0 else 0.0,
                "p25": round(float(group["priority_score"].quantile(0.25)), 4) if n > 0 else 0.0,
                "p50": round(float(group["priority_score"].quantile(0.50)), 4) if n > 0 else 0.0,
                "p75": round(float(group["priority_score"].quantile(0.75)), 4) if n > 0 else 0.0,
                "max": round(float(group["priority_score"].max()), 4) if n > 0 else 0.0,
            },
        })

    return {
        "description": (
            "Audit trail of Phase 3 Player Decision Engine rule assignments. "
            "Each rule entry shows coverage, priority score distribution, and conditions."
        ),
        "total_players": int(total),
        "rules_evaluated": len(action_categories),
        "rules_audit": rules_audit,
    }


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
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
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
        raise ModelValidationError(
            message=f"JSON write failed: {path}",
            expected="successful write",
            observed=str(exc),
        ) from exc

    try:
        with open(path, "r", encoding="utf-8") as fh:
            json.load(fh)
    except json.JSONDecodeError as exc:
        raise ModelValidationError(
            message=f"JSON re-parse failed after write: {path}",
            expected="valid JSON",
            observed=str(exc),
        ) from exc

    sha = compute_file_sha256(path)
    size = Path(path).stat().st_size
    logger.info("✓ JSON artifact: %s (%d bytes)", Path(path).name, size)
    return {"path": str(path), "size_bytes": size, "sha256": sha}


def write_parquet_artifact(df: pd.DataFrame, path: str) -> Dict[str, Any]:
    """Write DataFrame to Parquet, verify reload, return metadata."""
    try:
        df.to_parquet(path, index=False)
        df_reload = pd.read_parquet(path)
    except Exception as exc:
        raise ModelValidationError(
            message=f"Parquet write/reload failed: {path}",
            expected="successful write and reload",
            observed=str(exc),
        ) from exc

    try:
        pd.testing.assert_frame_equal(
            df, df_reload,
            check_dtype=True, check_like=False,
            check_exact=False, rtol=1e-5,
            check_index_type=False,  # RangeIndex → Int64Index on parquet roundtrip
        )
    except AssertionError as exc:
        raise ModelValidationError(
            message=f"Parquet reload mismatch: {path}",
            expected="identical content after reload",
            observed=str(exc),
        ) from exc

    sha = compute_file_sha256(path)
    size = Path(path).stat().st_size
    logger.info(
        "✓ Parquet artifact: %s (%d rows × %d cols, %d bytes)",
        Path(path).name, len(df), len(df.columns), size,
    )
    return {
        "path": str(path), "rows": len(df),
        "columns": len(df.columns), "size_bytes": size, "sha256": sha,
    }


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================


def run_phase3(
    feature_store_path: str = None,
    survival_predictions_path: str = None,
    manifest_path: str = None,
    config_path: str = None,
    benchmarks_path: str = None,
) -> Dict[str, Any]:
    """Execute Phase 3: Player Decision Engine.

    Pipeline
    --------
    1.  Load Phase 3 configuration (strict)
    2.  Validate Phase 1 + Phase 2 inputs (schema only)
    3.  Build unified player profiles (Phase 1 + Phase 2 merge)
    4.  Compute priority scores (weighted composite: engagement × risk × sessions)
    5.  Assign action categories (YAML business rules, first-match-wins)
    6.  Generate segment summary (aggregate stats per category)
    7.  Generate decision rules audit (coverage and P-score distributions)
    8.  Write 3 artifacts: player_decisions.parquet, segment_summary.json,
        decision_rules.json
    9.  Update manifest (phase_3_summary, version=3.0.0)
    10. Return structured pipeline report

    Parameters
    ----------
    feature_store_path : str, optional
    survival_predictions_path : str, optional
    manifest_path : str, optional
    config_path : str, optional
    benchmarks_path : str, optional

    Returns
    -------
    dict
        Structured pipeline report.

    Raises
    ------
    Phase3Error (or subclass), ConfigurationError
        On domain-specific failures.
    PipelineExecutionError
        On unexpected failures.
    """
    phase3_start = datetime.now(timezone.utc)

    fs_path = resolve_project_path("data", "processed", "feature_store.parquet")
    sp_path = resolve_project_path("data", "processed", "survival_predictions.parquet")
    mf_path = resolve_project_path("data", "processed", "manifest.json")
    cfg_path = resolve_project_path("config", "simulation_config.yaml")
    bmk_path = resolve_project_path("config", "industry_benchmarks.yaml")

    if feature_store_path:
        fs_path = Path(feature_store_path)
    if survival_predictions_path:
        sp_path = Path(survival_predictions_path)
    if manifest_path:
        mf_path = Path(manifest_path)
    if config_path:
        cfg_path = Path(config_path)
    if benchmarks_path:
        bmk_path = Path(benchmarks_path)

    try:
        logger.info("=" * 80)
        logger.info("PHASE 3: PLAYER DECISION ENGINE")
        logger.info("=" * 80)

        # ---- Step 1: Config -------------------------------------------------------
        logger.info("[Step 1/9] Loading Phase 3 configuration...")
        phase3_config = load_phase3_config(str(cfg_path), str(bmk_path))
        action_categories = phase3_config["action_categories"]
        priority_weights = phase3_config["priority_score_weights"]
        min_samples = phase3_config["min_samples"]

        # ---- Step 2: Validate inputs ---------------------------------------------
        logger.info("[Step 2/9] Validating Phase 1+2 inputs...")
        feature_store, survival_pred = validate_phase2_outputs(
            str(sp_path), str(fs_path)
        )

        # ---- Step 3: Build profiles ----------------------------------------------
        logger.info("[Step 3/9] Building unified player profiles...")
        profiles = build_player_profiles(feature_store, survival_pred, min_samples)

        # ---- Step 4: Priority scores ---------------------------------------------
        logger.info("[Step 4/9] Computing priority scores...")
        priority_scores = compute_priority_scores(profiles, priority_weights)

        # ---- Step 5: Assign action categories -----------------------------------
        logger.info("[Step 5/9] Assigning action categories (business rules engine)...")
        action_col, intervention_col, rules_fired = assign_action_categories(
            profiles, action_categories
        )

        # ---- Assemble decisions table -------------------------------------------
        decisions = pd.DataFrame({
            "userid": profiles["userid"].values,
            "lifecycle_stage": profiles["lifecycle_stage"].values,
            "risk_group": profiles["risk_group"].values,
            "engagement_score": profiles["engagement_score"].values.round(6),
            "sessions_per_day": profiles["sessions_per_day"].values.round(6),
            "survival_prob_day7": profiles["survival_prob_day7"].values.round(6),
            "priority_score": priority_scores.values.round(4),
            "action_category": action_col.values,
            "intervention": intervention_col.values,
        })

        # ---- Step 6: Segment summary --------------------------------------------
        logger.info("[Step 6/9] Generating segment summary...")
        segment_summary = generate_segment_summary(decisions, action_categories)

        # ---- Step 7: Decision rules audit ---------------------------------------
        logger.info("[Step 7/9] Generating decision rules audit...")
        rules_audit = generate_decision_rules_audit(
            decisions, action_categories, rules_fired
        )

        # ---- Step 8: Write artifacts --------------------------------------------
        logger.info("[Step 8/9] Writing Phase 3 artifacts...")
        out_dir = resolve_project_path("data", "processed")
        out_dir.mkdir(parents=True, exist_ok=True)
        written_artifacts = {}

        # player_decisions.parquet
        written_artifacts["player_decisions"] = write_parquet_artifact(
            decisions, str(out_dir / "player_decisions.parquet")
        )

        # segment_summary.json
        written_artifacts["segment_summary"] = write_json_artifact(
            segment_summary, str(out_dir / "segment_summary.json")
        )

        # decision_rules.json
        written_artifacts["decision_rules"] = write_json_artifact(
            rules_audit, str(out_dir / "decision_rules.json")
        )

        # ---- Step 9: Update manifest --------------------------------------------
        logger.info("[Step 9/9] Updating manifest...")
        with open(mf_path, "r", encoding="utf-8") as fh:
            existing_manifest = json.load(fh)

        # Build readable segment breakdown for manifest
        segment_breakdown = {
            name: {
                "n_players": data["n_players"],
                "pct_of_total": data["pct_of_total"],
                "mean_priority_score": data["priority_score"]["mean"],
                "intervention": data["intervention"],
            }
            for name, data in segment_summary["segment_summaries"].items()
        }

        phase3_artifact_entries = [
            {
                "name": "player_decisions_parquet",
                "phase": 3,
                "path": written_artifacts["player_decisions"]["path"],
                "type": "parquet",
                "size_bytes": written_artifacts["player_decisions"]["size_bytes"],
                "sha256": written_artifacts["player_decisions"]["sha256"],
                "rows": written_artifacts["player_decisions"]["rows"],
                "columns": written_artifacts["player_decisions"]["columns"],
                "purpose": "Phase 3: Per-player action category, priority score, intervention",
            },
            {
                "name": "segment_summary_json",
                "phase": 3,
                "path": written_artifacts["segment_summary"]["path"],
                "type": "json",
                "size_bytes": written_artifacts["segment_summary"]["size_bytes"],
                "sha256": written_artifacts["segment_summary"]["sha256"],
                "purpose": "Phase 3: Aggregate stats per action category/segment",
            },
            {
                "name": "decision_rules_json",
                "phase": 3,
                "path": written_artifacts["decision_rules"]["path"],
                "type": "json",
                "size_bytes": written_artifacts["decision_rules"]["size_bytes"],
                "sha256": written_artifacts["decision_rules"]["sha256"],
                "purpose": "Phase 3: Business rules audit trail — rule coverage and P-score distributions",
            },
        ]

        # Remove old Phase 3 artifacts from previous runs (if any)
        existing_artifacts = [
            a for a in existing_manifest.get("artifacts", [])
            if a.get("phase") != 3
        ]

        updated_manifest = {
            **existing_manifest,
            "manifest_version": "3.0.0",
            "phase": 3,
            "artifacts": existing_artifacts + phase3_artifact_entries,
            "phase_3_summary": {
                "status": "SUCCESS",
                "name": "Player Decision Engine",
                "approach": "Business rules + priority scoring (no ML regression)",
                "rationale": (
                    "Cookie Cats lacks future outcome labels beyond day 7. "
                    "sessions_per_day × 7 is an identity mapping, not a prediction task. "
                    "Decision engine correctly uses Phase 1+2 outputs for actionable targeting."
                ),
                "n_players": int(len(decisions)),
                "n_action_categories": len(action_categories),
                "segment_breakdown": segment_breakdown,
                "priority_score_weights": priority_weights,
            },
        }

        with open(mf_path, "w", encoding="utf-8") as fh:
            json.dump(convert_numpy_to_native(updated_manifest), fh, indent=2)

        logger.info("✓ Manifest updated → phase=3, version=3.0.0")

        # ---- Final report -------------------------------------------------------
        phase3_end = datetime.now(timezone.utc)
        duration_secs = (phase3_end - phase3_start).total_seconds()

        # Log segment breakdown
        logger.info("=" * 80)
        logger.info("PHASE 3 COMPLETE (SUCCESS) — Duration: %.2fs", duration_secs)
        logger.info("Segment breakdown:")
        for seg_name, seg_data in segment_summary["segment_summaries"].items():
            logger.info(
                "  %-35s %6d players (%5.1f%%)  P-score mean=%.1f",
                seg_name,
                seg_data["n_players"],
                seg_data["pct_of_total"],
                seg_data["priority_score"]["mean"],
            )
        logger.info("=" * 80)

        return {
            "pipeline": {
                "status": "SUCCESS",
                "phase": 3,
                "name": "Player Decision Engine",
                "start_time": phase3_start.isoformat(),
                "end_time": phase3_end.isoformat(),
                "duration_seconds": duration_secs,
            },
            "segment_summary": {
                seg: {
                    "n_players": data["n_players"],
                    "pct_of_total": data["pct_of_total"],
                    "mean_priority_score": data["priority_score"]["mean"],
                }
                for seg, data in segment_summary["segment_summaries"].items()
            },
            "artifacts_written": list(written_artifacts.keys()),
        }

    except (Phase3Error, ConfigurationError):
        logger.exception("PHASE 3 FAILED")
        raise

    except Exception as exc:
        logger.error("PHASE 3 FAILED (unexpected): %s", str(exc))
        raise PipelineExecutionError(
            message="Phase 3 pipeline failed with unexpected error",
            observed=str(exc),
        ) from exc
