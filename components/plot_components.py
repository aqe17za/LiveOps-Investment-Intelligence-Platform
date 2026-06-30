"""All Plotly chart functions for the EA LiveOps Intelligence Platform.

Rules:
- Every function returns a go.Figure (never renders directly)
- Every figure uses the centralized PLOTLY_LAYOUT_DEFAULTS from theme.py
- No matplotlib
- All charts support hover, zoom, and export via Plotly's default toolbar
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from utils.theme import (
    ACTION_COLORS, CONFIDENCE_COLORS, DECILE_COLORS,
    EA_BLUE, EA_BLUE_LIGHT, ERROR, SUCCESS, WARNING, INFO, HIGHLIGHT, PURPLE,
    LIFECYCLE_COLORS, PLOTLY_BG, PLOTLY_LAYOUT_DEFAULTS, PLOTLY_PAPER_BG,
    RISK_COLORS, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, BORDER, ORANGE,
    BG_CARD, hex_to_rgba
)


def _apply_defaults(fig: go.Figure, title: str = "") -> go.Figure:
    """Apply centralized layout defaults and optional title to a figure."""
    layout = dict(PLOTLY_LAYOUT_DEFAULTS)
    if title:
        layout["title"] = dict(
            text=title,
            font=dict(size=14, color=TEXT_PRIMARY),
            x=0,
            xanchor="left",
            pad=dict(l=0),
        )
    fig.update_layout(**layout)
    return fig


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — TELEMETRY PLATFORM
# ════════════════════════════════════════════════════════════════════════════


def feature_correlation_heatmap(df: pd.DataFrame) -> go.Figure:
    """Correlation heatmap for numeric feature store columns."""
    numeric_cols = [
        "sum_gamerounds", "sessions_per_day", "session_frequency_bin",
        "progression_proxy", "engagement_score", "retention_1", "retention_7",
    ]
    available = [c for c in numeric_cols if c in df.columns]
    corr = df[available].corr()

    labels = {
        "sum_gamerounds": "Game Rounds",
        "sessions_per_day": "Sessions/Day",
        "session_frequency_bin": "Freq Bin",
        "progression_proxy": "Progression",
        "engagement_score": "Engagement",
        "retention_1": "D1 Retention",
        "retention_7": "D7 Retention",
    }
    display_labels = [labels.get(c, c) for c in corr.columns]

    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=display_labels,
            y=display_labels,
            colorscale=[
                [0.0, "#2d0e1a"],
                [0.25, "#6b1a3a"],
                [0.5, PLOTLY_BG],
                [0.75, "#0d3d6e"],
                [1.0, EA_BLUE],
            ],
            zmin=-1,
            zmax=1,
            text=[[f"{v:.2f}" for v in row] for row in corr.values],
            texttemplate="%{text}",
            textfont=dict(size=10, color=TEXT_PRIMARY),
            hovertemplate="<b>%{y} × %{x}</b><br>Correlation: %{z:.3f}<extra></extra>",
        )
    )
    fig = _apply_defaults(fig, "Feature Correlation Matrix")
    fig.update_layout(height=420, xaxis_showgrid=False, yaxis_showgrid=False)
    return fig


def lifecycle_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of lifecycle stage distribution."""
    counts = df["lifecycle_stage"].value_counts().reset_index()
    counts.columns = ["stage", "count"]
    counts["pct"] = counts["count"] / counts["count"].sum() * 100
    counts["color"] = counts["stage"].map(LIFECYCLE_COLORS).fillna(TEXT_SECONDARY)

    fig = go.Figure(
        go.Bar(
            x=counts["count"],
            y=counts["stage"],
            orientation="h",
            marker_color=counts["color"].tolist(),
            text=[f"{p:.1f}%" for p in counts["pct"]],
            textposition="outside",
            textfont=dict(color=TEXT_SECONDARY, size=11),
            hovertemplate="<b>%{y}</b><br>Players: %{x:,}<br>Share: %{text}<extra></extra>",
        )
    )
    fig = _apply_defaults(fig, "Player Lifecycle Stage Distribution")
    fig.update_layout(height=300, xaxis_title="Players", yaxis_title="")
    return fig


