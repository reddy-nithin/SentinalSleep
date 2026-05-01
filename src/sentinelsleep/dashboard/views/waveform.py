"""Waveform view for the dashboard.

Renders a multi-line chart showing DSS and dimensional emotion scores over time.
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sentinelsleep import config


def render_waveform(timeseries_data: list[sqlite3.Row]) -> None:
    """Render DSS and emotion scores over time."""
    if not timeseries_data:
        st.info("No timeseries data available for this session.")
        return

    df = pd.DataFrame([dict(row) for row in timeseries_data])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    fig = go.Figure()

    # DSS Line
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["dss"],
        mode="lines", name="Distress (DSS)",
        line=dict(color="#E74C3C", width=2)
    ))

    # Valence Line
    if "valence" in df.columns and df["valence"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["valence"],
            mode="lines", name="Valence",
            line=dict(color="#3498DB", width=1, dash="dot"),
            visible="legendonly"  # hide by default to reduce clutter
        ))

    # Arousal Line
    if "arousal" in df.columns and df["arousal"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["arousal"],
            mode="lines", name="Arousal",
            line=dict(color="#F39C12", width=1, dash="dot"),
            visible="legendonly"
        ))

    # Dominance Line
    if "dominance" in df.columns and df["dominance"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["dominance"],
            mode="lines", name="Dominance",
            line=dict(color="#9B59B6", width=1, dash="dot"),
            visible="legendonly"
        ))

    # DSS Threshold line
    fig.add_hline(
        y=config.DSS_FLAG_THRESHOLD,
        line_dash="dash",
        line_color="red",
        annotation_text="Flag Threshold",
        annotation_position="bottom right"
    )

    fig.update_layout(
        title="Distress Signal and Emotion Dimensions",
        xaxis_title="Time",
        yaxis_title="Score (0.0 - 1.0)",
        yaxis_range=[0, 1.05],
        height=400,
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)
