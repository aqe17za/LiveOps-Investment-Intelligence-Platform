"""Premium UI components for enterprise analytics dashboard.

All components follow AAA game studio design standards.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
import plotly.graph_objects as go

def metric_card_premium(
    title: str,
    value: str, 
    subtitle: str = "",
    trend: str = "",
    trend_positive: bool = True,
    icon: str = "📊",
    color: str = "blue"
) -> None:
    """Premium KPI metric card like PowerBI/Tableau."""
    
    trend_class = "trend-positive" if trend_positive else "trend-negative"
    trend_html = f'<div class="metric-trend {trend_class}">{trend}</div>' if trend else ""
    subtitle_html = f'<div class="metric-subtitle">{subtitle}</div>' if subtitle else ""
    
    color_map = {
        "blue": "metric-blue",
        "green": "metric-green", 
        "amber": "metric-amber",
        "red": "metric-red",
        "gray": "metric-gray"
    }
    color_class = color_map.get(color, "metric-blue")
    
    st.markdown(f"""
    <div class="metric-card-premium {color_class}">
        <div class="metric-header">
            <div class="metric-icon">{icon}</div>
            <div class="metric-title">{title}</div>
        </div>
        <div class="metric-value-large">{value}</div>
        {subtitle_html}
        {trend_html}
    </div>
    """, unsafe_allow_html=True)

def section_card(title: str, content: str, icon: str = "", collapsible: bool = False) -> None:
    """Premium section card container."""
    icon_html = f'<span class="section-icon">{icon}</span>' if icon else ""
    
    if collapsible:
        with st.expander(f"{icon_html} {title}", expanded=True):
            st.markdown(f'<div class="section-content">{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="section-card">
            <div class="section-header">
                {icon_html}
                <h3>{title}</h3>
            </div>
            <div class="section-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)

def page_header_premium(
    title: str, 
    subtitle: str = "",
    status: str = "ACTIVE",
    breadcrumb: List[str] = None
) -> None:
    """Premium page header like enterprise dashboards."""
    
    status_colors = {
        "ACTIVE": "status-green",
        "LOADING": "status-amber", 
        "ERROR": "status-red",
        "INACTIVE": "status-gray"
    }
    status_class = status_colors.get(status, "status-gray")
    
    breadcrumb_html = ""
    if breadcrumb:
        breadcrumb_items = []
        for i, item in enumerate(breadcrumb):
            if i == len(breadcrumb) - 1:
                breadcrumb_items.append(f'<span class="breadcrumb-current">{item}</span>')
            else:
                breadcrumb_items.append(f'<span class="breadcrumb-item">{item}</span>')
        breadcrumb_html = f'<div class="breadcrumb">{"".join(breadcrumb_items)}</div>'
    
    subtitle_html = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    
    st.markdown(f"""
    <div class="page-header-premium">
        {breadcrumb_html}
        <div class="page-title-section">
            <h1 class="page-title">{title}</h1>
            <div class="page-status {status_class}">{status}</div>
        </div>
        {subtitle_html}
    </div>
    """, unsafe_allow_html=True)

def chart_container_premium(
    title: str,
    chart_func,
    subtitle: str = "",
    download_data: Any = None,
    chart_args: tuple = (),
    chart_kwargs: dict = {}
) -> None:
    """Premium chart container with download options."""
    
    subtitle_html = f'<div class="chart-subtitle">{subtitle}</div>' if subtitle else ""
    
    # Chart header with download buttons
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"""
        <div class="chart-header">
            <h4 class="chart-title">{title}</h4>
            {subtitle_html}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if download_data is not None:
            download_buttons_html = f"""
            <div class="download-section">
                <button class="download-btn" title="Download PNG">📥 PNG</button>
                <button class="download-btn" title="Download Data">📊 CSV</button>
            </div>
            """
            st.markdown(download_buttons_html, unsafe_allow_html=True)
    
    # Chart content with error handling
    try:
        if chart_func and callable(chart_func):
            fig = chart_func(*chart_args, **chart_kwargs)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['select2d', 'lasso2d']
                })
        else:
            st.markdown("""
            <div class="chart-placeholder">
                <div class="placeholder-icon">📊</div>
                <div class="placeholder-text">Chart will appear here</div>
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f"""
        <div class="chart-error-card">
            <div class="error-icon">⚠️</div>
            <div class="error-title">Visualization Unavailable</div>
            <div class="error-message">Chart rendering temporarily disabled. Data remains available.</div>
        </div>
        """, unsafe_allow_html=True)

def executive_banner(
    decision: str,
    confidence: str,
    summary: str,
    impact: str = ""
) -> None:
    """Executive decision banner like C-suite dashboards."""
    
    decision_colors = {
        "DEPLOY GLOBALLY": ("deploy-banner", "✅"),
        "DO NOT DEPLOY": ("no-deploy-banner", "🚫"), 
        "TARGETED DEPLOYMENT": ("targeted-banner", "🎯"),
        "MORE DATA NEEDED": ("pending-banner", "📊")
    }
    
    banner_class, icon = decision_colors.get(decision, ("pending-banner", "❓"))
    
    impact_html = f'<div class="banner-impact">{impact}</div>' if impact else ""
    
    st.markdown(f"""
    <div class="executive-banner {banner_class}">
        <div class="banner-header">
            <div class="banner-icon">{icon}</div>
            <div class="banner-title">{decision}</div>
            <div class="banner-confidence">Confidence: {confidence}</div>
        </div>
        <div class="banner-summary">{summary}</div>
        {impact_html}
    </div>
    """, unsafe_allow_html=True)

def navigation_progress(steps: List[str], current_step: int) -> None:
    """Progress navigation like enterprise tools."""
    
    steps_html = []
    for i, step in enumerate(steps):
        if i < current_step:
            steps_html.append(f'<div class="nav-step completed">{i+1}</div>')
            steps_html.append(f'<div class="nav-label completed">{step}</div>')
        elif i == current_step:
            steps_html.append(f'<div class="nav-step current">{i+1}</div>')
            steps_html.append(f'<div class="nav-label current">{step}</div>')
        else:
            steps_html.append(f'<div class="nav-step upcoming">{i+1}</div>')
            steps_html.append(f'<div class="nav-label upcoming">{step}</div>')
        
        if i < len(steps) - 1:
            steps_html.append('<div class="nav-connector">→</div>')
    
    st.markdown(f"""
    <div class="navigation-progress">
        {''.join(steps_html)}
    </div>
    """, unsafe_allow_html=True)

def data_table_premium(df, title: str = "", max_rows: int = 10) -> None:
    """Premium data table with search and export."""
    
    if title:
        st.markdown(f'<h4 class="table-title">{title}</h4>', unsafe_allow_html=True)
    
    # Table controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 Search", placeholder="Filter data...", key=f"search_{title}")
    with col2:
        show_all = st.checkbox("Show all rows", key=f"showall_{title}")
    with col3:
        st.download_button(
            label="📥 Download CSV",
            data=df.to_csv(index=False),
            file_name=f"{title.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )
    
    # Filter data
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        df = df[mask]
    
    # Display table
    if not show_all:
        df = df.head(max_rows)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(400, (len(df) + 1) * 35)
    )

def status_indicator(status: str, label: str = "") -> str:
    """Generate status indicator HTML."""
    status_map = {
        "success": ("🟢", "status-success"),
        "warning": ("🟡", "status-warning"),
        "error": ("🔴", "status-error"),
        "info": ("🔵", "status-info"),
        "inactive": ("⚪", "status-inactive")
    }
    
    icon, class_name = status_map.get(status, ("⚪", "status-inactive"))
    label_text = f" {label}" if label else ""
    
    return f'<span class="status-indicator {class_name}">{icon}{label_text}</span>'