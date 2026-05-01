"""Streamlit application entry point for the SentinelSleep Morning Dashboard.

Displays views based on read-only SQLite queries.
"""

import sys
from pathlib import Path

# Ensure src is in path so 'sentinelsleep' can be imported by the app when run via streamlit
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit as st

from sentinelsleep.dashboard import queries
from sentinelsleep.dashboard.views.interventions import render_interventions_table
from sentinelsleep.dashboard.views.timeline import render_timeline
from sentinelsleep.dashboard.views.trends import render_trends
from sentinelsleep.dashboard.views.waveform import render_waveform


def main() -> None:
    st.set_page_config(
        page_title="SentinelSleep Dashboard",
        page_icon="🌙",
        layout="wide",
    )

    st.title("SentinelSleep Morning Dashboard")
    st.markdown("Review nighttime events, distress scores, and intervention effectiveness.")

    # Sidebar: Session selection
    st.sidebar.header("Navigation")
    sessions = queries.get_sessions()
    
    if not sessions:
        st.info("No data available. Run the live pipeline or seed synthetic events first.")
        return

    session_opts = {s["id"]: f"Session {s['id']} ({str(s['started_at'])[:10]})" for s in sessions}
    selected_session_id = st.sidebar.selectbox(
        "Select Session",
        options=list(session_opts.keys()),
        format_func=lambda x: session_opts[x]
    )

    # Sidebar: Global trends
    st.sidebar.divider()
    trends = queries.get_trends(window_days=7)
    render_trends(trends)

    if selected_session_id is not None:
        # Fetch data for selected session
        events = queries.get_events_for_session(selected_session_id)
        timeseries = queries.get_dss_timeseries(selected_session_id)
        
        # We also want to show recent interventions globally (or just for this session)
        # We'll show global recent interventions at the bottom
        recent_interventions = queries.get_interventions(window_days=7)

        # Render Main Views
        st.header(f"Session Details: {session_opts[selected_session_id]}")
        
        # 1. Timeline View
        render_timeline(events)
        
        st.divider()
        
        # 2. Waveform View
        render_waveform(timeseries)
        
        st.divider()
        
        # 3. Interventions View
        render_interventions_table(recent_interventions)


if __name__ == "__main__":
    main()
