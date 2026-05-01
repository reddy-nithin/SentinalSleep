"""Whoop-style design tokens and helpers for the SentinelSleep dashboard."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

PALETTE: dict[str, str] = {
    "bg": "#0B0F14",
    "surface": "#141A21",
    "surface_alt": "#1C242D",
    "border": "#222D38",
    "text": "#E6EDF3",
    "text_dim": "#8B98A5",
    "accent": "#00E5A0",   # green — good / effective
    "warn": "#FFB020",     # amber — flagged
    "danger": "#FF4D6D",   # red — intervening / escalating
    "info": "#5AB1FF",     # blue — valence
    "violet": "#A78BFA",   # resolved / dominance
    "listening": "#2A3A4A",
    "flagged": "#FFB020",
    "intervening": "#00E5A0",
    "escalating": "#FF4D6D",
    "resolved": "#A78BFA",
    "awake": "#8B98A5",
}

STATE_COLORS: dict[str, str] = {
    "listening": PALETTE["listening"],
    "flagged": PALETTE["flagged"],
    "intervening": PALETTE["intervening"],
    "escalating": PALETTE["escalating"],
    "resolved": PALETTE["resolved"],
    "awake": PALETTE["awake"],
}

# Recovery score bands
RECOVERY_GREEN = (67, 100)
RECOVERY_AMBER = (34, 66)
RECOVERY_RED = (0, 33)


def recovery_color(score: int) -> str:
    if score >= RECOVERY_GREEN[0]:
        return PALETTE["accent"]
    if score >= RECOVERY_AMBER[0]:
        return PALETTE["warn"]
    return PALETTE["danger"]


def apply_global_css() -> None:
    """Inject global CSS matching the Whoop dark aesthetic."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }}

        /* Canvas */
        .stApp {{
            background-color: {PALETTE['bg']} !important;
        }}
        section[data-testid="stSidebar"] {{
            background-color: {PALETTE['surface']} !important;
            border-right: 1px solid {PALETTE['border']};
        }}

        /* Hide Streamlit chrome */
        #MainMenu, footer, header {{visibility: hidden;}}

        /* Typography */
        h1, h2, h3 {{
            font-weight: 700 !important;
            letter-spacing: -0.02em;
            color: {PALETTE['text']} !important;
        }}
        p, li, .stMarkdown {{
            color: {PALETTE['text']} !important;
        }}

        /* Cards */
        .ss-card {{
            background: {PALETTE['surface']};
            border: 1px solid {PALETTE['border']};
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 12px;
        }}
        .ss-card-alt {{
            background: {PALETTE['surface_alt']};
            border: 1px solid {PALETTE['border']};
            border-radius: 10px;
            padding: 16px 20px;
        }}

        /* KPI numbers */
        .ss-kpi-number {{
            font-size: 2.4rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            line-height: 1;
            color: {PALETTE['text']};
        }}
        .ss-kpi-label {{
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: {PALETTE['text_dim']};
            margin-top: 4px;
        }}
        .ss-kpi-delta {{
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 2px;
        }}

        /* Pill badges */
        .ss-pill {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}
        .ss-pill-green {{ background: rgba(0,229,160,0.15); color: {PALETTE['accent']}; }}
        .ss-pill-red   {{ background: rgba(255,77,109,0.15);  color: {PALETTE['danger']}; }}
        .ss-pill-amber {{ background: rgba(255,176,32,0.15);  color: {PALETTE['warn']}; }}
        .ss-pill-dim   {{ background: rgba(139,152,165,0.15); color: {PALETTE['text_dim']}; }}

        /* Dividers */
        hr, .stDivider {{ border-color: {PALETTE['border']} !important; opacity: 1 !important; }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: {PALETTE['bg']}; }}
        ::-webkit-scrollbar-thumb {{ background: {PALETTE['border']}; border-radius: 3px; }}

        /* Sidebar nav pills */
        .stSelectbox > div > div {{
            background-color: {PALETTE['surface_alt']} !important;
            border-color: {PALETTE['border']} !important;
        }}

        /* Metric override */
        [data-testid="stMetricValue"] {{
            font-weight: 700 !important;
            font-size: 1.6rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plotly_template() -> go.layout.Template:
    """Return a Plotly layout template matching the Whoop dark palette."""
    return go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=PALETTE["surface"],
            plot_bgcolor=PALETTE["surface"],
            font=dict(family="Inter, sans-serif", color=PALETTE["text"], size=12),
            title=dict(font=dict(size=14, color=PALETTE["text"], weight=700), x=0.0, xanchor="left"),
            xaxis=dict(
                gridcolor=PALETTE["border"],
                zerolinecolor=PALETTE["border"],
                tickfont=dict(color=PALETTE["text_dim"], size=11),
                linecolor=PALETTE["border"],
            ),
            yaxis=dict(
                gridcolor=PALETTE["border"],
                zerolinecolor=PALETTE["border"],
                tickfont=dict(color=PALETTE["text_dim"], size=11),
                linecolor=PALETTE["border"],
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                bordercolor=PALETTE["border"],
                font=dict(color=PALETTE["text_dim"], size=11),
            ),
            margin=dict(t=40, b=30, l=50, r=20),
            hoverlabel=dict(
                bgcolor=PALETTE["surface_alt"],
                bordercolor=PALETTE["border"],
                font=dict(color=PALETTE["text"], size=12),
            ),
        )
    )


def apply_plotly_defaults(fig: go.Figure, height: int = 320) -> go.Figure:
    """Apply the template and standard sizing to any figure."""
    fig.update_layout(template=plotly_template(), height=height)
    return fig
