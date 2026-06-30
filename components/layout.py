"""Section headers, dividers, and layout helpers."""

import streamlit as st


def section_header(title: str, subtitle: str = "") -> None:
    """Render an EA-style blue-accented section header."""
    sub_html = f'<p>{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-header">
            <h2>{title}</h2>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Render the top-of-page platform header."""
    icon_html = f'<span style="font-size:1.5rem;">{icon}</span>' if icon else ""
    st.markdown(
        f"""
        <div class="platform-header">
            <div class="platform-title">
                {icon_html}
                <span><span class="ea-accent">EA</span> {title}</span>
            </div>
            <div class="platform-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_callout(text: str) -> None:
    """Render a blue info callout box."""
    st.markdown(
        f'<div class="info-callout">ℹ️ {text}</div>',
        unsafe_allow_html=True,
    )


def warning_callout(text: str) -> None:
    """Render an orange warning callout box."""
    st.markdown(
        f'<div class="warning-callout">⚠️ {text}</div>',
        unsafe_allow_html=True,
    )


def divider() -> None:
    """Thin separator line."""
    st.markdown(
        '<hr style="border:none; border-top:1px solid #2a2a3e; margin:1.5rem 0;">',
        unsafe_allow_html=True,
    )


def stat_row_html(icon: str, label: str, value: str) -> str:
    """Return HTML for a single stat row (used in info cards)."""
    return f"""
    <div class="stat-row">
        <span class="stat-icon">{icon}</span>
        <span class="stat-label">{label}</span>
        <span class="stat-value">{value}</span>
    </div>
    """


def excluded_segment_note(segment_name: str, reason: str = "Minimum sample size not met") -> None:
    """Render a standard 'segment excluded' callout for missing segments."""
    st.markdown(
        f"""
        <div style="background:#1a1a28; border:1px solid #2a2a3e; border-left:3px solid #555570;
             border-radius:6px; padding:0.6rem 0.85rem; font-size:0.78rem; margin:0.3rem 0;">
            <span style="color:#8888aa;">{segment_name}</span>
            <span style="color:#444460; margin:0 0.4rem;">—</span>
            <span style="color:#555570; font-style:italic;">Excluded: {reason}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
