"""Reusable big-number metric card widget."""

from __future__ import annotations

import streamlit as st

from sentinelsleep.dashboard.theme import PALETTE


def render_metric_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_positive: bool | None = None,
    accent_color: str | None = None,
    subtitle: str | None = None,
) -> None:
    """Render a dark card with a large metric value.

    Args:
        label:          Short all-caps label above the number.
        value:          The main metric string (e.g. "87", "3", "68%").
        delta:          Optional delta string shown below the value.
        delta_positive: True → green delta, False → red, None → dim.
        accent_color:   Override the value text color (defaults to white).
        subtitle:       Small grey text below delta.
    """
    color = accent_color or PALETTE["text"]

    if delta is not None:
        if delta_positive is True:
            delta_color = PALETTE["accent"]
            delta_icon = "▲"
        elif delta_positive is False:
            delta_color = PALETTE["danger"]
            delta_icon = "▼"
        else:
            delta_color = PALETTE["text_dim"]
            delta_icon = "—"
        delta_html = f'<div class="ss-kpi-delta" style="color:{delta_color};">{delta_icon} {delta}</div>'
    else:
        delta_html = ""

    subtitle_html = (
        f'<div style="font-size:0.72rem;color:{PALETTE["text_dim"]};margin-top:4px;">{subtitle}</div>'
        if subtitle
        else ""
    )

    st.html(
        f"""
        <div class="ss-card" style="text-align:center;">
          <div class="ss-kpi-label">{label}</div>
          <div class="ss-kpi-number" style="color:{color};">{value}</div>
          {delta_html}
          {subtitle_html}
        </div>
        """
    )
