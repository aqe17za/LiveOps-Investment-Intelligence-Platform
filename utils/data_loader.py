"""Cached artifact loaders for the EA LiveOps Intelligence Platform.

Design principles:
- Every loader is decorated with @st.cache_data(ttl=3600)
- Every loader wraps IO in try/except and returns None on failure
- Callers must check for None before use
- No src/ imports — this layer reads pre-built artifacts only
- master_player_df is the unified player-level dataframe (3-way merge)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
import yaml

from utils.constants import (
    BUSINESS_IMPACT,
    COX_MODEL_SUMMARY,
    DATA_PROFILE,
    DECISION_ENGINE_EVALUATION,
    DECISION_RULES,
    EXPERIMENT_VALIDATION,
    FEATURE_STORE,
    INDUSTRY_BENCHMARKS,
    LIFECYCLE_STAGES,
    LIVEOPS_RECOMMENDATIONS,
    MANIFEST,
    OVERALL_TREATMENT_EFFECTS,
    PLAYER_DECISIONS,
    SEGMENT_LEVEL_EFFECTS,
    SEGMENT_SUMMARY,
    SIMULATION_CONFIG,
    STATISTICAL_TESTS,
    SURVIVAL_CURVES,
    SURVIVAL_DIAGNOSTICS,
    SURVIVAL_PREDICTIONS,
)

logger = logging.getLogger(__name__)


# ── Generic helpers ───────────────────────────────────────────────────────


def _safe_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON file safely. Returns None if missing or malformed."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning("Could not load %s: %s", path.name, exc)
        return None


def _safe_parquet(path: Path) -> Optional[pd.DataFrame]:
    """Load a Parquet file safely. Returns None if missing or malformed."""
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        logger.warning("Could not load %s: %s", path.name, exc)
        return None


def _safe_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file safely. Returns None if missing or malformed."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except Exception as exc:
        logger.warning("Could not load %s: %s", path.name, exc)
        return None


# ── Individual loaders ────────────────────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def load_manifest() -> Optional[Dict[str, Any]]:
    return _safe_json(MANIFEST)


@st.cache_data(ttl=3600, show_spinner=False)
def load_feature_store() -> Optional[pd.DataFrame]:
    return _safe_parquet(FEATURE_STORE)


@st.cache_data(ttl=3600, show_spinner=False)
def load_data_profile() -> Optional[Dict[str, Any]]:
    return _safe_json(DATA_PROFILE)


@st.cache_data(ttl=3600, show_spinner=False)
def load_lifecycle_stages() -> Optional[pd.DataFrame]:
    try:
        return pd.read_csv(LIFECYCLE_STAGES)
    except Exception as exc:
        logger.warning("Could not load lifecycle_stages.csv: %s", exc)
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_survival_curves() -> Optional[pd.DataFrame]:
    return _safe_parquet(SURVIVAL_CURVES)


@st.cache_data(ttl=3600, show_spinner=False)
def load_survival_predictions() -> Optional[pd.DataFrame]:
    return _safe_parquet(SURVIVAL_PREDICTIONS)


@st.cache_data(ttl=3600, show_spinner=False)
def load_survival_diagnostics() -> Optional[Dict[str, Any]]:
    return _safe_json(SURVIVAL_DIAGNOSTICS)


@st.cache_data(ttl=3600, show_spinner=False)
def load_cox_model_summary() -> Optional[Dict[str, Any]]:
    return _safe_json(COX_MODEL_SUMMARY)


@st.cache_data(ttl=3600, show_spinner=False)
def load_player_decisions() -> Optional[pd.DataFrame]:
    return _safe_parquet(PLAYER_DECISIONS)


@st.cache_data(ttl=3600, show_spinner=False)
def load_segment_summary() -> Optional[Dict[str, Any]]:
    return _safe_json(SEGMENT_SUMMARY)


@st.cache_data(ttl=3600, show_spinner=False)
def load_decision_rules() -> Optional[Dict[str, Any]]:
    return _safe_json(DECISION_RULES)


@st.cache_data(ttl=3600, show_spinner=False)
def load_experiment_validation() -> Optional[Dict[str, Any]]:
    return _safe_json(EXPERIMENT_VALIDATION)


@st.cache_data(ttl=3600, show_spinner=False)
def load_overall_treatment_effects() -> Optional[Dict[str, Any]]:
    return _safe_json(OVERALL_TREATMENT_EFFECTS)


@st.cache_data(ttl=3600, show_spinner=False)
def load_segment_level_effects() -> Optional[Dict[str, Any]]:
    return _safe_json(SEGMENT_LEVEL_EFFECTS)


@st.cache_data(ttl=3600, show_spinner=False)
def load_statistical_tests() -> Optional[Dict[str, Any]]:
    return _safe_json(STATISTICAL_TESTS)


@st.cache_data(ttl=3600, show_spinner=False)
def load_decision_engine_evaluation() -> Optional[Dict[str, Any]]:
    return _safe_json(DECISION_ENGINE_EVALUATION)


@st.cache_data(ttl=3600, show_spinner=False)
def load_liveops_recommendations() -> Optional[Dict[str, Any]]:
    return _safe_json(LIVEOPS_RECOMMENDATIONS)


@st.cache_data(ttl=3600, show_spinner=False)
def load_business_impact() -> Optional[Dict[str, Any]]:
    return _safe_json(BUSINESS_IMPACT)


@st.cache_data(ttl=3600, show_spinner=False)
def load_simulation_config() -> Optional[Dict[str, Any]]:
    return _safe_yaml(SIMULATION_CONFIG)


@st.cache_data(ttl=3600, show_spinner=False)
def load_industry_benchmarks() -> Optional[Dict[str, Any]]:
    return _safe_yaml(INDUSTRY_BENCHMARKS)


# ── Master player DataFrame (3-way merge) ─────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def load_master_player_df() -> Optional[pd.DataFrame]:
    """Build unified player-level dataframe by merging all three parquets.

    Merge key: userid (unique per player, no duplicates per experiment design).
    Columns from survival_predictions that overlap with feature_store
    (sessions_per_day, session_frequency_bin) are excluded from the right side
    to avoid duplication.

    Returns
    -------
    pd.DataFrame with ~20 columns covering all pipeline outputs per player,
    or None if any source parquet cannot be loaded.
    """
    fs = load_feature_store()
    sp = load_survival_predictions()
    pd_df = load_player_decisions()

    if fs is None or sp is None or pd_df is None:
        logger.error("Cannot build master_player_df — one or more source parquets missing")
        return None

    # Select non-overlapping columns from survival_predictions
    sp_cols = [
        "userid",
        "partial_hazard",
        "survival_prob_day1",
        "survival_prob_day7",
        "predicted_median_survival",
        "risk_group",
    ]
    sp_select = sp[[c for c in sp_cols if c in sp.columns]]

    # Select non-overlapping columns from player_decisions
    pd_cols = ["userid", "action_category", "priority_score", "intervention"]
    pd_select = pd_df[[c for c in pd_cols if c in pd_df.columns]]

    df = fs.merge(sp_select, on="userid", how="left")
    df = df.merge(pd_select, on="userid", how="left")

    logger.info("master_player_df built: %d rows × %d columns", len(df), len(df.columns))
    return df


# ── Artifact availability check ───────────────────────────────────────────


def check_artifact_availability() -> Dict[str, bool]:
    """Return a dict of {artifact_name: exists} for all dashboard artifacts."""
    artifacts = {
        "manifest.json": MANIFEST,
        "feature_store.parquet": FEATURE_STORE,
        "data_profile.json": DATA_PROFILE,
        "lifecycle_stages.csv": LIFECYCLE_STAGES,
        "survival_curves.parquet": SURVIVAL_CURVES,
        "survival_predictions.parquet": SURVIVAL_PREDICTIONS,
        "survival_diagnostics.json": SURVIVAL_DIAGNOSTICS,
        "cox_model_summary.json": COX_MODEL_SUMMARY,
        "player_decisions.parquet": PLAYER_DECISIONS,
        "segment_summary.json": SEGMENT_SUMMARY,
        "decision_rules.json": DECISION_RULES,
        "experiment_validation.json": EXPERIMENT_VALIDATION,
        "overall_treatment_effects.json": OVERALL_TREATMENT_EFFECTS,
        "segment_level_effects.json": SEGMENT_LEVEL_EFFECTS,
        "statistical_tests.json": STATISTICAL_TESTS,
        "decision_engine_evaluation.json": DECISION_ENGINE_EVALUATION,
        "liveops_recommendations.json": LIVEOPS_RECOMMENDATIONS,
        "business_impact_summary.json": BUSINESS_IMPACT,
    }
    return {name: Path(path).exists() for name, path in artifacts.items()}