def session_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Histogram of sessions_per_day with median line."""
    median = df["sessions_per_day"].median()

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=df["sessions_per_day"].clip(upper=20),
            nbinsx=50,
            marker_color=EA_BLUE,
            opacity=0.8,
            name="Players",
            hovertemplate="Sessions/Day: %{x}<br>Count: %{y:,}<extra></extra>",
        )
    )
    fig.add_vline(
        x=median,
        line_dash="dash",
        line_color=WARNING,
        annotation_text=f"Median: {median:.1f}",
        annotation_font_color=WARNING,
        annotation_position="top right",
    )
    fig = _apply_defaults(fig, "Sessions per Day Distribution")
    fig.update_layout(height=300, xaxis_title="Sessions per Day", yaxis_title="Players", showlegend=False)
    return fig


def engagement_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Box plots of engagement_score by lifecycle stage."""
    stages = df["lifecycle_stage"].unique()
    fig = go.Figure()

    for stage in stages:
        color = LIFECYCLE_COLORS.get(stage, TEXT_SECONDARY)
        fig.add_trace(
            go.Box(
                y=df[df["lifecycle_stage"] == stage]["engagement_score"],
                name=stage,
                marker_color=color,
                line_color=color,
                boxmean="sd",
                hovertemplate=f"<b>{stage}</b><br>Engagement: %{{y:.3f}}<extra></extra>",
            )
        )
    fig = _apply_defaults(fig, "Engagement Score by Lifecycle Stage")
    fig.update_layout(height=350, yaxis_title="Engagement Score", xaxis_title="")
    return fig


def retention_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """D1 vs D7 retention comparison by version."""
    d1_g30 = df[df["version"] == "gate_30"]["retention_1"].mean()
    d7_g30 = df[df["version"] == "gate_30"]["retention_7"].mean()
    d1_g40 = df[df["version"] == "gate_40"]["retention_1"].mean()
    d7_g40 = df[df["version"] == "gate_40"]["retention_7"].mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Gate 30 (Control)",
        x=["D1 Retention", "D7 Retention"],
        y=[d1_g30 * 100, d7_g30 * 100],
        marker_color=EA_BLUE,
        text=[f"{d1_g30:.1%}", f"{d7_g30:.1%}"],
        textposition="outside",
        textfont=dict(color=TEXT_SECONDARY),
        hovertemplate="Gate 30 — %{x}: %{text}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Gate 40 (Treatment)",
        x=["D1 Retention", "D7 Retention"],
        y=[d1_g40 * 100, d7_g40 * 100],
        marker_color=HIGHLIGHT,
        text=[f"{d1_g40:.1%}", f"{d7_g40:.1%}"],
        textposition="outside",
        textfont=dict(color=TEXT_SECONDARY),
        hovertemplate="Gate 40 — %{x}: %{text}<extra></extra>",
    ))
    fig = _apply_defaults(fig, "Retention by Version (Gate 30 vs Gate 40)")
    fig.update_layout(height=320, barmode="group", yaxis_title="Retention Rate (%)", xaxis_title="")
    return fig


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 — PLAYER SURVIVAL ANALYTICS
# ════════════════════════════════════════════════════════════════════════════


def km_step_chart(df: pd.DataFrame) -> go.Figure:
    """Kaplan-Meier step chart from survival_curves.parquet.

    Adds a day-0 anchor (survival=1.0) for each group so the step
    chart starts correctly. Day-0 is not fabricated — it is a mathematical
    identity (all players survive at time 0 by definition).
    """
    fig = go.Figure()
    stages = df["lifecycle_stage"].dropna().unique()

    for stage in stages:
        stage_df = df[df["lifecycle_stage"] == stage].sort_values("time_days")
        color = LIFECYCLE_COLORS.get(stage, TEXT_SECONDARY)

        # Prepend t=0 anchor
        times = [0] + stage_df["time_days"].tolist()
        probs = [1.0] + stage_df["survival_prob"].tolist()
        ci_lo = [1.0] + stage_df["ci_lower"].tolist()
        ci_hi = [1.0] + stage_df["ci_upper"].tolist()

        # CI band
        fig.add_trace(go.Scatter(
            x=times + times[::-1],
            y=ci_hi + ci_lo[::-1],
            fill="toself",
            fillcolor=hex_to_rgba(color, 0.08),
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ))

        # Step line
        n = stage_df["n_players"].iloc[0] if len(stage_df) > 0 else 0
        fig.add_trace(go.Scatter(
            x=times,
            y=probs,
            mode="lines+markers",
            name=f"{stage} (n={n:,})",
            line=dict(color=color, width=2.5, shape="hv"),
            marker=dict(size=7, color=color),
            hovertemplate=(
                f"<b>{stage}</b><br>"
                "Day %{x}<br>"
                "Survival: %{y:.1%}<extra></extra>"
            ),
        ))

    fig = _apply_defaults(fig, "Survival Probability by Lifecycle Stage (KM Estimates)")
    fig.add_hline(y=0.5, line_dash="dot", line_color=TEXT_MUTED,
                  annotation_text="50% survival", annotation_font_color=TEXT_MUTED)
    fig.update_layout(
        height=420,
        xaxis_title="Days",
        yaxis_title="Survival Probability",
        yaxis=dict(**PLOTLY_LAYOUT_DEFAULTS["yaxis"], range=[0, 1.05],
                   tickformat=".0%"),
        xaxis=dict(**PLOTLY_LAYOUT_DEFAULTS["xaxis"], range=[-0.3, 8]),
    )
    return fig


