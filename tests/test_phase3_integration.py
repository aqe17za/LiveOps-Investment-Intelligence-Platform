"""Phase 3 integration tests — Player Decision Engine.

Tests the full decision engine pipeline including:
- Player profile building, priority scoring, business rule assignment
- Artifact schema validation (player_decisions.parquet, segment_summary.json, decision_rules.json)
- Idempotency (deterministic priority scores)
- Error propagation (ConfigurationError, DataPreparationError)
- Clean state restoration for Phase 4

Phase 1 + Phase 2 must have been run before these tests execute.
"""

import json
import os

import numpy as np
import pandas as pd
import pytest

from src.exceptions import (
    ConfigurationError,
    DataPreparationError,
    Phase1Error,
    Phase3Error,
)
from src.retention_intelligence import run_phase3

FEATURE_STORE_PATH = "data/processed/feature_store.parquet"
SURVIVAL_PRED_PATH = "data/processed/survival_predictions.parquet"
MANIFEST_PATH = "data/processed/manifest.json"
DECISIONS_PATH = "data/processed/player_decisions.parquet"
SEGMENT_SUMMARY_PATH = "data/processed/segment_summary.json"
DECISION_RULES_PATH = "data/processed/decision_rules.json"

EXPECTED_ARTIFACTS = {"player_decisions", "segment_summary", "decision_rules"}
KNOWN_ACTION_CATEGORIES = {
    "High Priority Reactivation",
    "At-Risk Retention",
    "Onboarding Nurture",
    "Active Growth",
    "Loyalty Reward",
    "Monitor and Observe",
}


# ============================================================================
# TEST 1: End-to-end success + artifact validation
# ============================================================================


def test_run_phase3_end_to_end():
    """run_phase3() completes with SUCCESS, writes 3 artifacts, updates manifest."""
    report = run_phase3()

    # Pipeline status
    assert report["pipeline"]["status"] == "SUCCESS"
    assert report["pipeline"]["phase"] == 3
    assert report["pipeline"]["name"] == "Player Decision Engine"

    # Artifacts written
    assert set(report["artifacts_written"]) == EXPECTED_ARTIFACTS

    # ---- player_decisions.parquet -----------------------------------------------
    assert os.path.exists(DECISIONS_PATH), "player_decisions.parquet not found"
    df = pd.read_parquet(DECISIONS_PATH)

    # Row count matches feature store
    fs = pd.read_parquet(FEATURE_STORE_PATH)
    assert len(df) == len(fs), "Decision count != feature store row count"

    # Required columns
    required_cols = {
        "userid", "lifecycle_stage", "risk_group", "engagement_score",
        "sessions_per_day", "survival_prob_day7", "priority_score",
        "action_category", "intervention",
    }
    missing_cols = required_cols - set(df.columns)
    assert not missing_cols, f"Missing columns in player_decisions: {missing_cols}"

    # No null values in any column
    null_counts = df.isnull().sum()
    assert null_counts.sum() == 0, f"Null values found: {null_counts[null_counts > 0].to_dict()}"

    # Priority score in [0, 100]
    assert df["priority_score"].between(0, 100).all(), (
        f"Priority scores out of [0,100] range: "
        f"min={df['priority_score'].min():.4f}, max={df['priority_score'].max():.4f}"
    )

    # Every player assigned to a known action category
    unknown_cats = set(df["action_category"].unique()) - KNOWN_ACTION_CATEGORIES
    assert not unknown_cats, f"Unknown action categories found: {unknown_cats}"

    # All players assigned (no unassigned)
    assert "Unassigned" not in df["action_category"].values

    # ---- segment_summary.json ---------------------------------------------------
    assert os.path.exists(SEGMENT_SUMMARY_PATH)
    with open(SEGMENT_SUMMARY_PATH, encoding="utf-8") as fh:
        summary = json.load(fh)

    assert "total_players" in summary
    assert summary["total_players"] == len(df)
    assert "segment_summaries" in summary
    assert len(summary["segment_summaries"]) > 0

    # Segment player counts must sum to total
    segment_count_sum = sum(
        s["n_players"] for s in summary["segment_summaries"].values()
    )
    assert segment_count_sum == summary["total_players"], (
        f"Segment counts ({segment_count_sum}) != total players ({summary['total_players']})"
    )

    # Each segment has required fields
    for seg_name, seg_data in summary["segment_summaries"].items():
        for key in ("n_players", "pct_of_total", "priority_score", "intervention"):
            assert key in seg_data, f"Segment '{seg_name}' missing key: {key}"
        p = seg_data["priority_score"]
        for stat in ("mean", "std", "min", "p50", "max"):
            assert stat in p, f"Segment '{seg_name}' priority_score missing stat: {stat}"
        assert p["min"] <= p["p50"] <= p["max"], f"Segment '{seg_name}' P-score order broken"

    # ---- decision_rules.json ----------------------------------------------------
    assert os.path.exists(DECISION_RULES_PATH)
    with open(DECISION_RULES_PATH, encoding="utf-8") as fh:
        rules = json.load(fh)

    assert "rules_audit" in rules
    assert len(rules["rules_audit"]) > 0
    assert rules["total_players"] == len(df)

    # Rules audit: player counts match decisions table
    rules_total = sum(r["n_players_matched"] for r in rules["rules_audit"])
    # Note: rules_total >= total (catch-all matches everyone before overwrite)
    # The audit reflects rules_fired counts, not final assignments
    # Final assignment sum = total (verified via segment_summary above)

    for rule in rules["rules_audit"]:
        assert "rule_name" in rule
        assert "priority" in rule
        assert "conditions" in rule
        assert "n_players_matched" in rule
        assert "priority_score_distribution" in rule

    # ---- manifest ---------------------------------------------------------------
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)

    assert manifest["phase"] == 3
    assert manifest["manifest_version"] == "3.0.0"
    assert "phase_3_summary" in manifest

    p3 = manifest["phase_3_summary"]
    assert p3["status"] == "SUCCESS"
    assert p3["name"] == "Player Decision Engine"
    assert "approach" in p3
    assert "no ML" in p3["approach"].lower() or "business rules" in p3["approach"].lower()
    assert p3["n_players"] == len(df)
    assert "segment_breakdown" in p3

    # Phase 1+2 artifacts still present
    artifact_names = {a["name"] for a in manifest["artifacts"]}
    assert "feature_store_parquet" in artifact_names, "Phase 1 artifact lost from manifest"

    # Phase 3 artifacts present
    p3_names = {a["name"] for a in manifest["artifacts"] if a.get("phase") == 3}
    assert "player_decisions_parquet" in p3_names
    assert "segment_summary_json" in p3_names
    assert "decision_rules_json" in p3_names


