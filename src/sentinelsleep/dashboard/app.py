"""SentinelSleep Morning Dashboard — Whoop-style dark UI entry point."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import streamlit as st

from sentinelsleep.dashboard import queries
from sentinelsleep.dashboard.theme import PALETTE, apply_global_css
from sentinelsleep.dashboard.views.interventions import render_interventions_table
from sentinelsleep.dashboard.views.night_detail import render_night_detail
from sentinelsleep.dashboard.views.overview import render_overview
from sentinelsleep.dashboard.views.trends import render_trends


def main() -> None:
    st.set_page_config(
        page_title="SentinelSleep",
        page_icon="🌙",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_css()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding:8px 0 20px 0;">
              <div style="font-size:1.2rem;font-weight:800;color:{PALETTE['text']};letter-spacing:-0.02em;">
                🌙 SentinelSleep
              </div>
              <div style="font-size:0.72rem;color:{PALETTE['text_dim']};margin-top:2px;">
                PTSD Nightmare Monitoring
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Navigate",
            ["Overview", "Night Detail", "Interventions", "Trends"],
            label_visibility="collapsed",
        )

        st.divider()

        sessions = queries.get_sessions()
        if not sessions:
            st.info("No data. Run the simulation or seed synthetic events first.")
            st.code("uv run python scripts/seed_synthetic_events.py")
            return

        session_opts = {
            s["id"]: f"{str(s['started_at'])[:10]}  (#{s['id']})"
            for s in sessions
        }
        selected_id = st.selectbox(
            "Night",
            options=list(session_opts.keys()),
            format_func=lambda x: session_opts[x],
        )

        st.divider()
        trends_data = queries.get_trends(window_days=7)
        st.markdown(
            '<div class="ss-kpi-label">7-DAY SUMMARY</div>',
            unsafe_allow_html=True,
        )
        st.metric("Sessions", trends_data["total_sessions"])
        st.metric("Interventions", trends_data["total_interventions"])
        st.metric("Effectiveness", f"{trends_data['effective_rate_percent']:.0f}%")

    if selected_id is None:
        return

    # ── Per-session data ──────────────────────────────────────────────────────
    events = queries.get_events_for_session(selected_id)
    timeseries = queries.get_dss_timeseries(selected_id)
    interventions = queries.get_interventions(window_days=90)
    # Filter interventions to the selected session
    session_interventions = [i for i in interventions if i["session_id"] == selected_id]

    session_label = session_opts[selected_id]

    # ── Page routing ──────────────────────────────────────────────────────────
    if page == "Overview":
        render_overview(
            events=events,
            interventions=session_interventions,
            session_label=session_label,
            all_sessions=sessions,
            trends=trends_data,
        )

    elif page == "Night Detail":
        render_night_detail(events=events, timeseries=timeseries)

    elif page == "Interventions":
        render_interventions_table(session_interventions)

    elif page == "Trends":
        render_trends(trends_data)


if __name__ == "__main__":
    main()
