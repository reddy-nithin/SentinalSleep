"""Timeline view for the dashboard.

Renders a horizontal bar chart showing the sequence of states throughout a session.
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st


def render_timeline(events: list[sqlite3.Row]) -> None:
    """Render a horizontal timeline of states from a list of events."""
    if not events:
        st.info("No events recorded for this session.")
        return

    # Convert to DataFrame
    df = pd.DataFrame([dict(row) for row in events])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # We need start and end times for each continuous state segment.
    # Group consecutive identical states.
    segments = []
    current_state = df.iloc[0]["state"]
    start_time = df.iloc[0]["timestamp"]

    for i in range(1, len(df)):
        if df.iloc[i]["state"] != current_state:
            segments.append({
                "State": current_state,
                "Start": start_time,
                "End": df.iloc[i]["timestamp"],
            })
            current_state = df.iloc[i]["state"]
            start_time = df.iloc[i]["timestamp"]

    # Final segment
    segments.append({
        "State": current_state,
        "Start": start_time,
        "End": df.iloc[-1]["timestamp"] + pd.Timedelta(seconds=30),  # Pad end slightly for visibility
    })

    seg_df = pd.DataFrame(segments)

    # Color mapping for states
    color_map = {
        "listening": "#2E86C1",   # Blue
        "flagged": "#F1C40F",     # Yellow
        "intervening": "#27AE60", # Green
        "escalating": "#E74C3C",  # Red
        "resolved": "#8E44AD",    # Purple
        "awake": "#BDC3C7",       # Grey
    }

    fig = px.timeline(
        seg_df,
        x_start="Start",
        x_end="End",
        y="State",
        color="State",
        color_discrete_map=color_map,
        title="Session Timeline",
        height=300,
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(showlegend=False, margin=dict(t=40, b=20, l=20, r=20))

    st.plotly_chart(fig, use_container_width=True)
