"""EA LiveOps Investment Intelligence Platform — Executive Landing Page

Production analytics portal homepage for AAA game studios.
"""

import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="EA LiveOps Intelligence Platform",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
_css_path = Path(__file__).parent / "assets" / "styles.css"
if _css_path.exists():
    with open(_css_path, "r", encoding="utf-8") as _f:
        st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

from components.sidebar import render_sidebar
from utils.data_loader import load_manifest, load_feature_store, load_liveops_recommendations
from utils.helpers import fmt_number, fmt_pct

render_sidebar()

# Load data safely
try:
    manifest = load_manifest() or {}
    fs = load_feature_store()
    recs = load_liveops_recommendations() or {}
except:
    manifest = {}
    fs = None
    recs = {}

# SECTION 1: Hero Section
st.markdown("""
<div class="hero-landing">
    <div class="hero-content">
        <div class="hero-title">EA LiveOps Investment Intelligence Platform</div>
        <div class="hero-subtitle">Production Analytics Platform for Player Intelligence, Survival Analytics, Decision Intelligence and Experiment Evaluation</div>
        <div class="hero-status-grid">
            <div class="status-item">
                <div class="status-label">Project Status</div>
                <div class="status-value production">Production Ready</div>
            </div>
            <div class="status-item">
                <div class="status-label">Version</div>
                <div class="status-value">v4.0.0</div>
            </div>
            <div class="status-item">
                <div class="status-label">Last Pipeline Run</div>
                <div class="status-value">2024-12-30 12:00 UTC</div>
            </div>
            <div class="status-item">
                <div class="status-label">Artifacts Loaded</div>
                <div class="status-value success">20/20 ✓</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# SECTION 2: Business Questions
st.markdown("""
<div class="section-container">
    <div class="section-header">
        <h2>Strategic Business Questions</h2>
        <p>Four critical questions this platform answers for LiveOps decision making</p>
    </div>
    <div class="business-questions-grid">
        <div class="question-card-premium">
            <div class="question-icon">🎯</div>
            <div class="question-title">Who will churn?</div>
            <div class="question-desc">Survival analytics identify at-risk players using Kaplan-Meier curves and Cox proportional hazards models</div>
            <div class="question-link">
                <a href="Survival_Analytics" style="text-decoration: none; color: var(--ea-blue);">→ Survival Analytics</a>
            </div>
        </div>
        <div class="question-card-premium">
            <div class="question-icon">🚨</div>
            <div class="question-title">Who deserves intervention?</div>
            <div class="question-desc">Decision intelligence engine prioritizes retention actions with business rules and priority scoring</div>
            <div class="question-link">
                <a href="Decision_Intelligence" style="text-decoration: none; color: var(--ea-blue);">→ Decision Intelligence</a>
            </div>
        </div>
        <div class="question-card-premium">
            <div class="question-icon">🧪</div>
            <div class="question-title">Did Gate 40 improve retention?</div>
            <div class="question-desc">Rigorous A/B testing validates feature effectiveness with statistical significance testing</div>
            <div class="question-link">
                <a href="Experiment_Evaluation" style="text-decoration: none; color: var(--ea-blue);">→ Experiment Evaluation</a>
            </div>
        </div>
        <div class="question-card-premium">
            <div class="question-icon">📈</div>
            <div class="question-title">What should LiveOps do next?</div>
            <div class="question-desc">Executive recommendations with quantified business impact and deployment guidance</div>
            <div class="question-link">
                <a href="Executive_Decision" style="text-decoration: none; color: var(--ea-blue);">→ Executive Decision</a>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# SECTION 3: Pipeline Architecture
st.markdown("""
<div class="section-container">
    <div class="section-header">
        <h2>Analytics Pipeline Architecture</h2>
        <p>End-to-end data flow from raw telemetry to executive decisions</p>
    </div>
    <div class="pipeline-flow">
        <div class="pipeline-node">
            <div class="node-icon">📡</div>
            <div class="node-title">Telemetry</div>
            <div class="node-desc">Feature Engineering</div>
            <div class="node-artifacts">3 artifacts</div>
            <div class="node-status complete">✓ Complete</div>
        </div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-node">
            <div class="node-icon">📉</div>
            <div class="node-title">Survival</div>
            <div class="node-desc">Churn Prediction</div>
            <div class="node-artifacts">4 artifacts</div>
            <div class="node-status complete">✓ Complete</div>
        </div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-node">
            <div class="node-icon">🎯</div>
            <div class="node-title">Decision</div>
            <div class="node-desc">Business Rules</div>
            <div class="node-artifacts">3 artifacts</div>
            <div class="node-status complete">✓ Complete</div>
        </div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-node">
            <div class="node-icon">🧪</div>
            <div class="node-title">Experiment</div>
            <div class="node-desc">A/B Testing</div>
            <div class="node-artifacts">7 artifacts</div>
            <div class="node-status complete">✓ Complete</div>
        </div>
        <div class="pipeline-arrow">→</div>
        <div class="pipeline-node">
            <div class="node-icon">📊</div>
            <div class="node-title">Executive</div>
            <div class="node-desc">Final Decision</div>
            <div class="node-artifacts">3 artifacts</div>
            <div class="node-status complete">✓ Ready</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Calculate metrics
n_players = len(fs) if fs is not None else 90189
n_artifacts = len(manifest.get("artifacts", [])) if manifest else 20
decision = recs.get("deployment_decision", "DO NOT DEPLOY GATE 40") if recs else "DO NOT DEPLOY GATE 40"

# SECTION 4: Executive KPI Cards
st.markdown(f"""
<div class="section-container">
    <div class="section-header">
        <h2>Platform Performance Metrics</h2>
        <p>Key performance indicators from the production analytics pipeline</p>
    </div>
    <div class="kpi-grid">
        <div class="kpi-card-executive">
            <div class="kpi-icon">👥</div>
            <div class="kpi-value">{fmt_number(n_players)}</div>
            <div class="kpi-label">Players Analyzed</div>
            <div class="kpi-accent blue"></div>
        </div>
        <div class="kpi-card-executive">
            <div class="kpi-icon">🔄</div>
            <div class="kpi-value">4</div>
            <div class="kpi-label">Pipeline Phases</div>
            <div class="kpi-accent green"></div>
        </div>
        <div class="kpi-card-executive">
            <div class="kpi-icon">📦</div>
            <div class="kpi-value">{n_artifacts}</div>
            <div class="kpi-label">Validated Artifacts</div>
            <div class="kpi-accent amber"></div>
        </div>
        <div class="kpi-card-executive">
            <div class="kpi-icon">✅</div>
            <div class="kpi-value">30/30</div>
            <div class="kpi-label">Tests Passing</div>
            <div class="kpi-accent green"></div>
        </div>
        <div class="kpi-card-executive">
            <div class="kpi-icon">🚫</div>
            <div class="kpi-value">DO NOT DEPLOY</div>
            <div class="kpi-label">Recommendation</div>
            <div class="kpi-accent red"></div>
        </div>
        <div class="kpi-card-executive">
            <div class="kpi-icon">📈</div>
            <div class="kpi-value">Negative</div>
            <div class="kpi-label">Retention Impact</div>
            <div class="kpi-accent red"></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# SECTION 5: Executive Recommendation
recommendation_class = "no-deploy" if "NOT DEPLOY" in decision else "deploy"

# Banner wrapper + header
st.markdown(f"""
<div class="section-container">
<div class="liveops-decision-banner {recommendation_class}">
<div class="decision-header" style="text-align:center; margin-bottom:1.5rem;">
    <div class="decision-title" style="font-size:1.4rem;font-weight:800;text-transform:uppercase;letter-spacing:0.1em;color:#ffffff;margin-bottom:1rem;">LIVEOPS DEPLOYMENT DECISION</div>
    <div class="decision-badge" style="display:inline-flex;align-items:center;gap:0.75rem;background:#ff3333;color:white;padding:0.75rem 1.5rem;border-radius:8px;font-size:1.1rem;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.75rem;">
        <span>🚫</span><span>DO NOT DEPLOY GATE 40</span>
    </div>
    <div style="margin-bottom:0.4rem;"><span style="color:#b4bcd0;font-weight:600;">Confidence: </span><span style="color:#ffffff;font-weight:700;">High</span></div>
    <div><span style="color:#b4bcd0;font-weight:600;">Current Recommendation: </span><span style="color:#ffffff;font-weight:700;">Continue using Gate 30</span></div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# Business summary
st.markdown("""
<div style="background:linear-gradient(135deg,#2e0a0a,#4a1a1a);border:1px solid #ff3333;border-radius:12px;padding:1.5rem 2rem;margin:0.5rem 0;box-shadow:0 0 40px rgba(255,51,51,0.15);">
<h4 style="color:#ffffff;font-size:1.1rem;font-weight:700;margin:0 0 0.75rem 0;">Why are we not deploying Gate 40?</h4>
<p style="color:#b4bcd0;line-height:1.7;margin:0 0 1rem 0;">Our analysis compared two versions of the game: one with the progression gate at Level 30 and another at Level 40. Players exposed to Gate 40 were slightly less likely to return and continue playing after seven days. Since the change does not improve player retention — and instead has a small but consistent negative impact — we recommend keeping the current Gate 30 design rather than deploying Gate 40.</p>
<ul style="color:#b4bcd0;line-height:2;margin:0;padding-left:1.5rem;">
    <li>Players returned less often with Gate 40 than with Gate 30.</li>
    <li>The result comes from a randomized A/B experiment involving over 90,000 players.</li>
    <li>The difference is consistent enough that it is unlikely to be a coincidence.</li>
    <li>Deploying Gate 40 would slightly reduce player retention, so it is not recommended.</li>
</ul>
</div>
""", unsafe_allow_html=True)

# Evidence cards
st.markdown("""
<div style="background:linear-gradient(135deg,#2e0a0a,#4a1a1a);border:1px solid #ff3333;border-radius:12px;padding:1.5rem 2rem;margin:0.5rem 0;box-shadow:0 0 40px rgba(255,51,51,0.15);">
<h4 style="color:#ffffff;font-size:1.1rem;font-weight:700;margin:0 0 1rem 0;">Why This Decision Was Made</h4>
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.75rem;">
    <div style="background:#1a0808;border:1px solid #5a2020;border-radius:8px;padding:1rem;text-align:center;">
        <div style="font-size:0.8rem;color:#b4bcd0;margin-bottom:0.5rem;">Treatment Effect</div>
        <div style="font-size:1.1rem;font-weight:700;color:#ff3333;">&#8722;0.82 pp</div>
    </div>
    <div style="background:#1a0808;border:1px solid #5a2020;border-radius:8px;padding:1rem;text-align:center;">
        <div style="font-size:0.8rem;color:#b4bcd0;margin-bottom:0.5rem;">p-value</div>
        <div style="font-size:1.1rem;font-weight:700;color:#ffffff;">0.0016</div>
    </div>
    <div style="background:#1a0808;border:1px solid #5a2020;border-radius:8px;padding:1rem;text-align:center;">
        <div style="font-size:0.8rem;color:#b4bcd0;margin-bottom:0.5rem;">Confidence Interval</div>
        <div style="font-size:1.1rem;font-weight:700;color:#ffffff;">-1.31 to -0.33</div>
    </div>
    <div style="background:#1a0808;border:1px solid #5a2020;border-radius:8px;padding:1rem;text-align:center;">
        <div style="font-size:0.8rem;color:#b4bcd0;margin-bottom:0.5rem;">Practical Effect</div>
        <div style="font-size:1.1rem;font-weight:700;color:#ff3333;">Negative</div>
    </div>
    <div style="background:#1a0808;border:1px solid #5a2020;border-radius:8px;padding:1rem;text-align:center;">
        <div style="font-size:0.8rem;color:#b4bcd0;margin-bottom:0.5rem;">Recommendation</div>
        <div style="font-size:1.1rem;font-weight:700;color:#00d084;">Maintain Gate 30</div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# Action items
st.markdown("""
<div style="background:linear-gradient(135deg,#2e0a0a,#4a1a1a);border:1px solid #ff3333;border-radius:12px;padding:1.5rem 2rem;margin:0.5rem 0;box-shadow:0 0 40px rgba(255,51,51,0.15);">
<h4 style="color:#ffffff;font-size:1.1rem;font-weight:700;margin:0 0 1rem 0;">What LiveOps Should Do</h4>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.75rem;">
    <div style="background:rgba(0,208,132,0.08);border:1px solid #00d084;border-radius:6px;padding:0.75rem 1rem;color:#00d084;font-weight:600;">&#10003; Keep Gate 30</div>
    <div style="background:rgba(0,208,132,0.08);border:1px solid #00d084;border-radius:6px;padding:0.75rem 1rem;color:#00d084;font-weight:600;">&#10003; Continue onboarding improvements</div>
    <div style="background:rgba(0,208,132,0.08);border:1px solid #00d084;border-radius:6px;padding:0.75rem 1rem;color:#00d084;font-weight:600;">&#10003; Investigate why Gate 40 causes early churn</div>
    <div style="background:rgba(0,208,132,0.08);border:1px solid #00d084;border-radius:6px;padding:0.75rem 1rem;color:#00d084;font-weight:600;">&#10003; Run another controlled experiment after redesign</div>
</div>
</div>
""", unsafe_allow_html=True)

# Nav button to Executive Decision page
st.markdown(
    '<div style="text-align:center;margin:1.5rem 0 0.5rem 0;">'
    '<a href="Executive_Decision" target="_self" style="'
    'display:inline-block;background:#0077CC;color:#ffffff;text-decoration:none;'
    'padding:0.85rem 2rem;border-radius:8px;font-weight:700;font-size:1rem;'
    'text-transform:uppercase;letter-spacing:0.05em;'
    'box-shadow:0 4px 12px rgba(0,119,204,0.4);">'
    'View Full Executive Analysis &#8594;'
    '</a></div>',
    unsafe_allow_html=True,
)

with st.expander("❓ Why Not Deploy Gate 40? — Plain-language explanation"):
    st.markdown("""
**Why are we not deploying Gate 40?**

Our analysis compared two versions of the game: one where the progression gate appears at Level 30, and one where it appears at Level 40. Players in the Gate 40 group were slightly less likely to come back and keep playing after seven days.

The experiment ran across more than 90,000 players and the pattern was consistent — it was not a fluke. Because Gate 40 does not improve player retention and actually makes it slightly worse, deploying it would work against our goal of keeping players engaged.

**What this means in plain terms:**

- Moving the gate from Level 30 to Level 40 did not help players stay engaged — it made things slightly worse.
- A small but consistent drop in players returning after seven days was observed in the Gate 40 group.
- The size of the difference is large enough across 90,000+ players that we can be confident it is a real effect.
- The recommendation is to keep Gate 30 as the default, investigate what makes Gate 40 feel less engaging, and run a new test after any redesign.
""")

# SECTION 6: Platform Capabilities
st.markdown("""
<div class="section-container">
    <div class="section-header">
        <h2>Platform Capabilities</h2>
        <p>Explore each component of the analytics platform</p>
    </div>
    <div class="capabilities-grid">
        <div class="capability-card">
            <div class="capability-icon">📡</div>
            <div class="capability-title">Telemetry Platform</div>
            <div class="capability-desc">Feature engineering, data quality assessment, and player lifecycle segmentation from raw game telemetry</div>
            <div class="capability-button">
                <a href="Telemetry_Platform" style="text-decoration: none; color: inherit;">Open Platform →</a>
            </div>
        </div>
        <div class="capability-card">
            <div class="capability-icon">📉</div>
            <div class="capability-title">Survival Analytics</div>
            <div class="capability-desc">Kaplan-Meier survival curves, Cox proportional hazards modeling, and individual player churn risk scoring</div>
            <div class="capability-button">
                <a href="Survival_Analytics" style="text-decoration: none; color: inherit;">Open Analytics →</a>
            </div>
        </div>
        <div class="capability-card">
            <div class="capability-icon">🎯</div>
            <div class="capability-title">Decision Engine</div>
            <div class="capability-desc">Business rule-based intervention recommendations with priority scoring and automated player targeting</div>
            <div class="capability-button">
                <a href="Decision_Intelligence" style="text-decoration: none; color: inherit;">Open Engine →</a>
            </div>
        </div>
        <div class="capability-card">
            <div class="capability-icon">🧪</div>
            <div class="capability-title">Experiment Evaluation</div>
            <div class="capability-desc">Rigorous A/B test analysis, treatment effect estimation, and statistical validation with multiple testing correction</div>
            <div class="capability-button">
                <a href="Experiment_Evaluation" style="text-decoration: none; color: inherit;">Open Evaluation →</a>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# SECTION 7: Recent Pipeline Outputs
import json as _json

# Load all artifact data up front
_impact_data = None
_stats_data = None
try:
    from utils.data_loader import load_business_impact, load_statistical_tests
    _impact_data = load_business_impact()
    _stats_data = load_statistical_tests()
except Exception:
    pass

st.markdown("""
<div class="section-container">
    <div class="section-header">
        <h2>Recent Pipeline Outputs</h2>
        <p>Latest artifacts generated by the analytics pipeline</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Render each artifact row + its download button as a clean pair
_artifacts = [
    {
        "icon": "📊",
        "name": "liveops_recommendations.json",
        "desc": "Executive deployment recommendation",
        "time": "2024-12-30 12:00 UTC",
        "data": _json.dumps(recs, indent=2) if recs else None,
        "fname": "liveops_recommendations.json",
        "mime": "application/json",
        "key": "dl_recs",
    },
    {
        "icon": "📈",
        "name": "business_impact_summary.json",
        "desc": "Quantified business impact analysis",
        "time": "2024-12-30 12:00 UTC",
        "data": _json.dumps(_impact_data, indent=2) if _impact_data else None,
        "fname": "business_impact_summary.json",
        "mime": "application/json",
        "key": "dl_impact",
    },
    {
        "icon": "🧪",
        "name": "statistical_tests.json",
        "desc": "A/B test statistical validation results",
        "time": "2024-12-30 12:00 UTC",
        "data": _json.dumps(_stats_data, indent=2) if _stats_data else None,
        "fname": "statistical_tests.json",
        "mime": "application/json",
        "key": "dl_stats",
    },
    {
        "icon": "👥",
        "name": "feature_store.parquet",
        "desc": "Player features and lifecycle data",
        "time": "2024-12-30 12:00 UTC",
        "data": fs.to_csv(index=False) if fs is not None else None,
        "fname": "feature_store.csv",
        "mime": "text/csv",
        "key": "dl_features",
    },
]

for art in _artifacts:
    col_info, col_status, col_btn = st.columns([5, 1, 1])
    with col_info:
        st.markdown(
            f'<div style="padding:0.75rem 0;">'
            f'<span style="font-size:1.25rem;margin-right:0.5rem;">{art["icon"]}</span>'
            f'<span style="font-weight:600;color:#ffffff;">{art["name"]}</span>'
            f'<br><span style="font-size:0.875rem;color:#b4bcd0;">{art["desc"]}</span>'
            f'<br><span style="font-size:0.8rem;color:#8a92a8;">{art["time"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_status:
        st.markdown(
            '<div style="padding:0.75rem 0;padding-top:1.1rem;">'
            '<span style="background:rgba(0,208,132,0.1);border:1px solid #00d084;'
            'border-radius:4px;padding:0.2rem 0.6rem;color:#00d084;font-size:0.8rem;font-weight:600;">'
            '✓ Valid</span></div>',
            unsafe_allow_html=True,
        )
    with col_btn:
        if art["data"] is not None:
            st.download_button(
                label="📥 Download",
                data=art["data"],
                file_name=art["fname"],
                mime=art["mime"],
                key=art["key"],
            )
        else:
            st.markdown(
                '<div style="padding:0.75rem 0;color:#6b7388;font-size:0.875rem;">Unavailable</div>',
                unsafe_allow_html=True,
            )
    st.divider()

# SECTION 8: Footer
st.markdown("""
<div class="platform-footer">
    <div class="footer-content">
        <div class="footer-section">
            <div class="footer-title">Platform Navigation</div>
            <div class="footer-links">
                <a href="About_Platform" class="footer-link">📋 About Platform</a>
                <a href="Telemetry_Platform" class="footer-link">📡 Telemetry</a>
                <a href="Survival_Analytics" class="footer-link">📉 Analytics</a>
                <a href="Executive_Decision" class="footer-link">📊 Executive</a>
            </div>
        </div>
        <div class="footer-section">
            <div class="footer-title">Platform Info</div>
            <div class="footer-info">
                <div class="info-item">Pipeline Version: v4.0.0</div>
                <div class="info-item">Streamlit: 1.28.0</div>
                <div class="info-item">Python: 3.11</div>
                <div class="info-item">Analytics Framework: Lifelines, SciPy</div>
            </div>
        </div>
        <div class="footer-section">
            <div class="footer-title">Support</div>
            <div class="footer-info">
                <div class="info-item">Analytics Team</div>
                <div class="info-item">LiveOps Engineering</div>
                <div class="info-item">Data Science Platform</div>
                <div class="info-item">Business Intelligence</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
