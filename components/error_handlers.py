"""Professional error handling components for production dashboard.

Never show Python tracebacks to users.
Always show professional placeholder cards.
"""

import streamlit as st
import traceback
import logging

logger = logging.getLogger(__name__)

def safe_chart_render(chart_func, *args, **kwargs):
    """Safely render a chart with professional error handling."""
    try:
        fig = chart_func(*args, **kwargs)
        return fig
    except Exception as e:
        logger.error(f"Chart rendering error: {str(e)}")
        return create_chart_error_placeholder(chart_func.__name__)

def safe_metric_render(metric_func, *args, **kwargs):
    """Safely render metrics with professional error handling."""
    try:
        return metric_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Metric rendering error: {str(e)}")
        return "N/A"

def create_chart_error_placeholder(chart_name: str):
    """Create professional chart error placeholder."""
    st.markdown(f"""
    <div class="chart-error-placeholder">
        <div class="error-icon">📊</div>
        <div class="error-title">Visualization Temporarily Unavailable</div>
        <div class="error-message">
            The {chart_name.replace('_', ' ').title()} chart could not be rendered due to data processing.
            <br>Analytics results remain fully available in other sections.
        </div>
        <div class="error-action">
            <button class="retry-button" onclick="window.location.reload()">Refresh Dashboard</button>
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_data_error_placeholder(section_name: str, reason: str = "Data processing in progress"):
    """Create professional data error placeholder."""
    st.markdown(f"""
    <div class="data-error-placeholder">
        <div class="error-icon">⚡</div>
        <div class="error-title">{section_name} Unavailable</div>
        <div class="error-message">
            {reason}<br>
            Please check the pipeline status or contact your analytics team.
        </div>
    </div>
    """, unsafe_allow_html=True)

def safe_page_render(page_func, *args, **kwargs):
    """Safely render entire page with error boundary."""
    try:
        return page_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Page rendering error: {str(e)}")
        st.error("⚠️ Page Loading Issue")
        st.markdown("""
        <div class="page-error">
            <h3>This page is temporarily unavailable</h3>
            <p>Our analytics team has been notified. Please try refreshing or navigate to another section.</p>
        </div>
        """, unsafe_allow_html=True)
        
def wrap_with_error_boundary(component_name: str):
    """Decorator to wrap components with error boundaries."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {component_name}: {str(e)}")
                create_chart_error_placeholder(component_name)
                return None
        return wrapper
    return decorator