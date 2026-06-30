"""Styled table rendering helpers."""

import pandas as pd
import streamlit as st

from utils.theme import SUCCESS, WARNING, ERROR, EA_BLUE, TEXT_SECONDARY


def styled_dataframe(
    df: pd.DataFrame,
    height: int = 400,
    hide_index: bool = True,
) -> None:
    """Render a styled dataframe with dark theme."""
    st.dataframe(
        df,
        use_container_width=True,
        height=height,
        hide_index=hide_index,
    )


def segment_effects_table(segment_effects: dict, outcome: str = "retention_7") -> pd.DataFrame:
    """Build a flat DataFrame from segment_level_effects for display."""
    rows = []
    for dim in segment_effects.get("segmentation_dimensions", []):
        for seg_name, seg_data in dim["segments"].items():
            if outcome in seg_data.get("outcomes", {}):
                out = seg_data["outcomes"][outcome]
                rows.append({
                    "Dimension": dim["dimension_name"],
                    "Segment": seg_name,
                    "N (Control)": seg_data["n_control"],
                    "N (Treatment)": seg_data["n_treatment"],
                    "Control Rate": f"{out['control_rate']:.1%}",
                    "Treatment Rate": f"{out['treatment_rate']:.1%}",
                    "Abs Lift": f"{out['absolute_lift'] * 100:+.3f} pp",
                    "Rel Lift": f"{out.get('relative_lift', 0) * 100:+.1f}%",
                    "95% CI": f"[{out['ci_lower']*100:.3f}, {out['ci_upper']*100:.3f}] pp",
                })
    return pd.DataFrame(rows)


def statistical_tests_table(statistical_tests: dict) -> pd.DataFrame:
    """Build a flat DataFrame from segment_tests for display."""
    rows = []
    for t in statistical_tests.get("segment_tests", []):
        sig = t.get("significant", False)
        rows.append({
            "Dimension": t["dimension"],
            "Segment": t["segment"],
            "Outcome": t["outcome"],
            "Raw p": f"{t['p_value']:.4f}",
            "Corrected p (Holm)": f"{t.get('p_value_corrected', t['p_value']):.4f}",
            "Significant": "✓" if sig else "✗",
        })
    return pd.DataFrame(rows)


def decision_rules_table(decision_rules: dict) -> pd.DataFrame:
    """Build a flat DataFrame from decision_rules.json."""
    rows = []
    for rule in decision_rules.get("rules_audit", []):
        rows.append({
            "Priority": rule.get("priority", "—"),
            "Segment": rule.get("segment_name", "—"),
            "Condition": rule.get("condition_summary", "—"),
            "Action": rule.get("action_category", "—"),
            "Players": f"{rule.get('players_assigned', 0):,}",
            "Coverage": f"{rule.get('coverage_pct', 0):.1f}%",
        })
    return pd.DataFrame(rows)


def validation_checks_table(validation: dict) -> pd.DataFrame:
    """Build a DataFrame from experiment_validation checks."""
    rows = []
    for check in validation.get("checks_performed", []):
        rows.append({
            "Check": check.get("check", "—").replace("_", " ").title(),
            "Result": "✓ Passed" if check.get("passed", False) else "✗ Failed",
            "Details": _check_details(check),
        })
    return pd.DataFrame(rows)


def _check_details(check: dict) -> str:
    """Extract a readable detail string from a validation check dict."""
    if check.get("check") == "sample_size":
        return f"Control: {check.get('n_control', '—'):,} | Treatment: {check.get('n_treatment', '—'):,}"
    if check.get("check") == "treatment_balance":
        return f"Imbalance ratio: {check.get('imbalance_ratio', '—')}"
    if check.get("check") == "missing_data":
        cols = check.get("columns_checked", [])
        return f"Checked: {', '.join(cols)}"
    if check.get("check") == "covariate_balance":
        results = check.get("balance_results", [])
        return " | ".join(f"{r['covariate']}: SMD={r['smd']:.4f}" for r in results)
    return "—"
