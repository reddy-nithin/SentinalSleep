"""Trends view for the dashboard.

Displays 7-day rolling aggregates.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_trends(trends: dict[str, Any]) -> None:
    """Render top-level metrics."""
    st.subheader(f"{trends['window_days']}-Day Trends")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Sessions",
            value=trends["total_sessions"]
        )
        
    with col2:
        st.metric(
            label="Total Interventions",
            value=trends["total_interventions"]
        )
        
    with col3:
        st.metric(
            label="Intervention Effectiveness",
            value=f"{trends['effective_rate_percent']:.1f}%",
            help="Percentage of interventions that successfully reduced DSS below threshold."
        )
