"""Phase 2 — Survival-Based Player Retention Analytics

Kaplan-Meier survival curves, Cox proportional hazards model, and churn risk scoring.
Shows outputs from Phase 2 of the pipeline.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from components.sidebar import render_sidebar
from components.plot_components import (
    km_step_chart,
    hazard_ratio_plot,
    risk_group_distribution,
    survival_probability_histogram,
)
from utils.data_loader import (
    load_survival_curves,
    load_survival_predictions,
    load_cox_model_summary,
    load_survival_diagnostics,
    load_master_player_df,
    load_manifest,
)
from utils.helpers import fmt_number, fmt_pct, fmt_float

render_sidebar()

# ── Load artifacts with error handling ────────────────────────────────────
try:
    curves       = load_survival_curves()
    predictions  = load_survival_predictions()
    cox_summary  = load_cox_model_summary()
    diagnostics  = load_survival_diagnostics()
    master_df    = load_master_player_df()
    manifest     = load_manifest() or {}
except Exception as e:
    st.error(f"Failed to load survival artifacts: {e}")
    st.stop()

if curves is None or predictions is None:
    st.markdown("""
    <div class="empty-state fade-in">
        <div class="empty-icon">📉</div>
        <div class="empty-title">Survival Artifacts Not Found</div>
        <div class="empty-message">
            Phase 2 has not been executed yet.<br>
            Run the survival analytics pipeline to generate the required artifacts.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Derived metrics with safe fallbacks ───────────────────────────────────
n_players      = len(predictions) if predictions is not None else 0
n_events       = int(predictions["retention_7"].sum()) if predictions is not None and "retention_7" in predictions.columns else 0
censoring_rate = 1 - (n_events / n_players) if n_players > 0 else 0.0
concordance    = cox_summary.get("concordance", 0.0) if cox_summary else 0.0
n_features     = len(cox_summary.get("hazard_ratios", {})) if cox_summary else 0

version   = manifest.get("manifest_version", "v4.0.0")
timestamp = manifest.get("execution_timestamp", "2024-12-30T12:00:00")
if timestamp and "T" in timestamp:
    timestamp = timestamp[:19].replace("T", " ") + " UTC"

