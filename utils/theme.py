"""Color palette, Plotly theme defaults, and segment color mappings.

All chart functions import from here. Changing a color here changes it
everywhere in the dashboard.
"""

# ── Hex to RGBA Conversion Helper ─────────────────────────────────────────
def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert hex color to rgba string.
    
    Parameters
    ----------
    hex_color : str
        Hex color like "#0077CC" or "0077CC"
    alpha : float
        Alpha transparency 0.0 to 1.0
        
    Returns
    -------
    str
        RGBA string like "rgba(0,119,204,0.5)"
        
    Examples
    --------
    >>> hex_to_rgba("#0077CC", 0.2)
    'rgba(0,119,204,0.2)'
    >>> hex_to_rgba("FF5733", 0.5)
    'rgba(255,87,51,0.5)'
    """
    # Remove # if present (only the first character)
    if hex_color.startswith("#"):
        hex_color = hex_color[1:]
    
    # Convert to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    return f"rgba({r},{g},{b},{alpha})"


# ── EA Color Palette ───────────────────────────────────────────────────────
EA_BLUE = "#0077CC"
EA_BLUE_LIGHT = "#1a8fe0"
EA_BLUE_DARK = "#005fa3"
EA_BLUE_GLOW = "rgba(0, 119, 204, 0.15)"

BG_PRIMARY = "#0a0a0f"
BG_SECONDARY = "#12121a"
BG_CARD = "#1a1a28"
BG_CARD_HOVER = "#1f1f35"
BORDER = "#2a2a3e"
BORDER_ACCENT = "#3a3a58"

TEXT_PRIMARY = "#e8e8f0"
TEXT_SECONDARY = "#8888aa"
TEXT_MUTED = "#555570"

SUCCESS = "#22c55e"
WARNING = "#f59e0b"
ERROR = "#ef4444"
INFO = "#3b82f6"
HIGHLIGHT = "#6366f1"
PURPLE = "#8b5cf6"
ORANGE = "#f97316"

# ── Plotly Layout Defaults ────────────────────────────────────────────────
PLOTLY_BG = "#12121a"
PLOTLY_PAPER_BG = "#0a0a0f"
PLOTLY_GRID = "#2a2a3e"
PLOTLY_FONT_COLOR = "#e8e8f0"
PLOTLY_FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"

PLOTLY_LAYOUT_DEFAULTS = dict(
    font=dict(family=PLOTLY_FONT_FAMILY, color=PLOTLY_FONT_COLOR, size=12),
    paper_bgcolor=PLOTLY_PAPER_BG,
    plot_bgcolor=PLOTLY_BG,
    margin=dict(l=50, r=30, t=50, b=50),
    xaxis=dict(
        gridcolor=PLOTLY_GRID,
        showgrid=True,
        gridwidth=1,
        linecolor=BORDER_ACCENT,
        tickfont=dict(color=TEXT_SECONDARY, size=11),
        title_font=dict(color=TEXT_SECONDARY, size=12),
    ),
    yaxis=dict(
        gridcolor=PLOTLY_GRID,
        showgrid=True,
        gridwidth=1,
        linecolor=BORDER_ACCENT,
        tickfont=dict(color=TEXT_SECONDARY, size=11),
        title_font=dict(color=TEXT_SECONDARY, size=12),
    ),
    legend=dict(
        bgcolor="rgba(26,26,40,0.8)",
        bordercolor=BORDER,
        borderwidth=1,
        font=dict(color=TEXT_SECONDARY, size=11),
    ),
    hoverlabel=dict(
        bgcolor=BG_CARD,
        bordercolor=EA_BLUE,
        font=dict(color=TEXT_PRIMARY, family=PLOTLY_FONT_FAMILY, size=12),
    ),
)

# ── Segment Color Maps ────────────────────────────────────────────────────

LIFECYCLE_COLORS: dict = {
    "Active": SUCCESS,
    "Onboarding": INFO,
    "At-Risk": WARNING,
    "Dormant": ERROR,
    "Variable": TEXT_SECONDARY,
    "Loyal": PURPLE,
}

RISK_COLORS: dict = {
    "Low Churn Risk": SUCCESS,
    "Medium Churn Risk": WARNING,
    "High Churn Risk": ERROR,
}

ACTION_COLORS: dict = {
    "High Priority Reactivation": ERROR,
    "At-Risk Retention": ORANGE,
    "Onboarding Nurture": INFO,
    "Active Growth": SUCCESS,
    "Loyalty Reward": PURPLE,
    "Monitor and Observe": TEXT_SECONDARY,
}

DECILE_COLORS: dict = {
    "Top 10%": EA_BLUE,
    "80-90%": EA_BLUE_LIGHT,
    "70-80%": "#4da6e0",
    "60-70%": "#6db8e8",
    "50-60%": "#8dc9ef",
    "40-50%": "#aad6f4",
    "30-40%": TEXT_SECONDARY,
    "20-30%": "#666688",
    "10-20%": "#444460",
    "Bottom 10%": BORDER_ACCENT,
}

CONFIDENCE_COLORS: dict = {
    "High": SUCCESS,
    "Medium": WARNING,
    "Low": ERROR,
}

DECISION_COLORS: dict = {
    "DEPLOY GLOBALLY": SUCCESS,
    "DO NOT DEPLOY": ERROR,
    "TARGETED DEPLOYMENT": WARNING,
    "MORE DATA NEEDED": INFO,
}
