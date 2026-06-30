"""Cache management utilities."""

import streamlit as st


def clear_all_caches() -> None:
    """Clear all Streamlit data caches. Use sparingly (forces full reload)."""
    st.cache_data.clear()


def get_cache_info() -> dict:
    """Return basic cache metadata for display in Configuration page."""
    return {
        "strategy": "st.cache_data with TTL=3600s",
        "scope": "All artifact loaders + master_player_df",
        "invalidation": "Automatic on TTL expiry or manual clear",
    }
