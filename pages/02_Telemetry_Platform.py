"""Phase 1 — Production Telemetry Platform

Feature engineering, data quality, and lifecycle segmentation.
Shows outputs from Phase 1 of the pipeline.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from components.sidebar import render_sidebar
from components.plot_components import (
    feature_correlation_heatmap,
    lifecycle_distribution_chart,
    session_distribution_chart,
    engagement_distribution_chart,
    retention_comparison_chart,
)
from utils.data_loader import (
    load_feature_store,
    load_data_profile,
    load_lifecycle_stages,
    load_manifest,
)
from utils.helpers import fmt_number, fmt_pct

render_sidebar()

# ── Load artifacts ────────────────────────────────────────────────────────
fs       = load_feature_store()
profile  = load_data_profile()
stages   = load_lifecycle_stages()
manifest = load_manifest() or {}

# ── Empty state ───────────────────────────────────────────────────────────
if fs is None or fs.empty:
    st.markdown("""
    <div class="empty-state fade-in">
        <div class="empty-icon">📡</div>
        <div class="empty-title">Feature Store Not Found</div>
        <div class="empty-message">
            The telemetry pipeline has not been executed yet.<br>
            Run Phase 1 to generate <code>feature_store.parquet</code> in
            <code>data/processed/</code>, then refresh this page.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Derived metrics ───────────────────────────────────────────────────────
n_players  = len(fs)
n_features = len(fs.columns)
d1_rate    = fs["retention_1"].mean() if "retention_1" in fs.columns else 0.0
d7_rate    = fs["retention_7"].mean() if "retention_7" in fs.columns else 0.0

version    = manifest.get("manifest_version", "v4.0.0")
timestamp  = manifest.get("execution_timestamp", "2024-12-30T12:00:00")
if timestamp and "T" in timestamp:
    timestamp = timestamp[:19].replace("T", " ") + " UTC"

# ═══════════════════════════════════════════════════════════════════════════
# HERO
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
            <span style="font-size:2rem;">📡</span>
            <div>
                <div style="font-size:1.75rem;font-weight:900;color:#ffffff;letter-spacing:-0.02em;">
                    Production Telemetry Platform
                </div>
                <div style="font-size:1rem;color:#b4bcd0;margin-top:0.25rem;">
                    Phase 1 Output — Feature engineering and lifecycle segmentation from the Cookie Cats dataset
                </div>
            </div>
        </div>
        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-top:1rem;">
            <span style="background:rgba(0,208,132,0.12);border:1px solid #00d084;
                color:#00d084;padding:0.3rem 0.75rem;border-radius:6px;
                font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">
                ✓ Phase 1 Complete
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
# KPI CARDS — 4 equal columns
# ═══════════════════════════════════════════════════════════════════════════
k1, k2, k3, k4 = st.columns(4)

def _kpi(col, icon, value, label, accent):
    accent_colors = {
        "blue":    ("#0077CC", "rgba(0,119,204,0.12)"),
        "green":   ("#00d084", "rgba(0,208,132,0.12)"),
        "amber":   ("#ff9500", "rgba(255,149,0,0.12)"),
        "red":     ("#ff3333", "rgba(255,51,51,0.12)"),
    }
    border_c, bg_c = accent_colors.get(accent, accent_colors["blue"])
    col.markdown(f"""
    <div style="
        background:{bg_c};
        border:1px solid {border_c};
        border-radius:12px;
        padding:1.5rem;
        text-align:center;
        transition:transform 0.2s ease,box-shadow 0.2s ease;
    ">
        <div style="font-size:2rem;margin-bottom:0.5rem;">{icon}</div>
        <div style="font-size:1.75rem;font-weight:800;color:#ffffff;
            font-variant-numeric:tabular-nums;line-height:1;">{value}</div>
        <div style="font-size:0.875rem;color:#b4bcd0;margin-top:0.4rem;font-weight:500;">{label}</div>
    </div>
    """, unsafe_allow_html=True)

_kpi(k1, "👥", fmt_number(n_players),  "Total Players",         "blue")
_kpi(k2, "🔧", str(n_features),        "Engineered Features",   "green")
_kpi(k3, "📅", fmt_pct(d1_rate),       "D1 Retention Rate",     "amber")
_kpi(k4, "📅", fmt_pct(d7_rate),       "D7 Retention Rate",     "amber")

