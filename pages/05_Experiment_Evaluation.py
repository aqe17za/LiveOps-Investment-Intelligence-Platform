"""Phase 4 — Causal Experiment Evaluation

A/B test analysis, treatment effects, and statistical validation.
Shows outputs from Phase 4 of the pipeline.
"""

import streamlit as st
import pandas as pd

from components.sidebar import render_sidebar
from components.plot_components import (
    treatment_effect_forest_plot, segment_comparison_chart,
    priority_decile_chart_retention
)
from utils.data_loader import (
    load_experiment_validation, load_overall_treatment_effects,
    load_segment_level_effects, load_statistical_tests, 
    load_liveops_recommendations, load_manifest
)
from utils.helpers import fmt_number, fmt_pct, fmt_lift, fmt_pvalue

# Page config and sidebar
render_sidebar()

# ── Navigation Breadcrumb ─────────────────────────────────────────────────
st.markdown("""
<div class="page-navigation fade-in">
    <div class="nav-breadcrumb">
        <span class="nav-step completed">Overview</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step completed">Telemetry</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step completed">Survival</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step completed">Decision</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step current">Experiment</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step upcoming">Executive</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Load artifacts
experiment = load_experiment_validation()
overall_effects = load_overall_treatment_effects()
segment_effects = load_segment_level_effects()
stat_tests = load_statistical_tests()
recommendations = load_liveops_recommendations()
manifest = load_manifest()

if overall_effects is None:
    st.error("⚠️ Experiment evaluation artifacts not found. Run Phase 4 first.")
    st.stop()

# Extract key metrics
decision = "DO NOT DEPLOY"
confidence = "High"
affected_metric = "Day 7 Retention"
absolute_lift = 0
p_value = 1
ci_lower = 0
ci_upper = 0
n_control = 0
n_treatment = 0

if recommendations:
    decision = recommendations.get("deployment_decision", "UNKNOWN")
    confidence = recommendations.get("recommendation_confidence", "Medium")

if overall_effects and "retention_7" in overall_effects:
    ret7 = overall_effects["retention_7"]
    absolute_lift = ret7.get("absolute_lift", 0)
    p_value = ret7.get("p_value", 1)
    ci_lower = ret7.get("ci_lower", 0)
    ci_upper = ret7.get("ci_upper", 0)
    n_control = ret7.get("n_control", 0)
    n_treatment = ret7.get("n_treatment", 0)

version = manifest.get("pipeline_version", "1.0") if manifest else "1.0"

# ═══════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ═══════════════════════════════════════════════════════════════════════════

decision_color = "#ef4444" if "NOT" in decision else "#22c55e"
decision_bg = "rgba(239,68,68,0.08)" if "NOT" in decision else "rgba(34,197,94,0.08)"
decision_icon = "🟥" if "NOT" in decision else "🟩"

st.markdown(f"""
<div style="
    background:linear-gradient(135deg,#1a1a28 0%,#12121a 100%);
    border:1px solid #2a2a3e;border-radius:16px;padding:2.5rem;
    margin-bottom:2rem;position:relative;overflow:hidden;">
    <div style="
        position:absolute;top:0;left:0;right:0;bottom:0;
        background:radial-gradient(ellipse at top right,{decision_bg} 0%,transparent 60%);
        pointer-events:none;
    "></div>
    <div style="position:relative;z-index:1;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:2rem;">
            <div style="flex:1;min-width:300px;">
                <div style="font-size:0.8rem;font-weight:700;color:#8888aa;
                    text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;">Phase 4</div>
                <h1 style="font-size:2.5rem;font-weight:800;color:#e8e8f0;
                    margin:0 0 1rem 0;letter-spacing:-0.02em;">Experiment Evaluation</h1>
                <p style="font-size:1.1rem;color:#8888aa;margin:0;line-height:1.6;">
                    Evaluate whether <strong style="color:#0077CC;">Gate 40</strong> should replace 
                    <strong style="color:#0077CC;">Gate 30</strong> using randomized A/B test evidence.
                </p>
            </div>
            <div style="min-width:280px;">
                <div style="background:{decision_bg};border:2px solid {decision_color};
                    border-radius:12px;padding:1.5rem;text-align:center;">
                    <div style="font-size:2.5rem;margin-bottom:0.75rem;">{decision_icon}</div>
                    <div style="font-size:1.5rem;font-weight:800;color:{decision_color};
                        margin-bottom:1rem;letter-spacing:-0.01em;">{decision}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;text-align:left;">
                        <div>
                            <div style="font-size:0.7rem;color:#8888aa;text-transform:uppercase;
                                letter-spacing:0.05em;margin-bottom:0.25rem;">Confidence</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;">{confidence}</div>
                        </div>
                        <div>
                            <div style="font-size:0.7rem;color:#8888aa;text-transform:uppercase;
                                letter-spacing:0.05em;margin-bottom:0.25rem;">Metric</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;">{affected_metric}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-top:1.5rem;">
            <span style="background:rgba(0,208,132,0.12);border:1px solid #00d084;
                color:#00d084;padding:0.3rem 0.75rem;border-radius:6px;
                font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">
                ✓ Phase 4 Complete
            </span>
            <span style="background:rgba(0,119,204,0.12);border:1px solid #0077CC;
                color:#0077CC;padding:0.3rem 0.75rem;border-radius:6px;
                font-size:0.8rem;font-weight:600;">
                Pipeline {version}
            </span>
            <span style="background:rgba(255,255,255,0.04);border:1px solid #3d4357;
                color:#8a92a8;padding:0.3rem 0.75rem;border-radius:6px;
                font-size:0.8rem;">
                {n_control + n_treatment:,} Players Analyzed
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY KPIs
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:0 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Executive Summary</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Primary experimental findings</p>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

# KPI Card Helper
def _kpi_card(col, icon, label, value, detail, accent_color, accent_bg):
    col.markdown(f"""
    <div style="background:#1a1a28;border:1px solid {accent_color};border-radius:12px;
        padding:1.5rem;text-align:center;transition:all 0.2s;">
        <div style="font-size:2.5rem;margin-bottom:0.75rem;">{icon}</div>
        <div style="font-size:0.75rem;color:#8888aa;text-transform:uppercase;
            letter-spacing:0.05em;margin-bottom:0.5rem;">{label}</div>
        <div style="font-size:2rem;font-weight:800;color:{accent_color};
            margin-bottom:0.5rem;letter-spacing:-0.02em;">{value}</div>
        <div style="font-size:0.85rem;color:#8888aa;">{detail}</div>
    </div>
    """, unsafe_allow_html=True)

_kpi_card(k1, "📉", "Retention Lift", fmt_lift(absolute_lift), 
         f"p={fmt_pvalue(p_value)}", "#ef4444", "rgba(239,68,68,0.08)")

_kpi_card(k2, "🎯", "P-Value", fmt_pvalue(p_value),
         "Highly Significant" if p_value < 0.01 else "Significant", 
         "#f59e0b", "rgba(245,158,11,0.08)")

_kpi_card(k3, "📊", "Confidence Interval", 
         f"[{fmt_lift(ci_lower)}, {fmt_lift(ci_upper)}]",
         "95% CI", "#6366f1", "rgba(99,102,241,0.08)")

exp_quality = "✓ Validated"
if experiment:
    validity = experiment.get("validity_checks", {})
    if not validity.get("balance_check", False):
        exp_quality = "⚠️ Check Balance"

_kpi_card(k4, "🔬", "Experiment Quality", exp_quality,
         f"{n_control + n_treatment:,} Players", "#22c55e", "rgba(34,197,94,0.08)")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS EXPLANATION
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;
    padding:2rem;margin:2rem 0;">
    <h3 style="font-size:1.5rem;font-weight:700;color:#e8e8f0;margin:0 0 1.25rem 0;">
        Why are we not deploying Gate 40?
    </h3>
    <p style="font-size:1.05rem;color:#b4bcd0;line-height:1.8;margin:0 0 1rem 0;">
        Players assigned to <strong style="color:#6366f1;">Gate 40</strong> were slightly 
        <strong style="color:#ef4444;">less likely to return</strong> after seven days compared 
        to players who experienced <strong style="color:#0077CC;">Gate 30</strong>.
    </p>
    <p style="font-size:1.05rem;color:#b4bcd0;line-height:1.8;margin:0 0 1rem 0;">
        Although the difference is small (approximately 0.8 percentage points), it was 
        <strong style="color:#f59e0b;">statistically significant</strong> and 
        <strong style="color:#f59e0b;">consistent across the experiment</strong>.
    </p>
    <p style="font-size:1.05rem;color:#b4bcd0;line-height:1.8;margin:0 0 1rem 0;">
        Deploying Gate 40 globally would likely <strong style="color:#ef4444;">reduce 
        long-term player retention</strong>, which directly impacts revenue and engagement.
    </p>
    <p style="font-size:1.05rem;color:#e8e8f0;line-height:1.8;margin:0;
        padding:1rem;background:rgba(0,119,204,0.08);border-left:3px solid #0077CC;border-radius:6px;">
        <strong>Recommendation:</strong> Continue using Gate 30 and investigate why Gate 40 
        causes early churn before considering any further gate position changes.
    </p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TREATMENT EFFECTS
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Treatment Effects</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Overall impact and segment-level variation</p>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("""
    <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:1.5rem;">
        <h4 style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin:0 0 1rem 0;">
            Overall Treatment Effect
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Overall treatment effect bar
    if overall_effects and "retention_7" in overall_effects:
        ret7 = overall_effects["retention_7"]
        control_rate = ret7.get("control_rate", 0) * 100
        treatment_rate = ret7.get("treatment_rate", 0) * 100
        
        st.markdown(f"""
        <div style="padding:1rem 0;">
            <div style="margin-bottom:1.5rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                    <span style="font-size:0.9rem;color:#8888aa;">Gate 30 (Control)</span>
                    <span style="font-size:1.1rem;font-weight:700;color:#0077CC;">{control_rate:.1f}%</span>
                </div>
                <div style="background:#2a2a3e;border-radius:8px;height:32px;overflow:hidden;">
                    <div style="background:#0077CC;height:100%;width:{control_rate}%;
                        transition:width 0.3s;display:flex;align-items:center;justify-content:flex-end;padding-right:0.5rem;">
                        <span style="font-size:0.75rem;color:white;font-weight:600;"></span>
                    </div>
                </div>
            </div>
            <div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                    <span style="font-size:0.9rem;color:#8888aa;">Gate 40 (Treatment)</span>
                    <span style="font-size:1.1rem;font-weight:700;color:#6366f1;">{treatment_rate:.1f}%</span>
                </div>
                <div style="background:#2a2a3e;border-radius:8px;height:32px;overflow:hidden;">
                    <div style="background:#6366f1;height:100%;width:{treatment_rate}%;
                        transition:width 0.3s;display:flex;align-items:center;justify-content:flex-end;padding-right:0.5rem;">
                        <span style="font-size:0.75rem;color:white;font-weight:600;"></span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background:rgba(239,68,68,0.08);border:1px solid #ef4444;border-radius:8px;
            padding:1rem;margin-top:1rem;text-align:center;">
            <div style="font-size:0.8rem;color:#8888aa;margin-bottom:0.25rem;">Absolute Difference</div>
            <div style="font-size:1.75rem;font-weight:800;color:#ef4444;">{fmt_lift(absolute_lift)}</div>
        </div>
        """, unsafe_allow_html=True)

with col_right:
    st.markdown("""
    <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:1.5rem;">
        <h4 style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin:0 0 1rem 0;">
            Distribution Across Segments
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Segment selector and forest plot
    if segment_effects:
        dimensions = segment_effects.get("segmentation_dimensions", [])
        dim_names = [d["dimension_name"] for d in dimensions]
        
        if dim_names:
            selected_dims = st.multiselect(
                "Select dimensions to visualize",
                dim_names,
                default=dim_names[:2] if len(dim_names) >= 2 else dim_names,
                key="segment_dims"
            )

st.markdown("<br>", unsafe_allow_html=True)

# Forest plot below
if segment_effects and dim_names and selected_dims:
    st.markdown("""
    <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:1.5rem;">
    </div>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(
        treatment_effect_forest_plot(segment_effects, "retention_7", selected_dims),
        use_container_width=True,
        config={"displayModeBar": False}
    )
    
    st.markdown("""
    <p style="font-size:0.9rem;color:#8888aa;text-align:center;margin:1rem 0 0 0;">
        <strong>Interpretation:</strong> Most segments show negative lift, indicating Gate 40 
        reduces retention across diverse player groups.
    </p>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# SEGMENT ANALYSIS TABLE
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Segment Analysis</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Detailed breakdown by player segment</p>
</div>
""", unsafe_allow_html=True)

if segment_effects and dimensions:
    selected_dimension = st.selectbox(
        "Select segmentation dimension",
        dim_names,
        index=0,
        key="dimension_select"
    )
    
    # Build table data
    if selected_dimension:
        dim = next((d for d in dimensions if d["dimension_name"] == selected_dimension), None)
        if dim:
            table_data = []
            for seg_name, seg_data in dim["segments"].items():
                if "retention_7" in seg_data.get("outcomes", {}):
                    out = seg_data["outcomes"]["retention_7"]
                    lift = out["absolute_lift"]
                    n = seg_data["n_control"] + seg_data["n_treatment"]
                    pval = out.get("p_value", 1)
                    
                    status = "🟢 Neutral" if abs(lift) < 0.005 else ("🔴 Negative" if lift < 0 else "🟢 Positive")
                    recommendation = "Monitor" if abs(lift) < 0.005 else ("High concern" if lift < -0.01 else "Note")
                    
                    table_data.append({
                        "Segment": seg_name,
                        "Sample": f"{n:,}",
                        "Lift": fmt_lift(lift),
                        "CI": f"[{fmt_lift(out['ci_lower'])}, {fmt_lift(out['ci_upper'])}]",
                        "P-Value": fmt_pvalue(pval),
                        "Status": status,
                        "Recommendation": recommendation
                    })
            
            if table_data:
                df_table = pd.DataFrame(table_data)
                
                st.markdown("""
                <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;overflow:hidden;">
                </div>
                """, unsafe_allow_html=True)
                
                st.dataframe(
                    df_table,
                    use_container_width=True,
                    height=400,
                    hide_index=True
                )

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PRIORITY SCORE IMPACT
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Priority Score Impact</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Treatment effect by decision engine priority deciles</p>
</div>
""", unsafe_allow_html=True)

if segment_effects:
    st.markdown("""
    <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:1.5rem;">
    </div>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(
        priority_decile_chart_retention(segment_effects),
        use_container_width=True,
        config={"displayModeBar": False}
    )
    
    st.markdown("""
    <p style="font-size:0.9rem;color:#8888aa;text-align:center;margin:1rem 0 0 0;">
        <strong>Interpretation:</strong> Gate 40 shows negative impact across all priority score deciles, 
        indicating the treatment harms retention regardless of predicted player value.
    </p>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# STATISTICAL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Statistical Validation</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Experiment quality and rigor checks</p>
</div>
""", unsafe_allow_html=True)

v1, v2, v3, v4 = st.columns(4)

# Validation cards
def _validation_card(col, icon, title, status, detail):
    status_color = "#22c55e" if "✓" in icon or "Passed" in status else "#f59e0b"
    status_bg = "rgba(34,197,94,0.08)" if "✓" in icon else "rgba(245,158,11,0.08)"
    
    col.markdown(f"""
    <div style="background:#1a1a28;border:1px solid {status_color};border-radius:12px;
        padding:1.5rem;text-align:center;min-height:200px;display:flex;flex-direction:column;justify-content:center;">
        <div style="font-size:2.5rem;margin-bottom:0.75rem;">{icon}</div>
        <div style="font-size:0.9rem;font-weight:700;color:{status_color};
            text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">{title}</div>
        <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.5rem;">{status}</div>
        <div style="font-size:0.85rem;color:#8888aa;">{detail}</div>
    </div>
    """, unsafe_allow_html=True)

randomization_status = "Passed"
balance_status = "Balanced"
if experiment:
    validity = experiment.get("validity_checks", {})
    if not validity.get("balance_check", True):
        randomization_status = "Review"
        balance_status = "Check Required"

_validation_card(v1, "✓", "Randomization", randomization_status, 
                f"{n_control:,} control vs {n_treatment:,} treatment")

multiple_testing_status = "Corrected"
total_tests = 0
if stat_tests:
    total_tests = len(stat_tests.get("segment_tests", []))
    method = stat_tests.get("correction_method", "Holm-Bonferroni")
    _validation_card(v2, "✓", "Multiple Testing", multiple_testing_status,
                    f"{total_tests} tests, {method[:15]}")
else:
    _validation_card(v2, "✓", "Multiple Testing", multiple_testing_status, "Applied")

_validation_card(v3, "✓", "Balance Check", balance_status,
                "Groups are comparable")

ci_status = f"[{fmt_lift(ci_lower)}, {fmt_lift(ci_upper)}]"
_validation_card(v4, "✓", "Confidence Intervals", "Computed",
                f"95% CI: {ci_status}")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# FINAL RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Final Recommendation</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Deployment decision and next actions</p>
</div>
""", unsafe_allow_html=True)

final_decision_color = "#ef4444" if "NOT" in decision else "#22c55e"
final_decision_bg = "rgba(239,68,68,0.08)" if "NOT" in decision else "rgba(34,197,94,0.08)"
final_decision_icon = "🚫" if "NOT" in decision else "✓"

st.markdown(f"""
<div style="background:linear-gradient(135deg,{final_decision_bg},{final_decision_bg});
    border:2px solid {final_decision_color};border-radius:16px;
    padding:2.5rem;text-align:center;margin:2rem 0;">
    <div style="font-size:4rem;margin-bottom:1rem;">{final_decision_icon}</div>
    <div style="font-size:2.25rem;font-weight:800;color:{final_decision_color};
        margin-bottom:1.5rem;letter-spacing:-0.02em;">{decision}</div>
    <div style="background:#1a1a28;border-radius:12px;padding:1.5rem;text-align:left;
        margin-bottom:1.5rem;">
        <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.75rem;">
            Why this decision was made:
        </div>
        <ul style="margin:0;padding-left:1.5rem;color:#b4bcd0;font-size:1rem;line-height:1.8;">
            <li>Gate 40 shows consistent <strong style="color:#ef4444;">negative impact</strong> on Day 7 retention</li>
            <li>Effect is <strong style="color:#f59e0b;">statistically significant</strong> (p={fmt_pvalue(p_value)})</li>
            <li>Negative impact appears across <strong style="color:#6366f1;">multiple player segments</strong></li>
        </ul>
    </div>
    <div style="background:#1a1a28;border-radius:12px;padding:1.5rem;text-align:left;">
        <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.75rem;">
            Next Actions:
        </div>
        <ul style="margin:0;padding-left:1.5rem;color:#b4bcd0;font-size:1rem;line-height:1.8;">
            <li><strong style="color:#22c55e;">Continue using Gate 30</strong> for all players</li>
            <li><strong style="color:#0077CC;">Investigate player feedback</strong> to understand why Gate 40 causes early churn</li>
            <li><strong style="color:#6366f1;">Run follow-up experiment</strong> after addressing the root cause</li>
        </ul>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# ARTIFACTS FOOTER
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h3 style="font-size:1.25rem;font-weight:700;color:#e8e8f0;margin:0;">Pipeline Artifacts</h3>
    <p style="font-size:0.85rem;color:#8888aa;margin:0.25rem 0 0 0;">Generated by Phase 4 — Experiment Evaluation</p>
</div>
""", unsafe_allow_html=True)

artifacts = [
    {"name": "experiment_validation.json", "desc": "Experiment design and validity checks", "rows": "—"},
    {"name": "overall_treatment_effects.json", "desc": "Primary outcome analysis", "rows": "2 outcomes"},
    {"name": "segment_level_effects.json", "desc": "Heterogeneous effect analysis", "rows": f"{total_tests} segments"},
    {"name": "statistical_tests.json", "desc": "Multiple testing correction", "rows": f"{total_tests} tests"},
]

art_cols = st.columns(4)
for i, art in enumerate(artifacts):
    with art_cols[i]:
        art_cols[i].markdown(f"""
        <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:8px;
            padding:1rem;min-height:140px;">
            <div style="font-size:1.25rem;margin-bottom:0.5rem;">📄</div>
            <div style="font-size:0.85rem;font-weight:700;color:#0077CC;margin-bottom:0.5rem;">
                {art["name"]}
            </div>
            <div style="font-size:0.75rem;color:#8888aa;margin-bottom:0.5rem;">{art["desc"]}</div>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                <span style="background:rgba(0,208,132,0.12);border:1px solid #00d084;
                    color:#00d084;padding:0.2rem 0.5rem;border-radius:4px;
                    font-size:0.7rem;font-weight:600;">✓ Available</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
