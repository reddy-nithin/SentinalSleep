"""Night Detail page — synced DSS waveform + state ribbon in a single figure."""

from __future__ import annotations

import sqlite3

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from sentinelsleep import config
from sentinelsleep.dashboard.theme import PALETTE, STATE_COLORS, apply_plotly_defaults


_STATE_ORDER = ["listening", "flagged", "intervening", "escalating", "resolved", "awake"]


def render_night_detail(
    events: list[sqlite3.Row],
    timeseries: list[sqlite3.Row],
) -> None:
    """Render a two-subplot figure: DSS/emotion waveform on top, state ribbon below.

    The two subplots share the same x-axis so crosshair cursors are synced.

    Args:
        events:     Full event list for the session (used for state ribbon).
        timeseries: DSS + emotion dimension timeseries (from get_dss_timeseries).
    """
    st.markdown(
        f'<h2 style="margin-bottom:4px;">Night Detail</h2>'
        f'<div style="color:{PALETTE["text_dim"]};font-size:0.85rem;margin-bottom:16px;">'
        'Distress waveform and state timeline for the selected session.</div>',
        unsafe_allow_html=True,
    )

    if not timeseries:
        st.info("No timeseries data available for this session.")
        return

    ts_df = pd.DataFrame([dict(r) for r in timeseries])
    ts_df["timestamp"] = pd.to_datetime(ts_df["timestamp"])

    ev_df = pd.DataFrame([dict(r) for r in events]) if events else pd.DataFrame()
    if not ev_df.empty:
        ev_df["timestamp"] = pd.to_datetime(ev_df["timestamp"])

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.06,
    )

    # ── Top subplot: DSS + emotion dimensions ─────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=ts_df["timestamp"], y=ts_df["dss"],
            mode="lines",
            name="Distress (DSS)",
            line=dict(color=PALETTE["danger"], width=2.5),
            fill="tozeroy",
            fillcolor="rgba(255,77,109,0.12)",
            hovertemplate="<b>DSS</b>: %{y:.3f}<br>%{x}<extra></extra>",
        ),
        row=1, col=1,
    )

    if "valence" in ts_df and ts_df["valence"].notna().any():
        fig.add_trace(
            go.Scatter(
                x=ts_df["timestamp"], y=ts_df["valence"],
                mode="lines", name="Valence",
                line=dict(color=PALETTE["info"], width=1.5, dash="dot"),
                visible="legendonly",
                hovertemplate="<b>Valence</b>: %{y:.3f}<extra></extra>",
            ),
            row=1, col=1,
        )

    if "arousal" in ts_df and ts_df["arousal"].notna().any():
        fig.add_trace(
            go.Scatter(
                x=ts_df["timestamp"], y=ts_df["arousal"],
                mode="lines", name="Arousal",
                line=dict(color=PALETTE["warn"], width=1.5, dash="dot"),
                visible="legendonly",
                hovertemplate="<b>Arousal</b>: %{y:.3f}<extra></extra>",
            ),
            row=1, col=1,
        )

    if "dominance" in ts_df and ts_df["dominance"].notna().any():
        fig.add_trace(
            go.Scatter(
                x=ts_df["timestamp"], y=ts_df["dominance"],
                mode="lines", name="Dominance",
                line=dict(color=PALETTE["violet"], width=1.5, dash="dot"),
                visible="legendonly",
                hovertemplate="<b>Dominance</b>: %{y:.3f}<extra></extra>",
            ),
            row=1, col=1,
        )

    # DSS flag threshold line
    fig.add_hline(
        y=config.DSS_FLAG_THRESHOLD,
        line_dash="dash",
        line_color=PALETTE["warn"],
        line_width=1,
        opacity=0.6,
        annotation_text=f"Flag ({config.DSS_FLAG_THRESHOLD})",
        annotation_font=dict(color=PALETTE["warn"], size=10),
        annotation_position="bottom right",
        row=1, col=1,
    )

    # Intervention annotation markers
    if not ev_df.empty:
        int_events = ev_df[ev_df["state"] == "intervening"]
        for _, row in int_events.iterrows():
            # Find DSS at that timestamp (nearest)
            idx = (ts_df["timestamp"] - row["timestamp"]).abs().idxmin()
            dss_at = ts_df.loc[idx, "dss"]
            fig.add_annotation(
                x=row["timestamp"],
                y=dss_at,
                text="▶",
                showarrow=False,
                font=dict(color=PALETTE["accent"], size=14),
                hovertext="Intervention fired",
                xanchor="center",
                row=1, col=1,
            )

    # ── Bottom subplot: state ribbon ──────────────────────────────────────────
    if not ev_df.empty:
        # Build segments
        segments: list[dict] = []
        cur_state = ev_df.iloc[0]["state"]
        start_ts = ev_df.iloc[0]["timestamp"]

        for i in range(1, len(ev_df)):
            if ev_df.iloc[i]["state"] != cur_state:
                segments.append({"state": cur_state, "start": start_ts, "end": ev_df.iloc[i]["timestamp"]})
                cur_state = ev_df.iloc[i]["state"]
                start_ts = ev_df.iloc[i]["timestamp"]
        segments.append({
            "state": cur_state,
            "start": start_ts,
            "end": ev_df.iloc[-1]["timestamp"] + pd.Timedelta(seconds=2),
        })

        added_states: set[str] = set()
        for seg in segments:
            show_in_legend = seg["state"] not in added_states
            added_states.add(seg["state"])
            fig.add_trace(
                go.Bar(
                    x=[(seg["end"] - seg["start"]).total_seconds()],
                    y=["State"],
                    orientation="h",
                    base=[(seg["start"] - ev_df.iloc[0]["timestamp"]).total_seconds()],
                    name=seg["state"].title(),
                    marker_color=STATE_COLORS.get(seg["state"], PALETTE["text_dim"]),
                    showlegend=show_in_legend,
                    hovertemplate=(
                        f"<b>{seg['state'].title()}</b><br>"
                        f"{seg['start'].strftime('%H:%M:%S')} → {seg['end'].strftime('%H:%M:%S')}<extra></extra>"
                    ),
                ),
                row=2, col=1,
            )

    apply_plotly_defaults(fig, height=500)
    fig.update_layout(
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis2=dict(title="", tickformat="%H:%M"),
        yaxis=dict(title="Score", range=[0, 1.05]),
        yaxis2=dict(title="", visible=False),
        hovermode="x unified",
        margin=dict(t=36, b=30, l=50, r=20),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
