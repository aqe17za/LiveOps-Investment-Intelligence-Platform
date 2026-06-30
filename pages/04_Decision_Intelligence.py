"""Phase 3 — Decision Intelligence Engine

Business rule-based player interventions and priority scoring.
Shows outputs from Phase 3 of the pipeline.
"""

import streamlit as st

from components.sidebar import render_sidebar, render_artifact_footer
from components.layout import page_header, section_header, info_callout, excluded_segment_note
from components.metric_cards import metric_row, player_card
from components.plot_components import (
    priority_score_distribution, recommendation_distribution_chart, 
    player_journey_sankey
)
from utils.data_loader import (
    load_player_decisions, load_segment_summary, load_decision_rules,
    load_master_player_df
)
from utils.helpers import fmt_number, fmt_pct, fmt_float, priority_band

# Page config and sidebar
render_sidebar()

# ── Navigation Context ────────────────────────────────────────────────────
st.markdown("""
<div class="page-navigation fade-in">
    <div class="nav-breadcrumb">
        <span class="nav-step completed">Overview</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step completed">Telemetry Platform</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step completed">Survival Analytics</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step current">Decision Intelligence</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step upcoming">Experiment Evaluation</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step upcoming">Executive Decision</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Page header
page_header(
    "Decision Intelligence Engine",
    "Phase 3 Output — Rule-based player interventions with priority scoring",
    icon="🎯"
)

# Load artifacts
decisions = load_player_decisions()
segment_summary = load_segment_summary()
rules = load_decision_rules()
master_df = load_master_player_df()

if decisions is None or decisions.empty:
    st.error("⚠️ Decision engine artifacts not found. Run Phase 3 first.")
    st.stop()

# Overview metrics
section_header("Decision Engine Overview", "Player recommendations and priority scores")

n_players = len(decisions)
n_categories = decisions["action_category"].nunique() if "action_category" in decisions.columns else 0
avg_priority = decisions["priority_score"].mean() if "priority_score" in decisions.columns else 0
high_priority_n = len(decisions[decisions["action_category"] == "High Priority Reactivation"]) if "action_category" in decisions.columns else 0

metric_row([
    {"label": "Players Analyzed", "value": fmt_number(n_players), "icon": "👥", "accent": "blue"},
    {"label": "Recommendation Categories", "value": str(n_categories), "icon": "📋", "accent": "success"},
    {"label": "Average Priority Score", "value": fmt_float(avg_priority, 3), "icon": "⚡", "accent": "warning"},
    {"label": "High Priority Interventions", "value": fmt_number(high_priority_n), "icon": "🔴", "accent": "error"},
])

st.markdown("<br>", unsafe_allow_html=True)

# Business rules summary
if rules:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Business Rules Applied**")
        business_rules = rules.get("business_rules", [])
        st.markdown(f"- **Total rules:** {len(business_rules)}")
        
        # Show rule categories
        categories = set()
        for rule in business_rules:
            categories.add(rule.get("action", "Unknown"))
        st.markdown(f"- **Action types:** {len(categories)}")
        st.markdown(f"- **Coverage:** 100% of players")
        
    with col2:
        st.markdown("**Priority Score Distribution**")
        if "priority_score" in decisions.columns:
            # Quartile breakdown
            q1 = decisions["priority_score"].quantile(0.25)
            q2 = decisions["priority_score"].quantile(0.5)
            q3 = decisions["priority_score"].quantile(0.75)
            st.markdown(f"- **Q1 (25th percentile):** {q1:.3f}")
            st.markdown(f"- **Q2 (Median):** {q2:.3f}")
            st.markdown(f"- **Q3 (75th percentile):** {q3:.3f}")

st.divider()

# Decision rules detail
section_header("Business Rules Engine", "Deterministic logic for player intervention recommendations")

if rules and "business_rules" in rules:
    with st.expander("📋 View All Business Rules", expanded=False):
        business_rules = rules["business_rules"]
        for i, rule in enumerate(business_rules, 1):
            st.markdown(f"**Rule {i}: {rule.get('name', 'Unnamed Rule')}**")
            st.markdown(f"- **Condition:** {rule.get('condition', 'N/A')}")
            st.markdown(f"- **Action:** {rule.get('action', 'N/A')}")
            st.markdown(f"- **Priority Method:** {rule.get('priority_calculation', 'N/A')}")
            if i < len(business_rules):
                st.markdown("---")

st.divider()

# Recommendation distributions
section_header("Player Recommendations", "Distribution of intervention categories and priority scores")

col1, col2 = st.columns(2)
with col1:
    if "action_category" in decisions.columns:
        st.plotly_chart(recommendation_distribution_chart(decisions), use_container_width=True, config={"displayModeBar": False})

with col2:
    if "priority_score" in decisions.columns and "action_category" in decisions.columns:
        st.plotly_chart(priority_score_distribution(decisions), use_container_width=True, config={"displayModeBar": False})

st.divider()

# Player journey flow
section_header("Player Journey Analysis", "Flow from lifecycle stage through risk assessment to recommendations")

if master_df is not None and all(col in master_df.columns for col in ["lifecycle_stage", "risk_group", "action_category"]):
    st.plotly_chart(player_journey_sankey(master_df), use_container_width=True, config={"displayModeBar": False})
    info_callout("Sankey diagram shows the complete player journey from lifecycle segmentation (Phase 1) → risk scoring (Phase 2) → intervention recommendations (Phase 3)")
else:
    excluded_segment_note("Player Journey", "Master player dataframe not available or missing required columns")

st.divider()

# Segment-level insights
section_header("Segment Performance", "Recommendation outcomes by player segments")

if segment_summary:
    segments = segment_summary.get("segments", {})
    if segments:
        # Show top segments by various metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Top Segments by Player Count**")
            # Sort segments by player count
            segment_items = [(name, data) for name, data in segments.items()]
            segment_items.sort(key=lambda x: x[1].get("player_count", 0), reverse=True)
            
            for name, data in segment_items[:5]:
                count = data.get("player_count", 0)
                d7_rate = data.get("retention_7_rate", 0)
                st.markdown(f"- **{name}:** {fmt_number(count)} players (D7: {fmt_pct(d7_rate)})")
        
        with col2:
            st.markdown("**Intervention Priority**")
            # Show segments with highest priority scores
            segment_items.sort(key=lambda x: x[1].get("avg_priority_score", 0), reverse=True)
            
            for name, data in segment_items[:5]:
                avg_priority = data.get("avg_priority_score", 0)
                dominant_action = data.get("dominant_action", "Unknown")
                st.markdown(f"- **{name}:** Priority {avg_priority:.3f}")
                st.markdown(f"  → {dominant_action}")

st.divider()

# Player lookup
section_header("Individual Player Recommendations", "Search for specific player intervention recommendations")

if master_df is not None:
    with st.expander("🔍 Player Decision Lookup", expanded=False):
        # Simple search by userid
        col1, col2 = st.columns([3, 1])
        with col1:
            search_userid = st.number_input("Enter Player ID (userid)", min_value=int(master_df["userid"].min()), max_value=int(master_df["userid"].max()), value=int(master_df["userid"].iloc[0]))
        with col2:
            search_button = st.button("Search Player")
        
        if search_button or search_userid:
            player = master_df[master_df["userid"] == search_userid]
            if not player.empty:
                p = player.iloc[0]
                priority_score = p.get("priority_score", 0)
                player_data = {
                    "Player ID": f"{int(p['userid'])}",
                    "Lifecycle Stage": p.get("lifecycle_stage", "N/A"),
                    "Risk Group": p.get("risk_group", "N/A"),
                    "Action Category": p.get("action_category", "N/A"),
                    "Priority Score": fmt_float(priority_score, 4),
                    "Priority Band": priority_band(priority_score),
                    "Recommended Intervention": p.get("intervention", "N/A"),
                    "Sessions per Day": fmt_float(p.get("sessions_per_day", 0), 2)
                }
                player_card(player_data)
                
                # Show reasoning
                if priority_score > 0.8:
                    st.error("🚨 **Critical Priority**: Immediate intervention recommended")
                elif priority_score > 0.6:
                    st.warning("⚠️ **High Priority**: Schedule intervention within 48 hours")
                elif priority_score > 0.4:
                    st.info("ℹ️ **Medium Priority**: Monitor and intervene if behavior worsens")
                else:
                    st.success("✅ **Low Priority**: Continue standard engagement")
            else:
                st.warning(f"Player {search_userid} not found in dataset.")

# Footer
render_artifact_footer([
    ("player_decisions.parquet", "Individual player recommendations (n=90,189)"),
    ("segment_summary.json", "Segment-level performance metrics"),
    ("decision_rules.json", "Business logic and rule definitions"),
])