def hazard_ratio_plot(cox_summary: Dict[str, Any]) -> go.Figure:
    """Forest plot of Cox model hazard ratios with 95% CI."""
    hrs = cox_summary.get("hazard_ratios", {})
    if not hrs:
        return go.Figure()

    label_map = {
        "sessions_per_day": "Sessions per Day",
        "session_frequency_bin": "Session Frequency Bin",
        "version_gate_40": "Gate 40 (vs Gate 30)",
    }

    names, centers, lowers, uppers, pvals = [], [], [], [], []
    for covariate, data in hrs.items():
        names.append(label_map.get(covariate, covariate))
        centers.append(data["hr"])
        lowers.append(data["ci_95_lower"])
        uppers.append(data["ci_95_upper"])
        pvals.append(data.get("p_value", 1.0))

    colors = [SUCCESS if c < 1 else WARNING for c in centers]

    fig = go.Figure()
    for i, (name, hr, lo, hi, pv) in enumerate(zip(names, centers, lowers, uppers, pvals)):
        sig = "p<0.001" if pv < 0.001 else f"p={pv:.3f}"
        fig.add_trace(go.Scatter(
            x=[hr],
            y=[name],
            mode="markers",
            marker=dict(size=12, color=colors[i], symbol="diamond"),
            error_x=dict(
                type="data",
                symmetric=False,
                array=[hi - hr],
                arrayminus=[hr - lo],
                color=colors[i],
                thickness=2,
                width=6,
            ),
            name=name,
            hovertemplate=(
                f"<b>{name}</b><br>"
                f"HR: {hr:.4f}<br>"
                f"95% CI: [{lo:.4f}, {hi:.4f}]<br>"
                f"{sig}<extra></extra>"
            ),
        ))

    fig.add_vline(x=1.0, line_dash="dash", line_color=TEXT_MUTED,
                  annotation_text="HR=1 (no effect)", annotation_font_color=TEXT_MUTED)
    fig = _apply_defaults(fig, "Cox Model — Hazard Ratios (95% CI)")
    fig.update_layout(
        height=300,
        xaxis_title="Hazard Ratio",
        yaxis_title="",
        showlegend=False,
        xaxis=dict(**PLOTLY_LAYOUT_DEFAULTS["xaxis"], type="log"),
    )
    return fig


def risk_group_distribution(df: pd.DataFrame) -> go.Figure:
    """Donut chart of risk group distribution."""
    counts = df["risk_group"].value_counts()
    colors = [RISK_COLORS.get(k, TEXT_SECONDARY) for k in counts.index]

    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=PLOTLY_BG, width=2)),
        textfont=dict(color=TEXT_PRIMARY, size=12),
        hovertemplate="<b>%{label}</b><br>Players: %{value:,}<br>Share: %{percent}<extra></extra>",
    ))
    fig = _apply_defaults(fig, "Player Risk Group Distribution")
    fig.update_layout(height=340, showlegend=True)
    return fig