st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# DATA QUALITY + EXPERIMENT GROUPS
# ═══════════════════════════════════════════════════════════════════════════
def _section(title, subtitle=""):
    sub_html = f'<div style="font-size:0.9rem;color:#b4bcd0;margin-top:0.25rem;">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div style="border-left:4px solid #0077CC;padding-left:0.85rem;margin:2rem 0 1rem 0;">
        <div style="font-size:1.25rem;font-weight:700;color:#ffffff;">{title}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

_section("Data Quality Assessment", "Completeness and integrity checks on the feature store")

qa1, qa2 = st.columns(2)

with qa1:
    missing      = (profile or {}).get("missing_values", {})
    total_miss   = sum(missing.values()) if missing else 0
    total_cells  = n_players * n_features
    complete_pct = 1 - total_miss / total_cells if total_cells > 0 else 1.0
    num_cols     = len([c for c in fs.columns if pd.api.types.is_numeric_dtype(fs[c])])
    cat_cols     = len(fs.columns) - num_cols

    st.markdown(f"""
    <div style="background:#1a1f2e;border:1px solid #3d4357;border-radius:12px;padding:1.5rem;">
        <div style="font-size:0.875rem;font-weight:700;color:#0077CC;text-transform:uppercase;
            letter-spacing:0.06em;margin-bottom:1rem;">Data Quality</div>
        <div style="display:flex;flex-direction:column;gap:0.6rem;">
            <div style="display:flex;justify-content:space-between;font-size:0.9rem;
                border-bottom:1px solid #3d4357;padding-bottom:0.5rem;">
                <span style="color:#b4bcd0;">Total missing values</span>
                <span style="color:#ffffff;font-weight:600;">{fmt_number(total_miss)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.9rem;
                border-bottom:1px solid #3d4357;padding-bottom:0.5rem;">
                <span style="color:#b4bcd0;">Complete records</span>
                <span style="color:#00d084;font-weight:600;">{fmt_pct(complete_pct)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.9rem;
                border-bottom:1px solid #3d4357;padding-bottom:0.5rem;">
                <span style="color:#b4bcd0;">Numeric features</span>
                <span style="color:#ffffff;font-weight:600;">{num_cols}</span>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.9rem;">
                <span style="color:#b4bcd0;">Categorical features</span>
                <span style="color:#ffffff;font-weight:600;">{cat_cols}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with qa2:
    version_counts = fs["version"].value_counts() if "version" in fs.columns else {}
    rows_html = ""
    for ver, cnt in version_counts.items():
        pct = cnt / n_players * 100 if n_players > 0 else 0
        color = "#0077CC" if "30" in str(ver) else "#7c4dff"
        rows_html += f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
            font-size:0.9rem;border-bottom:1px solid #3d4357;padding-bottom:0.5rem;margin-bottom:0.5rem;">
            <span style="color:#b4bcd0;">{ver.replace("_", " ").title()}</span>
            <span>
                <span style="color:{color};font-weight:700;">{fmt_number(cnt)}</span>
                <span style="color:#8a92a8;font-size:0.8rem;"> ({pct:.1f}%)</span>
            </span>
        </div>
        """
    st.markdown(f"""
    <div style="background:#1a1f2e;border:1px solid #3d4357;border-radius:12px;padding:1.5rem;">
        <div style="font-size:0.875rem;font-weight:700;color:#0077CC;text-transform:uppercase;
            letter-spacing:0.06em;margin-bottom:1rem;">Experiment Groups</div>
        {rows_html}
        <div style="display:flex;justify-content:space-between;font-size:0.9rem;">
            <span style="color:#b4bcd0;">Total players</span>
            <span style="color:#ffffff;font-weight:600;">{fmt_number(n_players)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# LIFECYCLE DISTRIBUTION + RETENTION COMPARISON
# ═══════════════════════════════════════════════════════════════════════════
_section("Lifecycle Distribution", "Player segmentation by engagement and activity level")

if "lifecycle_stage" in fs.columns:
    st.plotly_chart(
        lifecycle_distribution_chart(fs),
        use_container_width=True,
        config={"displayModeBar": False},
    )

st.divider()

_section("Retention by Version", "Gate 30 vs Gate 40 — Day 1 and Day 7 retention rates")

if "version" in fs.columns and "retention_1" in fs.columns and "retention_7" in fs.columns:
    st.plotly_chart(
        retention_comparison_chart(fs),
        use_container_width=True,
        config={"displayModeBar": False},
    )

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# ENGAGEMENT DISTRIBUTION + SESSION DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════
_section("Engagement & Session Distributions", "Player activity patterns across lifecycle stages")

ec1, ec2 = st.columns(2)

with ec1:
    if "engagement_score" in fs.columns and "lifecycle_stage" in fs.columns:
        st.plotly_chart(
            engagement_distribution_chart(fs),
            use_container_width=True,
            config={"displayModeBar": False},
        )

with ec2:
    if "sessions_per_day" in fs.columns:
        st.plotly_chart(
            session_distribution_chart(fs),
            use_container_width=True,
            config={"displayModeBar": False},
        )

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# CORRELATION HEATMAP
# ═══════════════════════════════════════════════════════════════════════════
_section("Feature Correlation Matrix", "Pairwise correlation between all engineered numeric features")

st.plotly_chart(
    feature_correlation_heatmap(fs),
    use_container_width=True,
    config={"displayModeBar": False},
)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# FEATURE STORE PREVIEW
# ═══════════════════════════════════════════════════════════════════════════
_section("Feature Store Preview", "Canonical player-level feature table from Phase 1")

preview_df = fs.head(15).copy()
for col in preview_df.columns:
    if pd.api.types.is_numeric_dtype(preview_df[col]):
        if col in ("retention_1", "retention_7"):
            preview_df[col] = preview_df[col].apply(
                lambda x: f"{x:.0%}" if pd.notna(x) else ""
            )
        elif col in ("engagement_score", "sessions_per_day"):
            preview_df[col] = preview_df[col].apply(
                lambda x: f"{x:.3f}" if pd.notna(x) else ""
            )
        elif col in ("sum_gamerounds", "userid"):
            preview_df[col] = preview_df[col].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else ""
            )

meta1, meta2, meta3, dl_col = st.columns([1, 1, 1, 1])
meta1.metric("Rows shown", "15")
meta2.metric("Total rows", fmt_number(n_players))
meta3.metric("Columns", str(n_features))
with dl_col:
    st.download_button(
        label="📥 Download CSV",
        data=fs.to_csv(index=False),
        file_name="feature_store.csv",
        mime="text/csv",
        key="dl_feature_store",
    )

st.dataframe(preview_df, use_container_width=True, hide_index=True)

st.info(
    "Showing first 15 players from the feature store. "
    "All features are engineered from the Cookie Cats A/B test dataset. "
    "Use the Download button above for the full dataset."
)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════
_section("Pipeline Artifacts", "Output files generated by Phase 1 — all validated and available")

processed_dir = Path(__file__).parent.parent / "data" / "processed"

artifacts = [
    {
        "icon": "📄",
        "name": "feature_store.parquet",
        "description": "Canonical player-level feature table",
        "detail": f"{fmt_number(n_players)} rows · {n_features} columns",
        "phase": "Phase 1",
    },
    {
        "icon": "📊",
        "name": "data_profile.json",
        "description": "Data quality and statistical summary",
        "detail": "Missing values, dtypes, distributions",
        "phase": "Phase 1",
    },
    {
        "icon": "🗂️",
        "name": "lifecycle_stages.csv",
        "description": "Player segmentation by lifecycle stage",
        "detail": "Categorised from engagement and activity",
        "phase": "Phase 1",
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
        <div style="font-size:0.95rem;font-weight:700;color:#ffffff;
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
footer_stats = (
    ("Pipeline Version", version),
    ("Last Updated", timestamp[:10] if len(timestamp) >= 10 else timestamp),
    ("Source Dataset", "Cookie Cats"),
    ("Feature Count", str(n_features)),
    ("Rows Processed", fmt_number(n_players)),
)
footer_items = "".join(
    (
        '<div class="telemetry-result">'
        f'<div class="telemetry-result-label">{label}</div>'
        f'<div class="telemetry-result-value">{value}</div>'
        "</div>"
    )
    for label, value in footer_stats
)

st.markdown(
    f"""
<style>
.telemetry-results-grid {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 1.5rem;
    width: 100%;
    padding: 0.75rem 0 1.5rem;
}}
.telemetry-result {{
    min-width: 0;
}}
.telemetry-result-label {{
    color: #e8e8f0;
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 0.45rem;
}}
.telemetry-result-value {{
    color: #e8e8f0;
    font-size: clamp(1.35rem, 2.1vw, 2rem);
    font-weight: 400;
    line-height: 1.2;
    overflow-wrap: anywhere;
}}
@media (max-width: 900px) {{
    .telemetry-results-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}
</style>
<div class="telemetry-results-grid">{footer_items}</div>
""",
    unsafe_allow_html=True,
)
