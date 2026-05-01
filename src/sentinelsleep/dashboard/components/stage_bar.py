"""Horizontal stacked bar showing state durations — Whoop sleep-stages style."""

from __future__ import annotations

import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sentinelsleep.dashboard.theme import STATE_COLORS, PALETTE, apply_plotly_defaults

_STATE_ORDER = ["listening", "flagged", "intervening", "escalating", "resolved", "awake"]
_STATE_LABELS = {
    "listening": "Deep Sleep",
    "flagged": "Flagged",
    "intervening": "Intervention",
    "escalating": "Escalating",
    "resolved": "Resolved",
    "awake": "Awake",
}


def render_stage_bar(events: list[sqlite3.Row]) -> None:
    """Render a stacked horizontal bar of state durations for a single session."""
    if not events:
        st.info("No events to display.")
        return

    df = pd.DataFrame([dict(row) for row in events])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Build segments: consecutive same-state runs
    segments: list[dict] = []
    cur_state = df.iloc[0]["state"]
    start_ts = df.iloc[0]["timestamp"]

    for i in range(1, len(df)):
        if df.iloc[i]["state"] != cur_state:
            segments.append({"state": cur_state, "start": start_ts, "end": df.iloc[i]["timestamp"]})
            cur_state = df.iloc[i]["state"]
            start_ts = df.iloc[i]["timestamp"]

    segments.append({
        "state": cur_state,
        "start": start_ts,
        "end": df.iloc[-1]["timestamp"] + pd.Timedelta(seconds=2),
    })

    seg_df = pd.DataFrame(segments)
    seg_df["duration_min"] = (seg_df["end"] - seg_df["start"]).dt.total_seconds() / 60

    # Sum by state
    totals = seg_df.groupby("state")["duration_min"].sum().to_dict()
    total_min = sum(totals.values()) or 1

    fig = go.Figure()
    for state in _STATE_ORDER:
        mins = totals.get(state, 0)
        if mins == 0:
            continue
        pct = mins / total_min * 100
        fig.add_trace(go.Bar(
            x=[mins],
            y=["Night"],
            orientation="h",
            name=_STATE_LABELS.get(state, state.title()),
            marker_color=STATE_COLORS.get(state, PALETTE["text_dim"]),
            hovertemplate=f"<b>{_STATE_LABELS.get(state, state)}</b><br>{mins:.1f} min ({pct:.0f}%)<extra></extra>",
        ))

    apply_plotly_defaults(fig, height=90)
    fig.update_layout(
        barmode="stack",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(t=32, b=0, l=0, r=0),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
