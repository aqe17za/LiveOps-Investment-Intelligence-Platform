"""Executive Decision Summary

Business impact analysis and deployment recommendation.
Final executive summary combining all pipeline phases.
"""

import streamlit as st
import pandas as pd

from components.sidebar import render_sidebar
from components.plot_components import business_impact_segment_chart
from utils.data_loader import (
    load_liveops_recommendations, load_business_impact, 
    load_overall_treatment_effects, load_manifest
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
        <span class="nav-step completed">Experiment</span>
        <span class="nav-arrow">→</span>
        <span class="nav-step current">Executive</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Load artifacts
recommendations = load_liveops_recommendations()
business_impact = load_business_impact()
overall_effects = load_overall_treatment_effects()
manifest = load_manifest()

if not recommendations:
    st.error("⚠️ Executive recommendation not found. Run Phase 4 first.")
    st.stop()

# Extract key data
decision = recommendations.get("deployment_decision", "UNKNOWN")
confidence = recommendations.get("recommendation_confidence", "Medium")
summary = recommendations.get("summary", "Analysis complete")

# Get metrics
expected_retained = 0
absolute_lift = 0
p_value = 1
total_players = 0

if business_impact:
    overall_impact = business_impact.get("overall_impact", {})
    expected_retained = overall_impact.get("expected_retained_players", 0)

if overall_effects and "retention_7" in overall_effects:
    ret7_data = overall_effects["retention_7"]
    absolute_lift = ret7_data.get("absolute_lift", 0)
    p_value = ret7_data.get("p_value", 1)
    total_players = ret7_data.get("n_control", 0) + ret7_data.get("n_treatment", 0)

version = manifest.get("pipeline_version", "1.0") if manifest else "1.0"
recommended_version = "Gate 30"

# ═══════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ═══════════════════════════════════════════════════════════════════════════

decision_color = "#ef4444" if "NOT" in decision else "#22c55e"
decision_bg = "rgba(239,68,68,0.08)" if "NOT" in decision else "rgba(34,197,94,0.08)"
decision_icon = "🟥" if "NOT" in decision else "🟩"

st.markdown(f"""
<div style="
    background:linear-gradient(135deg,#1a1a28 0%,#0f0f18 100%);
    border:2px solid {decision_color};border-radius:16px;padding:3rem;
    margin-bottom:2rem;position:relative;overflow:hidden;
    box-shadow:0 8px 32px rgba(0,0,0,0.4);">
    <div style="
        position:absolute;top:0;left:0;right:0;bottom:0;
        background:radial-gradient(ellipse at top right,{decision_bg} 0%,transparent 70%);
        pointer-events:none;
    "></div>
    <div style="position:relative;z-index:1;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:3rem;">
            <div style="flex:1;min-width:320px;">
                <div style="font-size:0.85rem;font-weight:700;color:#8888aa;
                    text-transform:uppercase;letter-spacing:0.15em;margin-bottom:0.75rem;">
                    Final Recommendation
                </div>
                <h1 style="font-size:3rem;font-weight:900;color:#e8e8f0;
                    margin:0 0 1.25rem 0;letter-spacing:-0.03em;line-height:1.1;">
                    Executive Decision
                </h1>
                <p style="font-size:1.15rem;color:#b4bcd0;margin:0;line-height:1.7;">
                    Final deployment recommendation based on the complete 
                    <strong style="color:#0077CC;">four-phase experiment evaluation</strong>.
                </p>
            </div>
            <div style="min-width:320px;">
                <div style="background:{decision_bg};border:3px solid {decision_color};
                    border-radius:16px;padding:2rem;text-align:center;
                    box-shadow:0 4px 16px rgba(0,0,0,0.3);">
                    <div style="font-size:3.5rem;margin-bottom:1rem;">{decision_icon}</div>
                    <div style="font-size:1.75rem;font-weight:900;color:{decision_color};
                        margin-bottom:1.5rem;letter-spacing:-0.02em;line-height:1.2;">
                        {decision}
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;text-align:left;">
                        <div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:0.75rem;">
                            <div style="font-size:0.7rem;color:#8888aa;text-transform:uppercase;
                                letter-spacing:0.05em;margin-bottom:0.25rem;">Confidence</div>
                            <div style="font-size:1.2rem;font-weight:800;color:#e8e8f0;">{confidence}</div>
                        </div>
                        <div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:0.75rem;">
                            <div style="font-size:0.7rem;color:#8888aa;text-transform:uppercase;
                                letter-spacing:0.05em;margin-bottom:0.25rem;">Recommended</div>
                            <div style="font-size:1.2rem;font-weight:800;color:#22c55e;">{recommended_version}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-top:2rem;">
            <span style="background:rgba(0,208,132,0.12);border:1px solid #00d084;
                color:#00d084;padding:0.4rem 1rem;border-radius:8px;
                font-size:0.85rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">
                ✓ Analysis Complete
            </span>
            <span style="background:rgba(0,119,204,0.12);border:1px solid #0077CC;
                color:#0077CC;padding:0.4rem 1rem;border-radius:8px;
                font-size:0.85rem;font-weight:600;">
                Pipeline v{version}
            </span>
            <span style="background:rgba(255,255,255,0.04);border:1px solid #3d4357;
                color:#8a92a8;padding:0.4rem 1rem;border-radius:8px;
                font-size:0.85rem;">
                {total_players:,} Players Analyzed
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
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Key metrics and deployment status</p>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

# KPI Card Helper
def _kpi_large(col, icon, label, value, detail, accent_color):
    col.markdown(f"""
    <div style="background:#1a1a28;border:1px solid {accent_color};border-radius:12px;
        padding:1.75rem;text-align:center;transition:transform 0.2s;min-height:200px;
        display:flex;flex-direction:column;justify-content:center;">
        <div style="font-size:3rem;margin-bottom:1rem;">{icon}</div>
        <div style="font-size:0.75rem;color:#8888aa;text-transform:uppercase;
            letter-spacing:0.05em;margin-bottom:0.5rem;">{label}</div>
        <div style="font-size:2rem;font-weight:800;color:{accent_color};
            margin-bottom:0.5rem;letter-spacing:-0.02em;">{value}</div>
        <div style="font-size:0.9rem;color:#b4bcd0;">{detail}</div>
    </div>
    """, unsafe_allow_html=True)

_kpi_large(k1, decision_icon, "Deployment Decision", 
          "DO NOT DEPLOY" if "NOT" in decision else decision,
          "Final Recommendation", decision_color)

_kpi_large(k2, "📉", "Retention Impact", fmt_lift(absolute_lift),
          f"p={fmt_pvalue(p_value)}", "#ef4444")

_kpi_large(k3, "🎯", "Confidence", confidence,
          "Statistical Certainty", "#6366f1")

experiment_status = "✓ Completed"
_kpi_large(k4, "🔬", "Experiment Status", experiment_status,
          f"{total_players:,} players", "#22c55e")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS EXPLANATION
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;
    padding:2.5rem;margin:2rem 0;">
    <h3 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0 0 1.5rem 0;">
        Why are we recommending Gate 30?
    </h3>
    <p style="font-size:1.1rem;color:#b4bcd0;line-height:1.9;margin:0 0 1.25rem 0;">
        Players exposed to <strong style="color:#6366f1;">Gate 40</strong> consistently 
        <strong style="color:#ef4444;">returned less often</strong> after seven days compared 
        to players who experienced <strong style="color:#0077CC;">Gate 30</strong>.
    </p>
    <p style="font-size:1.1rem;color:#b4bcd0;line-height:1.9;margin:0 0 1.25rem 0;">
        Although the difference is not huge, it was measured across a 
        <strong style="color:#22c55e;">randomized controlled experiment</strong> and was 
        <strong style="color:#f59e0b;">consistent enough</strong> that deploying Gate 40 
        would likely reduce long-term player retention.
    </p>
    <p style="font-size:1.1rem;color:#b4bcd0;line-height:1.9;margin:0 0 1.25rem 0;">
        Continuing with <strong style="color:#22c55e;">Gate 30</strong> is therefore the 
        <strong style="color:#22c55e;">safer business decision</strong> that preserves 
        our current player engagement levels.
    </p>
    <div style="background:rgba(0,119,204,0.08);border-left:4px solid #0077CC;
        border-radius:8px;padding:1.5rem;margin-top:1.5rem;">
        <div style="font-size:1rem;font-weight:700;color:#0077CC;margin-bottom:0.5rem;">
            Bottom Line
        </div>
        <div style="font-size:1.05rem;color:#e8e8f0;line-height:1.7;">
            Making the game harder at Level 40 causes more players to stop playing. 
            Keep the current Level 30 gate to maintain retention.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS IMPACT
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Business Impact</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Quantified effects and decision rationale</p>
</div>
""", unsafe_allow_html=True)

col_impact, col_rationale = st.columns([1, 1])

with col_impact:
    st.markdown("""
    <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:1.5rem;">
        <h4 style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin:0 0 1rem 0;">
            Expected Business Impact
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Impact metrics in cards
    def _impact_metric(icon, label, value, color):
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.02);border:1px solid #2a2a3e;
            border-radius:8px;padding:1rem;margin:0.75rem 0;">
            <div style="display:flex;align-items:center;gap:1rem;">
                <div style="font-size:2rem;">{icon}</div>
                <div style="flex:1;">
                    <div style="font-size:0.85rem;color:#8888aa;margin-bottom:0.25rem;">{label}</div>
                    <div style="font-size:1.5rem;font-weight:800;color:{color};">{value}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    _impact_metric("📉", "Expected Retained Players", f"{expected_retained:+,.0f}", "#ef4444")
    _impact_metric("📊", "Retention Difference", fmt_lift(absolute_lift), "#f59e0b")
    _impact_metric("👥", "Affected Users", fmt_number(total_players), "#6366f1")
    _impact_metric("💰", "Estimated Impact", "Negative" if expected_retained < 0 else "Positive", 
                  "#ef4444" if expected_retained < 0 else "#22c55e")

with col_rationale:
    st.markdown("""
    <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:1.5rem;">
        <h4 style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin:0 0 1rem 0;">
            Decision Rationale
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Rationale points
    rationale = recommendations.get("rationale", [])
    for i, point in enumerate(rationale[:6], 1):
        icon = "✓" if "positive" in point.lower() or "good" in point.lower() else "●"
        color = "#22c55e" if icon == "✓" else "#b4bcd0"
        st.markdown(f"""
        <div style="display:flex;gap:0.75rem;margin:0.75rem 0;padding:0.75rem;
            background:rgba(255,255,255,0.02);border-radius:6px;">
            <div style="color:{color};font-weight:700;font-size:1rem;flex-shrink:0;">{icon}</div>
            <div style="color:#b4bcd0;font-size:0.95rem;line-height:1.6;">{point}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# SEGMENT IMPACT
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Segment Impact Analysis</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Expected retained players by segment</p>
</div>
""", unsafe_allow_html=True)

if business_impact and "segment_impact" in business_impact:
    segment_impacts = business_impact["segment_impact"]
    
    # Segmentation selector
    dimensions_available = list(set([s["dimension"] for s in segment_impacts]))
    selected_seg_dim = st.selectbox(
        "Select segmentation dimension",
        dimensions_available,
        index=0,
        key="seg_dimension"
    )
    
    st.markdown("""
    <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:1.5rem;">
    </div>
    """, unsafe_allow_html=True)
    
    # Chart
    st.plotly_chart(
        business_impact_segment_chart(business_impact),
        use_container_width=True,
        config={"displayModeBar": False}
    )
    
    st.markdown(f"""
    <p style="font-size:0.95rem;color:#b4bcd0;text-align:center;margin:1rem 0 0 0;line-height:1.7;">
        <strong>Interpretation:</strong> Most segments show negative expected impact, 
        meaning Gate 40 would reduce retained players across diverse player groups. 
        This reinforces the decision to keep Gate 30.
    </p>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# IMPACT TABLE
# ═══════════════════════════════════════════════════════════════════════════

if business_impact and "segment_impact" in business_impact:
    st.markdown("""
    <div style="margin:2rem 0 0.5rem 0;">
        <h3 style="font-size:1.5rem;font-weight:700;color:#e8e8f0;margin:0;">Detailed Segment Impact</h3>
        <p style="font-size:0.9rem;color:#8888aa;margin:0.25rem 0 0 0;">Top segments ranked by impact magnitude</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sort by absolute impact
    sorted_segments = sorted(segment_impacts, 
                           key=lambda x: abs(x.get("expected_retained_players", 0)), 
                           reverse=True)
    top_segments = sorted_segments[:15]
    
    table_data = []
    for seg in top_segments:
        retained = seg.get("expected_retained_players", 0)
        effect = seg.get("treatment_effect", 0)
        priority = seg.get("priority_score", 0)
        
        status = "🔴 Negative" if retained < -5 else ("🟡 Minor" if retained < 0 else "🟢 Positive")
        recommendation = "High Concern" if retained < -10 else ("Monitor" if retained < 0 else "Low Priority")
        
        table_data.append({
            "Segment": f"{seg['dimension'][:12]} | {seg['segment'][:18]}",
            "Expected Retained": f"{retained:+.1f}",
            "Treatment Effect": fmt_lift(effect) if isinstance(effect, (int, float)) else str(effect),
            "Priority": f"{priority:.3f}",
            "Recommendation": recommendation,
            "Status": status
        })
    
    df_table = pd.DataFrame(table_data)
    
    st.markdown("""
    <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;overflow:hidden;">
    </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(
        df_table,
        use_container_width=True,
        height=450,
        hide_index=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# FINAL RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Recommended Next Action</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Implementation guidance and immediate steps</p>
</div>
""", unsafe_allow_html=True)

if decision == "DO NOT DEPLOY":
    action_color = "#22c55e"
    action_bg = "rgba(34,197,94,0.08)"
    action_icon = "✅"
    action_title = "Continue Gate 30"
    
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{action_bg},{action_bg});
        border:2px solid {action_color};border-radius:16px;
        padding:2.5rem;margin:2rem 0;text-align:center;">
        <div style="font-size:4rem;margin-bottom:1rem;">{action_icon}</div>
        <div style="font-size:2rem;font-weight:800;color:{action_color};
            margin-bottom:1.5rem;letter-spacing:-0.02em;">{action_title}</div>
        <div style="background:#1a1a28;border-radius:12px;padding:2rem;text-align:left;">
            <div style="font-size:1.15rem;font-weight:700;color:#e8e8f0;margin-bottom:1rem;">
                Immediate Actions
            </div>
            <ul style="margin:0;padding-left:2rem;color:#b4bcd0;font-size:1.05rem;line-height:2;">
                <li><strong style="color:{action_color};">Keep Gate 30 in production</strong> — Maintain current configuration</li>
                <li><strong style="color:#0077CC;">Do not deploy Gate 40</strong> — Evidence shows negative retention impact</li>
                <li><strong style="color:#6366f1;">Design a new experiment</strong> before changing progression gates</li>
                <li><strong style="color:#f59e0b;">Monitor D7 retention weekly</strong> — Ensure stability</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif decision == "DEPLOY GLOBALLY":
    action_color = "#22c55e"
    action_bg = "rgba(34,197,94,0.08)"
    action_icon = "✅"
    action_title = "Deploy Gate 40 Globally"
    
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{action_bg},{action_bg});
        border:2px solid {action_color};border-radius:16px;
        padding:2.5rem;margin:2rem 0;text-align:center;">
        <div style="font-size:4rem;margin-bottom:1rem;">{action_icon}</div>
        <div style="font-size:2rem;font-weight:800;color:{action_color};
            margin-bottom:1.5rem;letter-spacing:-0.02em;">{action_title}</div>
        <div style="background:#1a1a28;border-radius:12px;padding:2rem;text-align:left;">
            <div style="font-size:1.15rem;font-weight:700;color:#e8e8f0;margin-bottom:1rem;">
                Immediate Actions
            </div>
            <ul style="margin:0;padding-left:2rem;color:#b4bcd0;font-size:1.05rem;line-height:2;">
                <li><strong style="color:{action_color};">Deploy to all new players</strong> — Full rollout recommended</li>
                <li><strong style="color:#0077CC;">Monitor KPIs daily</strong> — Track retention and session metrics</li>
                <li><strong style="color:#6366f1;">Prepare rollback plan</strong> — Have ability to revert if needed</li>
                <li><strong style="color:#f59e0b;">Communicate to stakeholders</strong> — Share expected impact</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

else:  # TARGETED DEPLOYMENT
    action_color = "#f59e0b"
    action_bg = "rgba(245,158,11,0.08)"
    action_icon = "🎯"
    action_title = "Targeted Deployment"
    
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{action_bg},{action_bg});
        border:2px solid {action_color};border-radius:16px;
        padding:2.5rem;margin:2rem 0;text-align:center;">
        <div style="font-size:4rem;margin-bottom:1rem;">{action_icon}</div>
        <div style="font-size:2rem;font-weight:800;color:{action_color};
            margin-bottom:1.5rem;letter-spacing:-0.02em;">{action_title}</div>
        <div style="background:#1a1a28;border-radius:12px;padding:2rem;text-align:left;">
            <div style="font-size:1.15rem;font-weight:700;color:#e8e8f0;margin-bottom:1rem;">
                Immediate Actions
            </div>
            <ul style="margin:0;padding-left:2rem;color:#b4bcd0;font-size:1.05rem;line-height:2;">
                <li><strong style="color:{action_color};">Deploy to high-performing segments only</strong></li>
                <li><strong style="color:#0077CC;">Monitor segment-specific metrics</strong></li>
                <li><strong style="color:#6366f1;">Collect additional data</strong> — Expand sample size</li>
                <li><strong style="color:#22c55e;">Gradual expansion</strong> — Roll out to more segments if successful</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# NEXT STEPS ROADMAP
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h3 style="font-size:1.5rem;font-weight:700;color:#e8e8f0;margin:0;">Next Steps Roadmap</h3>
    <p style="font-size:0.9rem;color:#8888aa;margin:0.25rem 0 0 0;">Timeline for implementation and follow-up</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:2rem;margin:1rem 0;">
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1.5rem;">
        <div style="text-align:center;">
            <div style="background:rgba(0,119,204,0.12);border:2px solid #0077CC;
                border-radius:50%;width:60px;height:60px;margin:0 auto 1rem auto;
                display:flex;align-items:center;justify-content:center;
                font-size:1.5rem;font-weight:800;color:#0077CC;">1</div>
            <div style="font-size:0.75rem;color:#8888aa;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.5rem;">Week 1</div>
            <div style="font-size:1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.5rem;">
                Continue Monitoring
            </div>
            <div style="font-size:0.85rem;color:#8888aa;line-height:1.5;">
                Track D7 retention and player feedback
            </div>
        </div>
        <div style="text-align:center;">
            <div style="background:rgba(99,102,241,0.12);border:2px solid #6366f1;
                border-radius:50%;width:60px;height:60px;margin:0 auto 1rem auto;
                display:flex;align-items:center;justify-content:center;
                font-size:1.5rem;font-weight:800;color:#6366f1;">2</div>
            <div style="font-size:0.75rem;color:#8888aa;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.5rem;">Week 2</div>
            <div style="font-size:1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.5rem;">
                Review Metrics
            </div>
            <div style="font-size:0.85rem;color:#8888aa;line-height:1.5;">
                Analyze retention trends and stability
            </div>
        </div>
        <div style="text-align:center;">
            <div style="background:rgba(245,158,11,0.12);border:2px solid #f59e0b;
                border-radius:50%;width:60px;height:60px;margin:0 auto 1rem auto;
                display:flex;align-items:center;justify-content:center;
                font-size:1.5rem;font-weight:800;color:#f59e0b;">3</div>
            <div style="font-size:0.75rem;color:#8888aa;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.5rem;">Week 3</div>
            <div style="font-size:1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.5rem;">
                Design Follow-Up
            </div>
            <div style="font-size:0.85rem;color:#8888aa;line-height:1.5;">
                Plan new experiment with intermediate gates
            </div>
        </div>
        <div style="text-align:center;">
            <div style="background:rgba(34,197,94,0.12);border:2px solid #22c55e;
                border-radius:50%;width:60px;height:60px;margin:0 auto 1rem auto;
                display:flex;align-items:center;justify-content:center;
                font-size:1.5rem;font-weight:800;color:#22c55e;">4</div>
            <div style="font-size:0.75rem;color:#8888aa;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.5rem;">Week 4</div>
            <div style="font-size:1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.5rem;">
                Executive Review
            </div>
            <div style="font-size:0.85rem;color:#8888aa;line-height:1.5;">
                Present findings to leadership
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h3 style="font-size:1.25rem;font-weight:700;color:#e8e8f0;margin:0;">Pipeline Artifacts</h3>
    <p style="font-size:0.85rem;color:#8888aa;margin:0.25rem 0 0 0;">Generated by Executive Decision phase</p>
