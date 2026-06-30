"""Reusable filter widgets."""
import streamlit as st
import pandas as pd
from typing import Optional


def lifecycle_filter(df: pd.DataFrame, key: str = "lc_filter") -> pd.DataFrame:
    """Multiselect filter for lifecycle_stage."""
    if "lifecycle_stage" not in df.columns:
        return df
    options = sorted(df["lifecycle_stage"].dropna().unique().tolist())
    selected = st.multiselect("Lifecycle Stage", options, default=options, key=key)
    return df[df["lifecycle_stage"].isin(selected)] if selected else df


def risk_filter(df: pd.DataFrame, key: str = "risk_filter") -> pd.DataFrame:
    """Multiselect filter for risk_group."""
    if "risk_group" not in df.columns:
        return df
    options = sorted(df["risk_group"].dropna().unique().tolist())
    selected = st.multiselect("Risk Group", options, default=options, key=key)
    return df[df["risk_group"].isin(selected)] if selected else df


def action_filter(df: pd.DataFrame, key: str = "action_filter") -> pd.DataFrame:
    """Multiselect filter for action_category."""
    if "action_category" not in df.columns:
        return df
    options = sorted(df["action_category"].dropna().unique().tolist())
    selected = st.multiselect("Action Category", options, default=options, key=key)
    return df[df["action_category"].isin(selected)] if selected else df


def version_filter(df: pd.DataFrame, key: str = "version_filter") -> pd.DataFrame:
    """Radio filter for version (gate_30 / gate_40 / Both)."""
    if "version" not in df.columns:
        return df
    choice = st.radio("Version", ["Both", "Gate 30 (Control)", "Gate 40 (Treatment)"], key=key)
    if choice == "Gate 30 (Control)":
        return df[df["version"] == "gate_30"]
    if choice == "Gate 40 (Treatment)":
        return df[df["version"] == "gate_40"]
    return df


def outcome_selector(key: str = "outcome_sel") -> str:
    """Radio selector for primary vs secondary outcome."""
    choice = st.radio("Outcome", ["D7 Retention (Primary)", "D1 Retention (Secondary)"], key=key)
    return "retention_7" if "D7" in choice else "retention_1"


def dimension_selector(segment_effects: dict, key: str = "dim_sel") -> str:
    """Selectbox for segmentation dimension."""
    dims = [d["dimension_name"] for d in segment_effects.get("segmentation_dimensions", [])]
    return st.selectbox("Segmentation Dimension", dims, key=key)