def survival_probability_histogram(df: pd.DataFrame) -> go.Figure:
    """Histogram of survival_prob_day7 colored by risk group."""
    fig = go.Figure()
    for risk, color in RISK_COLORS.items():
        subset = df[df["risk_group"] == risk]["survival_prob_day7"]
        if len(subset) == 0:
            continue
        fig.add_trace(go.Histogram(
            x=subset,
            name=risk,
            marker_color=color,
            opacity=0.7,
            nbinsx=40,
            hovertemplate=f"<b>{risk}</b><br>P(survive): %{{x:.2f}}<br>Count: %{{y:,}}<extra></extra>",
        ))
    fig = _apply_defaults(fig, "Day 7 Survival Probability Distribution by Risk Group")
    fig.update_layout(
        height=340,
        barmode="overlay",
        xaxis_title="P(Survive Day 7)",
        yaxis_title="Players",
    )
    return fig


# ════════════════════════════════════════════════════════════════════════════
# PAGE 4 — DECISION INTELLIGENCE
# ════════════════════════════════════════════════════════════════════════════


def priority_score_distribution(df: pd.DataFrame) -> go.Figure:
    """Violin + box plot of priority scores by action_category."""
    fig = go.Figure()
    categories = df["action_category"].dropna().unique()

    for cat in categories:
        color = ACTION_COLORS.get(cat, TEXT_SECONDARY)
        subset = df[df["action_category"] == cat]["priority_score"]
        fig.add_trace(go.Violin(
            y=subset,
            name=cat,
            box_visible=True,
            meanline_visible=True,
            marker_color=color,
            line_color=color,
            fillcolor=hex_to_rgba(color, 0.2),
            hovertemplate=f"<b>{cat}</b><br>Priority Score: %{{y:.3f}}<extra></extra>",
        ))
    fig = _apply_defaults(fig, "Priority Score Distribution by Recommendation Category")
    fig.update_layout(height=380, yaxis_title="Priority Score", xaxis_title="")
    return fig


