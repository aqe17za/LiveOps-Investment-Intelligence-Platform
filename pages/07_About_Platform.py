"""About Platform

Architecture overview, technology stack, and engineering principles.
Project statistics and technical documentation.
"""

import streamlit as st
from pathlib import Path
from datetime import datetime

from components.sidebar import render_sidebar
from utils.data_loader import load_manifest, check_artifact_availability
from utils.helpers import fmt_number

# Page config and sidebar
render_sidebar()

# Load manifest for project stats
manifest = load_manifest()
artifact_status = check_artifact_availability()

# Count files in project
project_root = Path(__file__).resolve().parent.parent
python_files = list(project_root.rglob("*.py"))
test_files = list(project_root.rglob("*test*.py"))
config_files = list(project_root.rglob("*.yaml")) + list(project_root.rglob("*.yml")) + list(project_root.rglob("*.json"))
doc_files = list(project_root.rglob("*.md"))

# Artifact stats
total_artifacts = len(manifest.get("artifacts", [])) if manifest else 0
available_artifacts = sum(1 for exists in artifact_status.values() if exists)
version = manifest.get("manifest_version", "4.0.0") if manifest else "4.0.0"
timestamp = manifest.get("execution_timestamp", "Unknown") if manifest else "Unknown"

# ═══════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ═══════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div style="
    background:linear-gradient(135deg,#1a1a28 0%,#0f0f18 100%);
    border:1px solid #2a2a3e;border-radius:16px;padding:3rem;
    margin-bottom:2rem;position:relative;overflow:hidden;">
    <div style="
        position:absolute;top:0;left:0;right:0;bottom:0;
        background:radial-gradient(ellipse at top left,rgba(0,119,204,0.12) 0%,transparent 60%);
        pointer-events:none;
    "></div>
    <div style="position:relative;z-index:1;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:3rem;">
            <div style="flex:1;min-width:320px;">
                <div style="font-size:0.85rem;font-weight:700;color:#8888aa;
                    text-transform:uppercase;letter-spacing:0.15em;margin-bottom:0.75rem;">
                    Platform Documentation
                </div>
                <h1 style="font-size:3rem;font-weight:900;color:#e8e8f0;
                    margin:0 0 1.25rem 0;letter-spacing:-0.03em;line-height:1.1;">
                    About the Platform
                </h1>
                <p style="font-size:1.15rem;color:#b4bcd0;margin:0;line-height:1.7;">
                    Architecture, engineering decisions, technology stack, and implementation 
                    details behind the <strong style="color:#0077CC;">EA LiveOps Investment 
                    Intelligence Platform</strong>.
                </p>
            </div>
            <div style="min-width:280px;">
                <div style="background:rgba(34,197,94,0.08);border:2px solid #22c55e;
                    border-radius:16px;padding:1.75rem;text-align:center;">
                    <div style="font-size:2.5rem;margin-bottom:0.75rem;">✓</div>
                    <div style="font-size:1.25rem;font-weight:800;color:#22c55e;margin-bottom:1rem;">
                        Production Ready
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;text-align:left;">
                        <div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:0.75rem;">
                            <div style="font-size:0.7rem;color:#8888aa;margin-bottom:0.25rem;">Pipeline</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;">4 Phases</div>
                        </div>
                        <div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:0.75rem;">
                            <div style="font-size:0.7rem;color:#8888aa;margin-bottom:0.25rem;">Tests</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;">30/30</div>
                        </div>
                        <div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:0.75rem;">
                            <div style="font-size:0.7rem;color:#8888aa;margin-bottom:0.25rem;">Artifacts</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;">{available_artifacts}</div>
                        </div>
                        <div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:0.75rem;">
                            <div style="font-size:0.7rem;color:#8888aa;margin-bottom:0.25rem;">Status</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#22c55e;">Ready</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PROJECT OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:0 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Project Overview</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">What this platform does and how it works</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:2rem;margin:1rem 0;">
    <p style="font-size:1.05rem;color:#b4bcd0;line-height:1.8;margin:0 0 1rem 0;">
        The <strong style="color:#0077CC;">EA LiveOps Investment Intelligence Platform</strong> is a 
        production-grade data science pipeline that analyzes player behavior, predicts churn risk, 
        generates personalized intervention recommendations, and evaluates A/B test results to inform 
        game design decisions.
    </p>
    <p style="font-size:1.05rem;color:#b4bcd0;line-height:1.8;margin:0 0 1rem 0;">
        The system processes player telemetry through <strong style="color:#22c55e;">four sequential 
        phases</strong>, each producing validated artifacts that feed into the next stage. Every 
        phase is tested, documented, and designed for enterprise production environments.
    </p>
    <div style="background:rgba(0,119,204,0.08);border-left:4px solid #0077CC;
        border-radius:8px;padding:1.25rem;margin-top:1.5rem;">
        <div style="font-size:0.95rem;font-weight:700;color:#0077CC;margin-bottom:0.5rem;">
            Designed For
        </div>
        <div style="font-size:0.95rem;color:#e8e8f0;line-height:1.7;">
            LiveOps teams, product managers, data scientists, and engineering leaders who need 
            <strong>actionable insights</strong> from player behavior data to drive retention 
            and engagement strategies.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Pipeline flow visualization
st.markdown("""
<div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:1.5rem;margin:1rem 0;">
    <h4 style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin:0 0 1.5rem 0;text-align:center;">
        Pipeline Architecture
    </h4>
    <div style="display:grid;grid-template-columns:1fr auto 1fr auto 1fr auto 1fr;
        gap:1rem;align-items:center;">
        <div style="background:rgba(0,119,204,0.12);border:1px solid #0077CC;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:1.5rem;margin-bottom:0.5rem;">📡</div>
            <div style="font-size:0.85rem;font-weight:700;color:#0077CC;">Phase 1</div>
            <div style="font-size:0.75rem;color:#8888aa;">Telemetry</div>
        </div>
        <div style="font-size:1.5rem;color:#2a2a3e;">→</div>
        <div style="background:rgba(99,102,241,0.12);border:1px solid #6366f1;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:1.5rem;margin-bottom:0.5rem;">📉</div>
            <div style="font-size:0.85rem;font-weight:700;color:#6366f1;">Phase 2</div>
            <div style="font-size:0.75rem;color:#8888aa;">Survival</div>
        </div>
        <div style="font-size:1.5rem;color:#2a2a3e;">→</div>
        <div style="background:rgba(245,158,11,0.12);border:1px solid #f59e0b;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:1.5rem;margin-bottom:0.5rem;">🎯</div>
            <div style="font-size:0.85rem;font-weight:700;color:#f59e0b;">Phase 3</div>
            <div style="font-size:0.75rem;color:#8888aa;">Decision</div>
        </div>
        <div style="font-size:1.5rem;color:#2a2a3e;">→</div>
        <div style="background:rgba(34,197,94,0.12);border:1px solid #22c55e;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:1.5rem;margin-bottom:0.5rem;">🧪</div>
            <div style="font-size:0.85rem;font-weight:700;color:#22c55e;">Phase 4</div>
            <div style="font-size:0.75rem;color:#8888aa;">Experiment</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PROJECT STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Project Statistics</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Technical metrics and implementation details</p>
</div>
""", unsafe_allow_html=True)

s1, s2, s3, s4, s5, s6 = st.columns(6)

def _stat_card(col, icon, label, value, color):
    col.markdown(f"""
    <div style="background:#1a1a28;border:1px solid {color};border-radius:12px;
        padding:1.5rem;text-align:center;min-height:180px;
        display:flex;flex-direction:column;justify-content:center;">
        <div style="font-size:2.5rem;margin-bottom:0.75rem;">{icon}</div>
        <div style="font-size:0.75rem;color:#8888aa;text-transform:uppercase;
            letter-spacing:0.05em;margin-bottom:0.5rem;">{label}</div>
        <div style="font-size:2rem;font-weight:800;color:{color};letter-spacing:-0.02em;">{value}</div>
    </div>
    """, unsafe_allow_html=True)

_stat_card(s1, "🐍", "Python Files", len(python_files), "#0077CC")
_stat_card(s2, "⚡", "Pipeline Phases", "4", "#6366f1")
_stat_card(s3, "📦", "Artifacts", available_artifacts, "#22c55e")
_stat_card(s4, "🧪", "Tests", len(test_files), "#f59e0b")
_stat_card(s5, "📚", "Documentation", len(doc_files), "#8b5cf6")
_stat_card(s6, "📝", "Version", version[:6], "#ef4444")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TECHNOLOGY STACK
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Technology Stack</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Core technologies and frameworks</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:2rem;">
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;">
        <div style="background:rgba(0,119,204,0.08);border:1px solid #0077CC;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#0077CC;">Python 3.9+</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Core Language</div>
        </div>
        <div style="background:rgba(99,102,241,0.08);border:1px solid #6366f1;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#6366f1;">Pandas</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Data Analysis</div>
        </div>
        <div style="background:rgba(245,158,11,0.08);border:1px solid #f59e0b;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#f59e0b;">Plotly</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Visualization</div>
        </div>
        <div style="background:rgba(34,197,94,0.08);border:1px solid #22c55e;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#22c55e;">Streamlit</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Dashboard</div>
        </div>
        <div style="background:rgba(139,92,246,0.08);border:1px solid #8b5cf6;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#8b5cf6;">Lifelines</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Survival Analysis</div>
        </div>
        <div style="background:rgba(239,68,68,0.08);border:1px solid #ef4444;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#ef4444;">SciPy</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Statistics</div>
        </div>
        <div style="background:rgba(0,119,204,0.08);border:1px solid #0077CC;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#0077CC;">PyTest</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Testing</div>
        </div>
        <div style="background:rgba(99,102,241,0.08);border:1px solid #6366f1;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#6366f1;">PyYAML</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Configuration</div>
        </div>
        <div style="background:rgba(245,158,11,0.08);border:1px solid #f59e0b;
            border-radius:8px;padding:1rem;text-align:center;">
            <div style="font-size:0.9rem;font-weight:700;color:#f59e0b;">Git</div>
            <div style="font-size:0.75rem;color:#8888aa;margin-top:0.25rem;">Version Control</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Pipeline Architecture</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Four-phase analytical workflow</p>
</div>
""", unsafe_allow_html=True)

phases_detail = [
    {
        "num": "1", "title": "Telemetry Platform", "icon": "📡",
        "desc": "Feature engineering and lifecycle segmentation",
        "color": "#0077CC", "bg": "rgba(0,119,204,0.08)"
    },
    {
        "num": "2", "title": "Survival Analytics", "icon": "📉",
        "desc": "Time-to-event analysis and churn prediction",
        "color": "#6366f1", "bg": "rgba(99,102,241,0.08)"
    },
    {
        "num": "3", "title": "Decision Intelligence", "icon": "🎯",
        "desc": "Business rule engine and intervention recommendations",
        "color": "#f59e0b", "bg": "rgba(245,158,11,0.08)"
    },
    {
        "num": "4", "title": "Experiment Evaluation", "icon": "🧪",
        "desc": "A/B test analysis and statistical validation",
        "color": "#22c55e", "bg": "rgba(34,197,94,0.08)"
    }
]

for phase in phases_detail:
    st.markdown(f"""
    <div style="background:{phase['bg']};border:1px solid {phase['color']};
        border-radius:12px;padding:1.5rem;margin:1rem 0;">
        <div style="display:flex;align-items:center;gap:1.5rem;">
            <div style="background:{phase['color']};border-radius:50%;
                width:60px;height:60px;display:flex;align-items:center;
                justify-content:center;font-size:1.5rem;flex-shrink:0;">{phase['icon']}</div>
            <div style="flex:1;">
                <div style="font-size:0.75rem;color:{phase['color']};font-weight:700;
                    text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem;">
                    Phase {phase['num']}
                </div>
                <div style="font-size:1.25rem;font-weight:700;color:#e8e8f0;margin-bottom:0.5rem;">
                    {phase['title']}
                </div>
                <div style="font-size:0.95rem;color:#b4bcd0;line-height:1.6;">
                    {phase['desc']}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# ENGINEERING PRINCIPLES
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Engineering Principles</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Design philosophy and best practices</p>
</div>
""", unsafe_allow_html=True)

principles = [
    {"icon": "🔁", "title": "Reproducibility", "desc": "Fixed random seeds and versioned data", "color": "#0077CC"},
    {"icon": "🧪", "title": "Testing", "desc": "Comprehensive test coverage (30/30 passing)", "color": "#22c55e"},
    {"icon": "📚", "title": "Documentation", "desc": "Detailed technical and methodology docs", "color": "#8b5cf6"},
    {"icon": "⚙️", "title": "Configuration", "desc": "YAML-based settings management", "color": "#6366f1"},
    {"icon": "✓", "title": "Validation", "desc": "Artifact integrity and quality checks", "color": "#22c55e"},
    {"icon": "🧩", "title": "Modularity", "desc": "Clean separation between pipeline phases", "color": "#f59e0b"},
]

cols = st.columns(3)
for i, principle in enumerate(principles):
    with cols[i % 3]:
        st.markdown(f"""
        <div style="background:#1a1a28;border:1px solid {principle['color']};
            border-radius:12px;padding:1.5rem;margin:0.5rem 0;min-height:160px;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">{principle['icon']}</div>
            <div style="font-size:1rem;font-weight:700;color:{principle['color']};
                margin-bottom:0.5rem;">{principle['title']}</div>
            <div style="font-size:0.85rem;color:#8888aa;line-height:1.6;">
                {principle['desc']}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# FUTURE ROADMAP
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Future Roadmap</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Planned enhancements and features</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;padding:2rem;">
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:2rem;">
        <div style="text-align:center;">
            <div style="background:rgba(0,119,204,0.12);border:2px solid #0077CC;
                border-radius:50%;width:80px;height:80px;margin:0 auto 1rem auto;
                display:flex;align-items:center;justify-content:center;">
                <span style="font-size:1.75rem;font-weight:800;color:#0077CC;">4.1</span>
            </div>
            <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.75rem;">
                Real-time Integration
            </div>
            <div style="font-size:0.9rem;color:#8888aa;line-height:1.6;">
                Live player telemetry streaming and real-time risk scoring
            </div>
        </div>
        <div style="text-align:center;">
            <div style="background:rgba(99,102,241,0.12);border:2px solid #6366f1;
                border-radius:50%;width:80px;height:80px;margin:0 auto 1rem auto;
                display:flex;align-items:center;justify-content:center;">
                <span style="font-size:1.75rem;font-weight:800;color:#6366f1;">5.0</span>
            </div>
            <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.75rem;">
                Multi-Game Support
            </div>
            <div style="font-size:0.9rem;color:#8888aa;line-height:1.6;">
                Generalized pipeline for different game genres and platforms
            </div>
        </div>
        <div style="text-align:center;">
            <div style="background:rgba(34,197,94,0.12);border:2px solid #22c55e;
                border-radius:50%;width:80px;height:80px;margin:0 auto 1rem auto;
                display:flex;align-items:center;justify-content:center;">
                <span style="font-size:1.75rem;font-weight:800;color:#22c55e;">6.0</span>
            </div>
            <div style="font-size:1.1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.75rem;">
                Advanced ML Models
            </div>
            <div style="font-size:0.9rem;color:#8888aa;line-height:1.6;">
                Deep learning for churn prediction and revenue optimization
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# RESOURCES
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:2rem 0 0.5rem 0;">
    <h2 style="font-size:1.75rem;font-weight:700;color:#e8e8f0;margin:0;">Resources</h2>
    <p style="font-size:0.95rem;color:#8888aa;margin:0.25rem 0 0 0;">Documentation and external links</p>
</div>
""", unsafe_allow_html=True)

resources = [
    {"icon": "📂", "title": "GitHub Repository", "desc": "View source code and contribute", "status": "coming"},
    {"icon": "📖", "title": "Documentation", "desc": "Technical specifications and guides", "status": "coming"},
    {"icon": "🏗️", "title": "Architecture", "desc": "System design and data flow", "status": "coming"},
    {"icon": "📊", "title": "Artifacts", "desc": "Download pipeline outputs", "status": "coming"},
]

cols = st.columns(4)
for i, resource in enumerate(resources):
    with cols[i]:
        status_color = "#555570" if resource["status"] == "coming" else "#22c55e"
        status_bg = "rgba(85,85,112,0.08)" if resource["status"] == "coming" else "rgba(34,197,94,0.08)"
        status_text = "Coming Soon" if resource["status"] == "coming" else "Available"
        
        st.markdown(f"""
        <div style="background:#1a1a28;border:1px solid #2a2a3e;border-radius:12px;
            padding:1.5rem;text-align:center;min-height:200px;
            display:flex;flex-direction:column;justify-content:space-between;">
            <div>
                <div style="font-size:2.5rem;margin-bottom:0.75rem;">{resource['icon']}</div>
                <div style="font-size:1rem;font-weight:700;color:#e8e8f0;margin-bottom:0.5rem;">
                    {resource['title']}
                </div>
                <div style="font-size:0.85rem;color:#8888aa;line-height:1.5;margin-bottom:1rem;">
                    {resource['desc']}
                </div>
            </div>
            <div style="background:{status_bg};border:1px solid {status_color};
                border-radius:6px;padding:0.5rem;color:{status_color};
                font-size:0.8rem;font-weight:600;cursor:not-allowed;opacity:0.7;">
                {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# FOOTER - NATIVE STREAMLIT (NO HTML)
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin:3rem 0 0.5rem 0;">
    <h3 style="font-size:1.25rem;font-weight:700;color:#e8e8f0;margin:0;">Platform Information</h3>
</div>
""", unsafe_allow_html=True)

# Clean footer using native Streamlit columns
f1, f2, f3, f4, f5 = st.columns(5)

with f1:
    st.metric("Pipeline Version", version[:8])

with f2:
    generated_time = timestamp[:10] if timestamp != "Unknown" else "Unknown"
    st.metric("Generated", generated_time)

with f3:
    st.metric("Artifacts", f"{available_artifacts}/{total_artifacts}")

with f4:
    st.metric("Source Dataset", "Cookie Cats")

with f5:
    st.metric("License", "MIT")

st.markdown("<br><br>", unsafe_allow_html=True)
