"""Interventions list view for the dashboard.

Displays a table of recent interventions with embedded audio playback.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from sentinelsleep import config


def render_interventions_table(interventions: list[sqlite3.Row]) -> None:
    """Render a table of interventions with audio playback widgets."""
    if not interventions:
        st.info("No interventions recorded in this timeframe.")
        return

    st.subheader(f"Recent Interventions ({len(interventions)})")

    # Display as a list of expandable cards rather than a raw table,
    # because we need to embed audio widgets which Streamlit dataframes don't support well natively.
    for row in interventions:
        ts = pd.to_datetime(row["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        pre = row["pre_dss"] or 0.0
        post = row["post_dss"] or 0.0
        
        if row["effective"] == 1:
            eff_badge = "✅ Effective"
        elif row["effective"] == 0:
            eff_badge = "❌ Ineffective"
        else:
            eff_badge = "⏳ Unknown"

        clip_name = Path(row["clip_path"]).name if row["clip_path"] else "Unknown"

        with st.expander(f"{ts} — DSS {pre:.2f} → {post:.2f}  ({eff_badge})"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**Clip:** {clip_name}")
                st.write(f"**Session ID:** {row['session_id']}")
            
            with col2:
                # Resolve clip path relative to audio cache if needed
                abs_clip = Path(row["clip_path"])
                if not abs_clip.is_absolute():
                    # For synthetic data, it might be an absolute path already or relative
                    pass
                
                # Check actual cache
                actual_clip = config.AUDIO_CACHE_DIR / "mixed" / clip_name
                if actual_clip.exists():
                    st.audio(str(actual_clip))
                else:
                    st.warning("Audio file not found on disk.")