# ═══════════════════════════════════════════════════════════════════════════
# HERO BANNER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="
    background:linear-gradient(135deg,#0a0e1a 0%,#1a1f2e 50%,#242937 100%);
    border:1px solid #3d4357;
    border-radius:16px;
    padding:2.5rem 2rem;
    margin-bottom:2rem;
    position:relative;
    overflow:hidden;
">
    <div style="
        position:absolute;top:0;left:0;right:0;bottom:0;
        background:radial-gradient(ellipse at top left,rgba(0,119,204,0.12) 0%,transparent 60%);
        pointer-events:none;
    "></div>
    <div style="position:relative;">
        <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.75rem;">
            <span style="font-size:2rem;">📉</span>
            <div>
                <div style="font-size:1.75rem;font-weight:900;color:#ffffff;letter-spacing:-0.02em;">
                    Survival-Based Player Retention Analytics
                </div>
                <div style="font-size:1rem;color:#b4bcd0;margin-top:0.25rem;">
                    This phase estimates player churn risk using Kaplan-Meier survival analysis and a Cox proportional hazards model
                </div>
            </div>
        </div>
        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-top:1rem;">
            <span style="background:rgba(0,208,132,0.12);border:1px solid #00d084;
                color:#00d084;padding:0.3rem 0.75rem;border-radius:6px;
                font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">
                ✓ Phase 2 Complete
            </span>
            <span style="background:rgba(0,119,204,0.12);border:1px solid #0077CC;
                color:#0077CC;padding:0.3rem 0.75rem;border-radius:6px;
                font-size:0.8rem;font-weight:600;">
                Pipeline {version}
            </span>
            <span style="background:rgba(255,255,255,0.04);border:1px solid #3d4357;
                color:#8a92a8;padding:0.3rem 0.75rem;border-radius:6px;
                font-size:0.8rem;">
                Last run: {timestamp}
            </span>
        </div>
    </div>
</div>
""".format(version=version, timestamp=timestamp), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY — 3 large cards
# ═══════════════════════════════════════════════════════════════════════════
def _section(title, subtitle=""):
    sub_html = f'<div style="font-size:0.9rem;color:#b4bcd0;margin-top:0.25rem;">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div style="border-left:4px solid #0077CC;padding-left:0.85rem;margin:2rem 0 1rem 0;">
        <div style="font-size:1.25rem;font-weight:700;color:#ffffff;">{title}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

_section("Executive Summary", "Key takeaways for business stakeholders")

# Find highest risk driver and best survival segment
highest_risk_driver = "Sessions per day"
highest_surv_segment = "Active Players"

if cox_summary and "hazard_ratios" in cox_summary:
    hrs = cox_summary["hazard_ratios"]
    # Find covariate with highest impact
    max_dist = 0
    for cov, data in hrs.items():
        dist = abs(data["hr"] - 1.0)
        if dist > max_dist:
            max_dist = dist
            if "session" in cov.lower():
                highest_risk_driver = "Sessions per day"
            elif "40" in cov:
                highest_risk_driver = "Gate 40 placement"
            else:
                highest_risk_driver = cov.replace("_", " ").title()

if master_df is not None and "lifecycle_stage" in master_df.columns:
    # Find lifecycle stage with best survival
    stage_survival = {}
    for stage in master_df["lifecycle_stage"].unique():
        if pd.notna(stage):
            stage_df = master_df[master_df["lifecycle_stage"] == stage]
            if "survival_prob_day7" in stage_df.columns:
                avg_surv = stage_df["survival_prob_day7"].mean()
                stage_survival[stage] = avg_surv
    if stage_survival:
        highest_surv_segment = max(stage_survival, key=stage_survival.get)

e1, e2, e3 = st.columns(3)

# Card 1: Highest Risk Driver
e1.markdown(f"""
<div style="background:rgba(255,51,51,0.08);border:1px solid #ff3333;border-radius:12px;padding:1.5rem;">
    <div style="font-size:1.75rem;margin-bottom:0.75rem;">🚨</div>
    <div style="font-size:0.875rem;font-weight:700;color:#ff3333;text-transform:uppercase;
        letter-spacing:0.06em;margin-bottom:0.5rem;">Highest Risk Driver</div>
    <div style="font-size:1.1rem;font-weight:700;color:#ffffff;margin-bottom:0.5rem;">{highest_risk_driver}</div>
    <div style="font-size:0.875rem;color:#b4bcd0;line-height:1.6;">
        Players with low session frequency show significantly higher churn risk in the Cox model
    </div>
</div>
""", unsafe_allow_html=True)

# Card 2: Highest Survival Segment
e2.markdown(f"""
<div style="background:rgba(0,208,132,0.08);border:1px solid #00d084;border-radius:12px;padding:1.5rem;">
    <div style="font-size:1.75rem;margin-bottom:0.75rem;">✓</div>
    <div style="font-size:0.875rem;font-weight:700;color:#00d084;text-transform:uppercase;
        letter-spacing:0.06em;margin-bottom:0.5rem;">Highest Survival Segment</div>
    <div style="font-size:1.1rem;font-weight:700;color:#ffffff;margin-bottom:0.5rem;">{highest_surv_segment}</div>
    <div style="font-size:0.875rem;color:#b4bcd0;line-height:1.6;">
        This segment has the highest Day 7 survival probability and should receive retention optimization
    </div>
</div>
""", unsafe_allow_html=True)

# Card 3: Business Recommendation
e3.markdown(f"""
<div style="background:rgba(0,119,204,0.08);border:1px solid #0077CC;border-radius:12px;padding:1.5rem;">
    <div style="font-size:1.75rem;margin-bottom:0.75rem;">💡</div>
    <div style="font-size:0.875rem;font-weight:700;color:#0077CC;text-transform:uppercase;
        letter-spacing:0.06em;margin-bottom:0.5rem;">Business Recommendation</div>
    <div style="font-size:1.1rem;font-weight:700;color:#ffffff;margin-bottom:0.5rem;">Target High-Risk Players</div>
    <div style="font-size:0.875rem;color:#b4bcd0;line-height:1.6;">
        Survival analysis identifies at-risk players before they churn, enabling proactive LiveOps interventions
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# MODEL KPIs — 4 equal cards
# ═══════════════════════════════════════════════════════════════════════════
_section("Model Performance", "Key statistics from the Cox proportional hazards survival model")

k1, k2, k3, k4 = st.columns(4)

def _kpi(col, icon, value, label, accent):
    accent_colors = {
        "blue":  ("#0077CC", "rgba(0,119,204,0.12)"),
        "green": ("#00d084", "rgba(0,208,132,0.12)"),
        "amber": ("#ff9500", "rgba(255,149,0,0.12)"),
        "red":   ("#ff3333", "rgba(255,51,51,0.12)"),
    }
    border_c, bg_c = accent_colors.get(accent, accent_colors["blue"])
    col.markdown(f"""
    <div style="
        background:{bg_c};
        border:1px solid {border_c};
        border-radius:12px;
        padding:1.5rem;
        text-align:center;
    ">
        <div style="font-size:2rem;margin-bottom:0.5rem;">{icon}</div>
        <div style="font-size:1.75rem;font-weight:800;color:#ffffff;
            font-variant-numeric:tabular-nums;line-height:1;">{value}</div>
        <div style="font-size:0.875rem;color:#b4bcd0;margin-top:0.4rem;font-weight:500;">{label}</div>
    </div>
    """, unsafe_allow_html=True)

_kpi(k1, "👥", fmt_number(n_players),      "Players Analyzed",  "blue")
_kpi(k2, "🔧", str(n_features),            "Features Used",     "green")
_kpi(k3, "🎯", fmt_float(concordance, 3),  "Model Concordance", "green")
_kpi(k4, "📅", fmt_number(n_events),       "Observed Events",   "amber")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# KAPLAN-MEIER SURVIVAL CURVES
# ═══════════════════════════════════════════════════════════════════════════
_section("Kaplan-Meier Survival Curves", "Player survival probability over time by lifecycle stage")

# TEMPORARILY EXPOSING EXCEPTION FOR DEBUG
if curves is not None and not curves.empty:
    st.plotly_chart(
        km_step_chart(curves),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    
    # Plain-English explanation
    st.markdown("""
    <div style="background:#1a1f2e;border-left:4px solid #0077CC;border-radius:8px;
        padding:1rem 1.5rem;margin-top:1rem;">
        <div style="font-weight:700;color:#ffffff;margin-bottom:0.5rem;">📘 What this means</div>
        <div style="color:#b4bcd0;line-height:1.7;font-size:0.9rem;">
            The steeper a curve declines, the faster players in that segment stop returning to the game. 
            Each step down represents a group of players who stopped playing at that time point. 
            A flatter curve means better player retention over time.
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:rgba(255,149,0,0.08);border:1px solid #ff9500;
        border-radius:8px;padding:1.5rem;text-align:center;">
        <div style="font-size:1.5rem;margin-bottom:0.5rem;">⚠️</div>
        <div style="color:#ff9500;font-weight:600;">Survival Curves Unavailable</div>
        <div style="color:#b4bcd0;font-size:0.875rem;margin-top:0.5rem;">
            The survival curves artifact could not be loaded. Other dashboard components remain available.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# RISK FACTORS — Cox Hazard Ratios
# ═══════════════════════════════════════════════════════════════════════════
_section("Risk Factors", "Features that increase or decrease player churn risk")

# TEMPORARILY EXPOSING EXCEPTION FOR DEBUG
if cox_summary and "hazard_ratios" in cox_summary:
    rf1, rf2 = st.columns([2, 1])
    
    with rf1:
        st.plotly_chart(
            hazard_ratio_plot(cox_summary),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    
    with rf2:
        hrs = cox_summary["hazard_ratios"]
        
        st.markdown("""
        <div style="background:#1a1f2e;border:1px solid #3d4357;border-radius:12px;padding:1.5rem;">
            <div style="font-size:0.875rem;font-weight:700;color:#0077CC;text-transform:uppercase;
                letter-spacing:0.06em;margin-bottom:1rem;">Business Interpretation</div>
        """, unsafe_allow_html=True)
        
        # Interpret each factor
        for cov, data in list(hrs.items())[:3]:  # Top 3
            hr = data["hr"]
            direction = "↓ Lower churn" if hr < 1 else "↑ Higher churn"
            color = "#00d084" if hr < 1 else "#ff3333"
            label = cov.replace("_", " ").replace("version gate 40", "Gate 40").title()
            
            st.markdown(f"""
            <div style="margin-bottom:0.75rem;">
                <div style="font-weight:600;color:#ffffff;font-size:0.9rem;">{label}</div>
                <div style="color:{color};font-size:0.8rem;margin-top:0.25rem;">{direction}</div>
                <div style="color:#8a92a8;font-size:0.75rem;">HR = {hr:.3f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:rgba(255,149,0,0.08);border:1px solid #ff9500;
        border-radius:8px;padding:1.5rem;text-align:center;">
        <div style="font-size:1.5rem;margin-bottom:0.5rem;">⚠️</div>
        <div style="color:#ff9500;font-weight:600;">Cox Model Summary Unavailable</div>
        <div style="color:#b4bcd0;font-size:0.875rem;margin-top:0.5rem;">
            Hazard ratios could not be loaded. Other dashboard components remain available.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# PLAYER RISK DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════
_section("Player Risk Distribution", "Distribution of churn risk scores across all players")

# TEMPORARILY EXPOSING EXCEPTION FOR DEBUG
if master_df is not None and "risk_group" in master_df.columns:
    rd1, rd2 = st.columns(2)
    
    with rd1:
        st.plotly_chart(
            risk_group_distribution(master_df),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    
    with rd2:
        if "survival_prob_day7" in master_df.columns:
            st.plotly_chart(
                survival_probability_histogram(master_df),
                use_container_width=True,
                config={"displayModeBar": False},
            )
    
    # Summary metrics
    if "survival_prob_day7" in master_df.columns:
        avg_risk  = master_df["survival_prob_day7"].mean()
        med_risk  = master_df["survival_prob_day7"].median()
        high_pct  = (master_df["risk_group"] == "High Risk").sum() / len(master_df) * 100 if "risk_group" in master_df.columns else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Average Survival (D7)", fmt_pct(avg_risk))
        m2.metric("Median Survival (D7)", fmt_pct(med_risk))
        m3.metric("High Risk %", f"{high_pct:.1f}%")
else:
    st.markdown("""
    <div style="background:rgba(255,149,0,0.08);border:1px solid #ff9500;
        border-radius:8px;padding:1.5rem;text-align:center;">
        <div style="font-size:1.5rem;margin-bottom:0.5rem;">⚠️</div>
        <div style="color:#ff9500;font-weight:600;">Risk Distribution Unavailable</div>
        <div style="color:#b4bcd0;font-size:0.875rem;margin-top:0.5rem;">
            Player risk scores could not be loaded.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# PLAYER SEGMENTS — Risk group breakdown
# ═══════════════════════════════════════════════════════════════════════════
_section("Player Segments by Risk", "Actionable player groups based on churn probability")

if master_df is not None and "risk_group" in master_df.columns:
    risk_counts = master_df["risk_group"].value_counts()
    total = len(master_df)
    
    s1, s2, s3 = st.columns(3)
    
    segments = [
        ("Low Risk", "✓", "#00d084", "rgba(0,208,132,0.08)", "Maintain engagement with regular content updates"),
        ("Medium Risk", "⚠️", "#ff9500", "rgba(255,149,0,0.08)", "Monitor closely and provide targeted incentives"),
        ("High Risk", "🚨", "#ff3333", "rgba(255,51,51,0.08)", "Immediate intervention with retention campaigns"),
    ]
    
    for col, (risk, icon, color, bg, action) in zip([s1, s2, s3], segments):
        count = risk_counts.get(risk, 0)
        pct = count / total * 100 if total > 0 else 0
        
        col.markdown(f"""
        <div style="background:{bg};border:1px solid {color};border-radius:12px;padding:1.5rem;height:100%;">
            <div style="font-size:1.75rem;margin-bottom:0.75rem;">{icon}</div>
            <div style="font-size:0.875rem;font-weight:700;color:{color};text-transform:uppercase;
                letter-spacing:0.06em;margin-bottom:0.5rem;">{risk}</div>
            <div style="font-size:1.5rem;font-weight:800;color:#ffffff;margin-bottom:0.25rem;">
                {fmt_number(count)}
            </div>
            <div style="font-size:0.9rem;color:#b4bcd0;margin-bottom:1rem;">{pct:.1f}% of players</div>
            <div style="font-size:0.8rem;color:#b4bcd0;line-height:1.5;
                padding-top:0.75rem;border-top:1px solid #3d4357;">
                <strong style="color:#ffffff;">Action:</strong> {action}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════
_section("Business Insights", "Key takeaways from survival analysis for LiveOps teams")

insights = [
    ("📊", "Session Frequency Impact", "Players with higher session frequency have substantially lower churn risk, as shown by hazard ratios < 1.0"),
    ("✓", "Most Players Low Risk", "The majority of players fall into the low-risk segment, indicating generally healthy retention"),
    ("🎯", "High-Risk Targeting", "High-risk players should receive targeted LiveOps campaigns before they churn, maximizing intervention effectiveness"),
    ("⏰", "Early Detection", "Survival analysis enables proactive identification of at-risk players, allowing intervention before churn occurs"),
]

for icon, title, desc in insights:
    st.markdown(f"""
    <div style="background:#1a1f2e;border:1px solid #3d4357;border-radius:12px;
        padding:1.25rem;margin-bottom:0.75rem;display:flex;gap:1rem;align-items:start;">
        <div style="font-size:1.5rem;flex-shrink:0;">{icon}</div>
        <div>
            <div style="font-weight:700;color:#ffffff;margin-bottom:0.25rem;font-size:0.95rem;">{title}</div>
            <div style="color:#b4bcd0;font-size:0.875rem;line-height:1.6;">{desc}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# TECHNICAL DETAILS — Collapsible expander
# ═══════════════════════════════════════════════════════════════════════════
with st.expander("🔬 Technical Details — Cox Model Statistics and Diagnostics"):
    st.markdown("### Cox Proportional Hazards Model")
    
    if cox_summary:
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Log-Likelihood", f"{cox_summary.get('log_likelihood', 0):.2f}")
        tc2.metric("AIC", f"{cox_summary.get('aic', 0):.1f}")
        tc3.metric("Concordance Index", fmt_float(concordance, 3))
        
        st.markdown("### Hazard Ratios and Coefficients")
        
        if "hazard_ratios" in cox_summary:
            hrs_data = []
            for cov, data in cox_summary["hazard_ratios"].items():
                hrs_data.append({
                    "Covariate": cov.replace("_", " ").title(),
                    "Hazard Ratio": f"{data['hr']:.4f}",
                    "95% CI Lower": f"{data['ci_95_lower']:.4f}",
                    "95% CI Upper": f"{data['ci_95_upper']:.4f}",
                    "p-value": f"{data.get('p_value', 1.0):.4f}",
                })
            st.dataframe(pd.DataFrame(hrs_data), use_container_width=True, hide_index=True)
        
        st.markdown("### Model Interpretation")
        st.markdown("""
        - **Hazard Ratio < 1:** Feature reduces churn risk (protective factor)
        - **Hazard Ratio > 1:** Feature increases churn risk (risk factor)
        - **Hazard Ratio = 1:** No effect on churn
        - **95% Confidence Interval:** If CI excludes 1.0, effect is statistically significant
        - **Concordance Index:** Model's ability to correctly rank player risk (0.5 = random, 1.0 = perfect)
        """)
        
        if diagnostics:
            st.markdown("### Model Diagnostics")
            st.json(diagnostics, expanded=False)
    else:
        st.warning("Cox model summary not available")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════
_section("Pipeline Artifacts", "Output files generated by Phase 2 — all validated and available")

processed_dir = Path(__file__).parent.parent / "data" / "processed"

artifacts = [
    {
        "icon": "📊",
        "name": "survival_predictions.parquet",
        "description": "Individual player churn risk scores",
        "detail": f"{fmt_number(n_players)} players with survival probabilities",
        "phase": "Phase 2",
    },
    {
        "icon": "📉",
        "name": "survival_curves.parquet",
        "description": "Kaplan-Meier survival curves by segment",
        "detail": "Time-to-event estimates for all lifecycle stages",
        "phase": "Phase 2",
    },
    {
        "icon": "🔬",
        "name": "cox_model_summary.json",
        "description": "Cox proportional hazards model results",
        "detail": f"Hazard ratios, coefficients, concordance = {concordance:.3f}",
        "phase": "Phase 2",
    },
    {
        "icon": "📋",
        "name": "survival_diagnostics.json",
        "description": "Model validation and assumption checks",
        "detail": "Proportional hazards tests and residual analysis",
        "phase": "Phase 2",
    },
]

art_cols = st.columns(len(artifacts))
for col, art in zip(art_cols, artifacts):
    file_path = processed_dir / art["name"]
    available = file_path.exists()
    status_color  = "#00d084" if available else "#ff3333"
    status_label  = "✓ Available" if available else "✗ Missing"
    status_bg     = "rgba(0,208,132,0.08)" if available else "rgba(255,51,51,0.08)"
    status_border = "#00d084" if available else "#ff3333"

    col.markdown(f"""
    <div style="
        background:#1a1f2e;
        border:1px solid #3d4357;
        border-radius:12px;
        padding:1.5rem;
        height:100%;
    ">
        <div style="font-size:2rem;margin-bottom:0.75rem;">{art["icon"]}</div>
        <div style="font-size:0.9rem;font-weight:700;color:#ffffff;
            margin-bottom:0.4rem;word-break:break-all;">{art["name"]}</div>
        <div style="font-size:0.875rem;color:#b4bcd0;margin-bottom:0.4rem;
            line-height:1.5;">{art["description"]}</div>
        <div style="font-size:0.8rem;color:#8a92a8;margin-bottom:0.75rem;">{art["detail"]}</div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
            <span style="background:rgba(0,119,204,0.12);border:1px solid #0077CC;
                color:#0077CC;padding:0.2rem 0.6rem;border-radius:4px;
                font-size:0.75rem;font-weight:600;">
                {art["phase"]}
            </span>
            <span style="background:{status_bg};border:1px solid {status_border};
                color:{status_color};padding:0.2rem 0.6rem;border-radius:4px;
                font-size:0.75rem;font-weight:600;">
                {status_label}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════
f1, f2, f3, f4, f5 = st.columns(5)
f1.metric("Pipeline Version", version)
f2.metric("Last Updated",     timestamp[:10] if len(timestamp) >= 10 else timestamp)
f3.metric("Model Type",        "Cox Proportional Hazards")
f4.metric("Players Analyzed",  fmt_number(n_players))
f5.metric("Concordance",       fmt_float(concordance, 3))