</div>
""", unsafe_allow_html=True)

artifacts = [
    {"name": "liveops_recommendations.json", "desc": "Final executive recommendation", "icon": "📋"},
    {"name": "business_impact_summary.json", "desc": "Quantified business impact", "icon": "💼"},
    {"name": "overall_treatment_effects.json", "desc": "Statistical results", "icon": "📊"},
    {"name": "manifest.json", "desc": "Pipeline metadata", "icon": "⚙️"},
]

art_cols = st.columns(4)
for i, art in enumerate(artifacts):
    with art_cols[i]:
        art_cols[i].markdown(f"""
        <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:8px;
            padding:1rem;min-height:140px;">
            <div style="font-size:1.5rem;margin-bottom:0.5rem;">{art["icon"]}</div>
            <div style="font-size:0.85rem;font-weight:700;color:#0077CC;margin-bottom:0.5rem;">
                {art["name"]}
            </div>
            <div style="font-size:0.75rem;color:#8888aa;margin-bottom:0.75rem;">{art["desc"]}</div>
            <span style="background:rgba(0,208,132,0.12);border:1px solid #00d084;
                color:#00d084;padding:0.2rem 0.5rem;border-radius:4px;
                font-size:0.7rem;font-weight:600;">✓ Available</span>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div style="background:#12121a;border-top:1px solid #2a2a3e;
    padding:1.5rem;margin-top:3rem;text-align:center;">
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:1rem;max-width:1000px;margin:0 auto;">
        <div>
            <div style="font-size:0.7rem;color:#555570;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.25rem;">Pipeline Version</div>
            <div style="font-size:0.9rem;font-weight:600;color:#8888aa;">{version}</div>
        </div>
        <div>
            <div style="font-size:0.7rem;color:#555570;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.25rem;">Decision Generated</div>
            <div style="font-size:0.9rem;font-weight:600;color:#8888aa;">Phase 4</div>
        </div>
        <div>
            <div style="font-size:0.7rem;color:#555570;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.25rem;">Experiment</div>
            <div style="font-size:0.9rem;font-weight:600;color:#8888aa;">Cookie Cats</div>
        </div>
        <div>
            <div style="font-size:0.7rem;color:#555570;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.25rem;">Source Dataset</div>
            <div style="font-size:0.9rem;font-weight:600;color:#8888aa;">A/B Test</div>
        </div>
        <div>
            <div style="font-size:0.7rem;color:#555570;text-transform:uppercase;
                letter-spacing:0.05em;margin-bottom:0.25rem;">Analytics Version</div>
            <div style="font-size:0.9rem;font-weight:600;color:#8888aa;">v{version}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