def recommendation_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of action category counts."""
    counts = df["action_category"].value_counts().reset_index()
    counts.columns = ["category", "count"]
    counts["pct"] = counts["count"] / counts["count"].sum() * 100
    counts["color"] = counts["category"].map(ACTION_COLORS).fillna(TEXT_SECONDARY)

    fig = go.Figure(go.Bar(
        x=counts["count"],
        y=counts["category"],
        orientation="h",
        marker_color=counts["color"].tolist(),
        text=[f"{p:.1f}%" for p in counts["pct"]],
        textposition="outside",
        textfont=dict(color=TEXT_SECONDARY, size=11),
        hovertemplate="<b>%{y}</b><br>Players: %{x:,}<br>Share: %{text}<extra></extra>",
    ))
    fig = _apply_defaults(fig, "Recommendation Category Distribution")
    fig.update_layout(height=320, xaxis_title="Players", yaxis_title="")
    return fig


def player_journey_sankey(df: pd.DataFrame) -> go.Figure:
    """Sankey diagram: Lifecycle Stage → Risk Group → Action Category."""
    # Build node list
    lifecycle_stages = df["lifecycle_stage"].dropna().unique().tolist()
    risk_groups = df["risk_group"].dropna().unique().tolist()
    action_cats = df["action_category"].dropna().unique().tolist()

    all_nodes = lifecycle_stages + risk_groups + action_cats
    node_idx = {n: i for i, n in enumerate(all_nodes)}

    lc_colors = [LIFECYCLE_COLORS.get(s, TEXT_SECONDARY) for s in lifecycle_stages]
    risk_colors_list = [RISK_COLORS.get(r, TEXT_SECONDARY) for r in risk_groups]
    action_colors_list = [ACTION_COLORS.get(a, TEXT_SECONDARY) for a in action_cats]
    all_colors = lc_colors + risk_colors_list + action_colors_list

    sources, targets, values, link_colors = [], [], [], []

    # Lifecycle → Risk
    for lc in lifecycle_stages:
        for rg in risk_groups:
            cnt = len(df[(df["lifecycle_stage"] == lc) & (df["risk_group"] == rg)])
            if cnt > 0:
                sources.append(node_idx[lc])
                targets.append(node_idx[rg])
                values.append(cnt)
                lc_color = LIFECYCLE_COLORS.get(lc, TEXT_SECONDARY)
                link_colors.append(hex_to_rgba(lc_color, 0.33))

    # Risk → Action
    for rg in risk_groups:
        for ac in action_cats:
            cnt = len(df[(df["risk_group"] == rg) & (df["action_category"] == ac)])
            if cnt > 0:
                sources.append(node_idx[rg])
                targets.append(node_idx[ac])
                values.append(cnt)
                rg_color = RISK_COLORS.get(rg, TEXT_SECONDARY)
                link_colors.append(hex_to_rgba(rg_color, 0.33))

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=20,
            thickness=20,
            line=dict(color=PLOTLY_BG, width=0.5),
            label=all_nodes,
            color=all_colors,
            hovertemplate="<b>%{label}</b><br>Flow: %{value:,}<extra></extra>",
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            hovertemplate="<b>%{source.label} → %{target.label}</b><br>Players: %{value:,}<extra></extra>",
        ),
    ))
    fig = _apply_defaults(fig, "Player Journey: Lifecycle → Risk → Recommendation")
    fig.update_layout(height=500, font_size=11)
    return fig


def priority_decile_chart_retention(segment_effects: Dict[str, Any]) -> go.Figure:
    """Bar chart of D7 retention lift by priority score decile."""
    dims = segment_effects.get("segmentation_dimensions", [])
    decile_dim = next((d for d in dims if d.get("column") == "priority_score_decile"), None)
    if not decile_dim:
        return go.Figure()

    decile_order = [
        "Bottom 10%", "10-20%", "20-30%", "30-40%", "40-50%",
        "50-60%", "60-70%", "70-80%", "80-90%", "Top 10%",
    ]
    records = []
    for seg_name, seg_data in decile_dim["segments"].items():
        if "retention_7" in seg_data.get("outcomes", {}):
            lift = seg_data["outcomes"]["retention_7"]["absolute_lift"]
            n = seg_data["n_control"] + seg_data["n_treatment"]
            records.append({"decile": seg_name, "lift": lift * 100, "n": n})

    if not records:
        return go.Figure()

    df_plot = pd.DataFrame(records)
    df_plot["order"] = df_plot["decile"].map(
        {d: i for i, d in enumerate(decile_order)}
    ).fillna(99)
    df_plot = df_plot.sort_values("order")

    colors = [SUCCESS if v > 0 else ERROR for v in df_plot["lift"]]

    fig = go.Figure(go.Bar(
        x=df_plot["decile"],
        y=df_plot["lift"],
        marker_color=colors,
        text=[f"{v:.2f} pp" for v in df_plot["lift"]],
        textposition="outside",
        textfont=dict(color=TEXT_SECONDARY, size=10),
        hovertemplate=(
            "<b>Decile: %{x}</b><br>"
            "D7 Lift: %{y:.3f} pp<extra></extra>"
        ),
    ))
    fig.add_hline(y=0, line_color=TEXT_MUTED, line_width=1)
    fig = _apply_defaults(fig, "D7 Retention Lift by Priority Score Decile")
    fig.update_layout(height=360, xaxis_title="Priority Score Decile", yaxis_title="Lift (pp)")
    return fig


# ════════════════════════════════════════════════════════════════════════════
# PAGE 5 — EXPERIMENT EVALUATION
# ════════════════════════════════════════════════════════════════════════════


def treatment_effect_forest_plot(
    segment_effects: Dict[str, Any],
    outcome: str = "retention_7",
    selected_dimensions: Optional[List[str]] = None,
) -> go.Figure:
    """Forest plot showing absolute lift + 95% CI per segment."""
    dims = segment_effects.get("segmentation_dimensions", [])
    if selected_dimensions:
        dims = [d for d in dims if d["dimension_name"] in selected_dimensions]

    records = []
    for dim in dims:
        for seg_name, seg_data in dim["segments"].items():
            if outcome in seg_data.get("outcomes", {}):
                out = seg_data["outcomes"][outcome]
                records.append({
                    "label": f"{seg_name}",
                    "dimension": dim["dimension_name"],
                    "lift": out["absolute_lift"] * 100,
                    "ci_lo": out["ci_lower"] * 100,
                    "ci_hi": out["ci_upper"] * 100,
                    "n": seg_data["n_control"] + seg_data["n_treatment"],
                })

    if not records:
        return go.Figure()

    df_plot = pd.DataFrame(records)
    df_plot["color"] = df_plot["lift"].apply(lambda v: SUCCESS if v > 0 else ERROR)
    df_plot["label_full"] = df_plot["dimension"].str[:12] + " | " + df_plot["label"]

    fig = go.Figure()
    for _, row in df_plot.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["lift"]],
            y=[row["label_full"]],
            mode="markers",
            marker=dict(size=10, color=row["color"], symbol="circle"),
            error_x=dict(
                type="data",
                symmetric=False,
                array=[row["ci_hi"] - row["lift"]],
                arrayminus=[row["lift"] - row["ci_lo"]],
                color=row["color"],
                thickness=2,
                width=5,
            ),
            name=row["label_full"],
            hovertemplate=(
                f"<b>{row['label']}</b> ({row['dimension']})<br>"
                f"Lift: {row['lift']:.3f} pp<br>"
                f"95% CI: [{row['ci_lo']:.3f}, {row['ci_hi']:.3f}] pp<br>"
                f"N: {row['n']:,}<extra></extra>"
            ),
        ))

    fig.add_vline(x=0, line_dash="dash", line_color=TEXT_MUTED,
                  annotation_text="No effect", annotation_font_color=TEXT_MUTED)
    fig = _apply_defaults(fig, f"Treatment Effects Forest Plot — {outcome.replace('_', ' ').title()}")
    fig.update_layout(
        height=max(400, len(df_plot) * 32 + 80),
        xaxis_title="Absolute Lift (percentage points)",
        yaxis_title="",
        showlegend=False,
    )
    return fig


def segment_comparison_chart(
    segment_effects: Dict[str, Any],
    dimension_name: str,
    outcome: str = "retention_7",
) -> go.Figure:
    """Grouped bar chart comparing control vs treatment retention by segment."""
    dims = segment_effects.get("segmentation_dimensions", [])
    dim = next((d for d in dims if d["dimension_name"] == dimension_name), None)
    if not dim:
        return go.Figure()

    segments, control_rates, treatment_rates = [], [], []
    for seg_name, seg_data in dim["segments"].items():
        if outcome in seg_data.get("outcomes", {}):
            out = seg_data["outcomes"][outcome]
            segments.append(seg_name)
            control_rates.append(out["control_rate"] * 100)
            treatment_rates.append(out["treatment_rate"] * 100)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Gate 30 (Control)",
        x=segments,
        y=control_rates,
        marker_color=EA_BLUE,
        text=[f"{v:.1f}%" for v in control_rates],
        textposition="outside",
        textfont=dict(color=TEXT_SECONDARY, size=10),
    ))
    fig.add_trace(go.Bar(
        name="Gate 40 (Treatment)",
        x=segments,
        y=treatment_rates,
        marker_color=HIGHLIGHT,
        text=[f"{v:.1f}%" for v in treatment_rates],
        textposition="outside",
        textfont=dict(color=TEXT_SECONDARY, size=10),
    ))
    fig = _apply_defaults(fig, f"{dimension_name} — Retention by Treatment Group")
    fig.update_layout(
        height=360,
        barmode="group",
        xaxis_title="",
        yaxis_title=f"{outcome.replace('_', ' ').title()} Rate (%)",
    )
    return fig


def multiple_testing_summary_chart(statistical_tests: Dict[str, Any]) -> go.Figure:
    """Scatter plot of raw vs corrected p-values for segment tests."""
    seg_tests = statistical_tests.get("segment_tests", [])
    if not seg_tests:
        return go.Figure()

    alpha = statistical_tests.get("alpha", 0.05)
    raw = [t["p_value"] for t in seg_tests]
    corrected = [t.get("p_value_corrected", t["p_value"]) for t in seg_tests]
    labels = [f"{t['dimension'][:10]}|{t['segment'][:12]}|{t['outcome']}" for t in seg_tests]
    sig = [t.get("significant", False) for t in seg_tests]
    colors = [SUCCESS if s else ERROR for s in sig]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=raw,
        y=corrected,
        mode="markers",
        marker=dict(size=8, color=colors, opacity=0.8),
        text=labels,
        hovertemplate="<b>%{text}</b><br>Raw p: %{x:.4f}<br>Corrected p: %{y:.4f}<extra></extra>",
        name="Segment tests",
    ))
    fig.add_hline(y=alpha, line_dash="dash", line_color=WARNING,
                  annotation_text=f"α={alpha}", annotation_font_color=WARNING)
    fig.add_vline(x=alpha, line_dash="dash", line_color=WARNING)
    # Diagonal reference
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(color=TEXT_MUTED, dash="dot", width=1),
        name="No correction",
        hoverinfo="skip",
    ))
    fig = _apply_defaults(fig, f"Multiple Testing: Raw vs Holm-Corrected p-values (n={len(raw)} tests)")
    fig.update_layout(
        height=380,
        xaxis_title="Raw p-value",
        yaxis_title="Corrected p-value (Holm-Bonferroni)",
        xaxis=dict(**PLOTLY_LAYOUT_DEFAULTS["xaxis"], range=[0, max(raw) * 1.05]),
        yaxis=dict(**PLOTLY_LAYOUT_DEFAULTS["yaxis"], range=[0, min(1.0, max(corrected) * 1.05)]),
    )
    return fig


# ════════════════════════════════════════════════════════════════════════════
# PAGE 6 — BUSINESS IMPACT
# ════════════════════════════════════════════════════════════════════════════


def business_impact_segment_chart(business_impact: Dict[str, Any]) -> go.Figure:
    """Ranked horizontal bar chart of segment expected retained players."""
    segs = business_impact.get("segment_impact", [])
    if not segs:
        return go.Figure()

    # Top 15 by absolute priority score
    segs_sorted = sorted(segs, key=lambda x: abs(x.get("priority_score", 0)), reverse=True)[:15]
    labels = [f"{s['dimension'][:10]}|{s['segment']}" for s in segs_sorted]
    retentions = [s.get("expected_retained_players", 0) for s in segs_sorted]
    colors = [SUCCESS if r > 0 else ERROR for r in retentions]

    fig = go.Figure(go.Bar(
        x=retentions,
        y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{r:+.0f}" for r in retentions],
        textposition="outside",
        textfont=dict(color=TEXT_SECONDARY, size=10),
        hovertemplate="<b>%{y}</b><br>Expected retained: %{x:+.1f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=TEXT_MUTED, line_width=1)
    fig = _apply_defaults(fig, "Expected Retained Players by Segment (Top 15 by Priority)")
    fig.update_layout(height=460, xaxis_title="Expected Retained Players", yaxis_title="")
    return fig


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — PIPELINE ARCHITECTURE DIAGRAM
# ════════════════════════════════════════════════════════════════════════════


def pipeline_flow_diagram() -> go.Figure:
    """Static pipeline architecture Sankey-style flow diagram."""
    phase_labels = [
        "Raw Data\n(Cookie Cats)",
        "Phase 1\nTelemetry Platform",
        "Phase 2\nSurvival Analytics",
        "Phase 3\nDecision Engine",
        "Phase 4\nCausal Experiment",
        "Executive\nRecommendation",
    ]
    colors = [TEXT_SECONDARY, EA_BLUE, INFO, WARNING, HIGHLIGHT, SUCCESS]
    x_pos = [0.05, 0.22, 0.39, 0.56, 0.73, 0.90]

    fig = go.Figure()

    # Connecting arrows (horizontal lines with arrowheads approximated)
    for i in range(len(x_pos) - 1):
        fig.add_annotation(
            x=x_pos[i + 1] - 0.01,
            y=0.5,
            ax=x_pos[i] + 0.01,
            ay=0.5,
            xref="paper", yref="paper",
            axref="paper", ayref="paper",
            arrowhead=2,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor=BORDER,
        )

    # Phase boxes
    for i, (label, color, x) in enumerate(zip(phase_labels, colors, x_pos)):
        fig.add_trace(go.Scatter(
            x=[x],
            y=[0.5],
            mode="markers+text",
            marker=dict(size=48, color=color, symbol="square", opacity=0.9,
                        line=dict(color=color, width=2)),
            text=[f"<b>{label}</b>"],
            textposition="bottom center",
            textfont=dict(color=TEXT_PRIMARY, size=10),
            hovertemplate=f"<b>{label.replace(chr(10), ' ')}</b><extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        height=220,
        paper_bgcolor=PLOTLY_PAPER_BG,
        plot_bgcolor=PLOTLY_BG,
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(visible=False, range=[0, 1]),
        margin=dict(l=10, r=10, t=10, b=60),
        font=dict(color=TEXT_PRIMARY),
        hoverlabel=dict(bgcolor="#1a1a28", bordercolor=EA_BLUE,
                        font=dict(color=TEXT_PRIMARY, size=12)),
    )
    return fig
