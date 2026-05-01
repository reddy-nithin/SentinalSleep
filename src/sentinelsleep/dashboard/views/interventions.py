"""Interventions page — card grid with DSS delta and audio playback."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from sentinelsleep import config
from sentinelsleep.dashboard.theme import PALETTE


def render_interventions_table(interventions: list[sqlite3.Row]) -> None:
    """Render a 2-column card grid of recent interventions.

    Each card shows: timestamp, DSS pre→post, effectiveness pill, clip name,
    and an inline audio player if the WAV file exists on disk.
    """
    st.markdown(
        f'<h2 style="margin-bottom:4px;">Interventions</h2>'
        f'<div style="color:{PALETTE["text_dim"]};font-size:0.85rem;margin-bottom:16px;">'
        'Recent therapeutic audio interventions and their effectiveness.</div>',
        unsafe_allow_html=True,
    )

    if not interventions:
        st.info("No interventions recorded in this timeframe.")
        return

    rows = [dict(r) for r in interventions]
    left_col, right_col = st.columns(2, gap="medium")

    for i, row in enumerate(rows):
        col = left_col if i % 2 == 0 else right_col
        with col:
            _render_card(row)


def _render_card(row: dict) -> None:
    """Render a single intervention card."""
    ts = pd.to_datetime(row["timestamp"]).strftime("%b %d — %H:%M:%S")
    pre = row.get("pre_dss") or 0.0
    post = row.get("post_dss") or 0.0
    delta = post - pre

    effective = row.get("effective")
    if effective == 1:
        pill_class = "ss-pill-green"
        pill_text = "Effective"
    elif effective == 0:
        pill_class = "ss-pill-red"
        pill_text = "Ineffective"
    else:
        pill_class = "ss-pill-dim"
        pill_text = "Pending"

    clip_name = Path(row["clip_path"]).name if row.get("clip_path") else "unknown"

    delta_color = PALETTE["accent"] if delta < 0 else PALETTE["danger"]
    delta_sign = "" if delta >= 0 else ""
    delta_str = f"{delta_sign}{delta:.2f}"

    st.html(
        f"""
        <div class="ss-card" style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <div style="font-size:0.72rem;color:{PALETTE['text_dim']};font-weight:600;
                          letter-spacing:0.06em;text-transform:uppercase;">{ts}</div>
              <div style="margin-top:8px;display:flex;align-items:center;gap:12px;">
                <div>
                  <span style="font-size:1.5rem;font-weight:800;color:{PALETTE['text']};">{pre:.2f}</span>
                  <span style="color:{PALETTE['text_dim']};margin:0 6px;">→</span>
                  <span style="font-size:1.5rem;font-weight:800;color:{PALETTE['text']};">{post:.2f}</span>
                </div>
                <div style="font-size:1rem;font-weight:700;color:{delta_color};">{delta_str}</div>
              </div>
              <div style="margin-top:8px;font-size:0.78rem;color:{PALETTE['text_dim']};">
                🎵 {clip_name}
              </div>
            </div>
            <span class="ss-pill {pill_class}">{pill_text}</span>
          </div>
        </div>
        """
    )

    # Audio player outside the HTML block so Streamlit can render it
    actual_clip = config.AUDIO_CACHE_DIR / "mixed" / clip_name
    if actual_clip.exists():
        st.audio(str(actual_clip))
    else:
        st.caption("Audio not available on disk.")
