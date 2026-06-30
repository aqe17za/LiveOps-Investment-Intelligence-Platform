"""Formatting helpers used across all dashboard pages.

All functions are pure (no side effects) and safe to call anywhere.
"""

from typing import Optional, Union


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a float as a percentage string. e.g. 0.1901 → '19.0%'."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def fmt_number(value: Union[int, float], decimals: int = 0) -> str:
    """Format a number with thousands separator. e.g. 90189 → '90,189'."""
    if value is None:
        return "N/A"
    try:
        if decimals == 0:
            return f"{int(value):,}"
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_lift(value: float, decimals: int = 2) -> str:
    """Format an absolute lift as ±X.XX pp. e.g. -0.0082 → '-0.82 pp'."""
    if value is None:
        return "N/A"
    try:
        v = float(value) * 100
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.{decimals}f} pp"
    except (TypeError, ValueError):
        return "N/A"


def fmt_float(value: float, decimals: int = 4) -> str:
    """Format a float with fixed decimals."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_pvalue(p: float) -> str:
    """Format a p-value with appropriate precision."""
    if p is None:
        return "N/A"
    try:
        p = float(p)
        if p < 0.001:
            return "< 0.001"
        if p < 0.01:
            return f"{p:.4f}"
        return f"{p:.3f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_ci(lower: float, upper: float, pct: bool = True, decimals: int = 2) -> str:
    """Format a confidence interval. e.g. [lower, upper] as '[−0.82%, −0.31%]'."""
    try:
        if pct:
            return f"[{fmt_lift(lower, decimals)}, {fmt_lift(upper, decimals)}]"
        return f"[{float(lower):.{decimals}f}, {float(upper):.{decimals}f}]"
    except (TypeError, ValueError):
        return "N/A"


def lift_direction(value: float) -> str:
    """Return '▲', '▼', or '─' based on lift sign."""
    if value is None:
        return "─"
    if float(value) > 0:
        return "▲"
    if float(value) < 0:
        return "▼"
    return "─"


def lift_color_class(value: float) -> str:
    """Return CSS delta class: 'positive', 'negative', 'neutral'."""
    if value is None:
        return "neutral"
    if float(value) > 0:
        return "positive"
    if float(value) < 0:
        return "negative"
    return "neutral"


def confidence_emoji(level: str) -> str:
    """Map confidence level to an emoji indicator."""
    return {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(level, "⚪")


def decision_emoji(decision: str) -> str:
    """Map deployment decision to an emoji."""
    return {
        "DEPLOY GLOBALLY": "✅",
        "DO NOT DEPLOY": "🚫",
        "TARGETED DEPLOYMENT": "🎯",
        "MORE DATA NEEDED": "📊",
    }.get(decision, "❓")


def risk_emoji(risk_group: str) -> str:
    """Map risk group to an emoji."""
    return {
        "High Churn Risk": "🔴",
        "Medium Churn Risk": "🟡",
        "Low Churn Risk": "🟢",
    }.get(risk_group, "⚪")


def truncate_userid(userid: int, n: int = 6) -> str:
    """Display last N digits of a userid for compact display."""
    return f"...{str(userid)[-n:]}"


def format_bytes(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / 1024 ** 2:.1f} MB"


def significant_label(p_corrected: float, alpha: float = 0.05) -> str:
    """Return significance label for a corrected p-value."""
    if p_corrected < 0.001:
        return "*** p<0.001"
    if p_corrected < 0.01:
        return "** p<0.01"
    if p_corrected < alpha:
        return f"* p<{alpha}"
    return "ns"


def priority_band(score: float) -> str:
    """Map a priority score [0,1] to a band label."""
    if score >= 0.80:
        return "Critical"
    if score >= 0.60:
        return "High"
    if score >= 0.40:
        return "Medium"
    return "Low"
