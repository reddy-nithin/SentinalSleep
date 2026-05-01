"""Horizontal KPI strip — a row of compact stat tiles."""

from __future__ import annotations

import streamlit as st

from sentinelsleep.dashboard.theme import PALETTE


def render_kpi_strip(kpis: list[dict]) -> None:
    """Render a horizontal row of KPI tiles.

    Each KPI dict must have:
        label (str):          short uppercase label
        value (str):          display value
        color (str, optional): accent color for the value
    """
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            color = kpi.get("color", PALETTE["text"])
            st.html(
                f"""
                <div class="ss-card-alt" style="text-align:center;">
                  <div class="ss-kpi-label">{kpi['label']}</div>
                  <div style="font-size:1.6rem;font-weight:800;color:{color};letter-spacing:-0.03em;line-height:1.2;">{kpi['value']}</div>
                </div>
                """
            )