# ============================================================================
# TEST 2: Priority score properties
# ============================================================================


def test_priority_scores_are_deterministic_and_bounded():
    """Priority scores are in [0,100], finite, and deterministic across runs."""
    run_phase3()
    df1 = pd.read_parquet(DECISIONS_PATH)

    run_phase3()
    df2 = pd.read_parquet(DECISIONS_PATH)

    # Bounded
    assert df1["priority_score"].between(0, 100).all()

    # Finite
    assert np.isfinite(df1["priority_score"]).all()

    # Deterministic (same scores on re-run)
    pd.testing.assert_series_equal(
        df1["priority_score"].reset_index(drop=True),
        df2["priority_score"].reset_index(drop=True),
        check_names=True,
        rtol=1e-5,
    )

    # Action categories deterministic
    assert (df1["action_category"].values == df2["action_category"].values).all()


# ============================================================================
# TEST 3: Business rules correctness
# ============================================================================


def test_business_rules_assign_all_players():
    """Every player receives exactly one valid action category."""
    run_phase3()
    df = pd.read_parquet(DECISIONS_PATH)

    # No unassigned players
    assert "Unassigned" not in df["action_category"].values

    # Known categories only
    assigned = set(df["action_category"].unique())
    assert assigned.issubset(KNOWN_ACTION_CATEGORIES), (
        f"Unknown categories: {assigned - KNOWN_ACTION_CATEGORIES}"
    )

    # Every player has a non-empty intervention
    assert (df["intervention"].str.len() > 0).all(), "Some players have empty intervention"

    # High Priority Reactivation: only Dormant/At-Risk lifecycle + High Churn Risk
    hp = df[df["action_category"] == "High Priority Reactivation"]
    if len(hp) > 0:
        assert hp["lifecycle_stage"].isin(["Dormant", "At-Risk"]).all()
        assert hp["risk_group"].isin(["High Churn Risk"]).all()

    # Loyalty Reward: only Active lifecycle + Low Churn Risk
    lr = df[df["action_category"] == "Loyalty Reward"]
    if len(lr) > 0:
        assert lr["lifecycle_stage"].isin(["Active"]).all()
        assert lr["risk_group"].isin(["Low Churn Risk"]).all()


# ============================================================================
# TEST 4: Invalid config → ConfigurationError propagates unwrapped
# ============================================================================


def test_run_phase3_invalid_config_raises_configuration_error():
    """ConfigurationError propagates unwrapped when config file is missing."""
    with pytest.raises(ConfigurationError) as exc_info:
        run_phase3(config_path="config/does_not_exist.yaml")
    assert isinstance(exc_info.value, Phase1Error)
    assert isinstance(exc_info.value, ConfigurationError)


# ============================================================================
# TEST 5: Missing Phase 2 column → DataPreparationError
# ============================================================================


def test_run_phase3_missing_column_raises_data_preparation_error():
    """DataPreparationError raised when survival_predictions is missing a column."""
    sp = pd.read_parquet(SURVIVAL_PRED_PATH)
    broken_path = "data/processed/_test_broken_survival_pred.parquet"
    sp.drop(columns=["risk_group"]).to_parquet(broken_path, index=False)

    try:
        with pytest.raises(DataPreparationError) as exc_info:
            run_phase3(survival_predictions_path=broken_path)
        assert isinstance(exc_info.value, Phase3Error)
        assert "risk_group" in str(exc_info.value) or "missing" in str(exc_info.value).lower()
    finally:
        if os.path.exists(broken_path):
            os.remove(broken_path)


# ============================================================================
# TEST 6: Restore clean state
# ============================================================================


def test_run_phase3_restore_clean_state():
    """Leave repo in valid Phase 3 manifest state for subsequent phases."""
    report = run_phase3()
    assert report["pipeline"]["status"] == "SUCCESS"

    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)
    assert manifest["phase"] == 3
    assert manifest["phase_3_summary"]["status"] == "SUCCESS"
    assert manifest["phase_3_summary"]["name"] == "Player Decision Engine"
