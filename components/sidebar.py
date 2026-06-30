"""Sidebar pipeline status card rendered on every page.

Call render_sidebar() at the top of each page file.
"""

import streamlit as st

from utils.data_loader import load_manifest


def _render_pipeline_status(current_phase: int) -> None:
    """Render pipeline status with native Streamlit elements only."""
    phase_names = (
        "Production Telemetry",
        "Survival Analytics",
        "Decision Engine",
        "Causal Experimentation",
    )

    for number, name in enumerate(phase_names, start=1):
        label, indicator = st.columns([6, 1])
        label.caption(f"Phase {number} — {name}")
        indicator.markdown("✅" if number <= current_phase else "—")


def render_sidebar() -> None:
    """Render the persistent sidebar with pipeline status and navigation meta."""
    manifest = load_manifest()

    with st.sidebar:
        st.markdown("## ⬡ EA LiveOps")
        st.caption("Investment Intelligence Platform")
        st.divider()
        st.markdown("### 🔧 Pipeline Status")

        if manifest:
            phase = int(manifest.get("phase", 4))
            _render_pipeline_status(phase)

            version = manifest.get("manifest_version", "4.0.0")
            st.caption(f"**Version:** {version[:8]}")
            st.caption(f"**Artifacts:** {len(manifest.get('artifacts', []))}")

            st.divider()

            phase4 = manifest.get("phase_4_summary", {})
            decision = phase4.get("deployment_decision", "")
            if decision and "NOT" in decision:
                st.error("🔴 DO NOT DEPLOY")
        else:
            st.warning("Run pipeline first")


def render_artifact_footer(sources: list[tuple[str, str]]) -> None:
    """Render artifact source attribution with native Streamlit elements.

    Parameters
    ----------
    sources : list of (artifact_name, description) tuples
    """
    manifest = load_manifest()
    version = manifest.get("manifest_version", "—") if manifest else "—"
    timestamp = manifest.get("execution_timestamp", "—") if manifest else "—"
    if timestamp and timestamp != "—":
        timestamp = timestamp[:19].replace("T", " ") + " UTC"

    st.divider()

    for name, description in sources:
        st.markdown(f"**Artifact:** `{name}`")
        st.caption(description)

    version_col, note_col = st.columns(2)
    with version_col:
        st.markdown(f"**Pipeline Version:** {version}")
        st.caption(f"Generated {timestamp}")
    with note_col:
        st.markdown("**Note**")
        st.caption(
            "All metrics are read from validated pipeline artifacts. "
            "No models are retrained by this dashboard."
        )
