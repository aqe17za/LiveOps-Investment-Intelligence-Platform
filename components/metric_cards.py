"""Metric card components using HTML injection.

All cards use the CSS classes defined in assets/styles.css.
"""

import streamlit as st


def metric_card(
    label: str,
    value: str,
    delta: str = "",
    delta_positive: bool = True,
    accent: str = "blue",
    icon: str = "",
) -> None:
    """Render a single KPI metric card.

    Parameters
    ----------
    label : str — card title (shown uppercase, small)
    value : str — main display value
    delta : str — optional change indicator below the value
    delta_positive : bool — True=green, False=red
    accent : str — border-top color variant: 'blue'|'success'|'warning'|'error'|'purple'
    icon : str — optional emoji prefix on the label
    """
    accent_map = {
        "blue": "",
        "success": " success-accent",
        "warning": " warning-accent",
        "error": " error-accent",
        "purple": " purple-accent",
    }
    accent_class = accent_map.get(accent, "")

    delta_html = ""
    if delta:
        delta_class = "positive" if delta_positive else "negative"
        delta_html = f'<div class="metric-delta {delta_class}">{delta}</div>'

    label_text = f"{icon} {label}".strip() if icon else label

    st.markdown(
        f"""
        <div class="metric-card{accent_class}">
            <div class="metric-label">{label_text}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_row(cards: list[dict]) -> None:
    """Render a horizontal row of metric cards.

    Parameters
    ----------
    cards : list of dicts, each with keys matching metric_card() parameters
    """
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            metric_card(**card)


def decision_banner(decision: str, summary: str, confidence: str = "") -> None:
    """Render the large executive deployment decision banner.

    Parameters
    ----------
    decision : str — 'DO NOT DEPLOY' | 'DEPLOY GLOBALLY' | 'TARGETED DEPLOYMENT'
    summary : str — one-line rationale shown below the decision
    confidence : str — 'High' | 'Medium' | 'Low'
    """
    banner_class_map = {
        "DO NOT DEPLOY": "no-deploy",
        "DEPLOY GLOBALLY": "deploy",
        "TARGETED DEPLOYMENT": "targeted",
        "MORE DATA NEEDED": "targeted",
    }
    text_class_map = {
        "DO NOT DEPLOY": "no-deploy",
        "DEPLOY GLOBALLY": "deploy",
        "TARGETED DEPLOYMENT": "targeted",
        "MORE DATA NEEDED": "targeted",
    }
    banner_cls = banner_class_map.get(decision, "targeted")
    text_cls = text_class_map.get(decision, "targeted")

    confidence_html = ""
    if confidence:
        conf_cls = confidence.lower()
        confidence_html = f"""
        <div style="margin-top:1rem;">
            <span class="confidence-badge {conf_cls}">
                Confidence: {confidence}
            </span>
        </div>
        """

    st.markdown(
        f"""
        <div class="decision-banner {banner_cls}">
            <div class="decision-text {text_cls}">{decision}</div>
            <div class="decision-sub">{summary}</div>
            {confidence_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(label: str, status: str = "ready") -> str:
    """Return HTML for a status badge (inline use in st.markdown)."""
    return f'<span class="status-badge {status}">{label}</span>'


def player_card(player_data: dict) -> None:
    """Render a player detail card from a dict of {field: value} pairs."""
    rows_html = ""
    for field, value in player_data.items():
        rows_html += f"""
        <div class="player-field-row">
            <span class="player-field-label">{field}</span>
            <span class="player-field-value">{value}</span>
        </div>
        """

    st.markdown(
        f"""
        <div class="player-card">
            <div class="player-card-header">Player Profile</div>
            {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
