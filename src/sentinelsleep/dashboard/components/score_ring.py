"""SVG recovery score ring — Whoop-style hero metric."""

from __future__ import annotations

import sqlite3

import streamlit as st

from sentinelsleep.dashboard.theme import PALETTE, recovery_color


def compute_recovery_score(
    events: list[sqlite3.Row],
    interventions: list[sqlite3.Row],
) -> int:
    """Heuristic sleep recovery score (0–100) from session events/interventions.

    Recovery formula (heuristic, not clinically validated):
        100
        - 30 × min(1, nightmare_events / 3)
        - 20 × (1 - effective_rate)
        - 25 × min(1, escalations / 2)
        - 25 × min(1, awake_minutes / 30)

    All deductions are clamped to their max contribution so a single bad
    dimension cannot push the score below zero on its own.
    """
    if not events:
        return 0

    states = [row["state"] for row in events]
    nightmare_events = sum(1 for s in states if s in ("intervening", "escalating"))
    escalations = sum(1 for s in states if s == "escalating")
    awake_chunks = sum(1 for s in states if s == "awake")
    awake_minutes = awake_chunks * 2 / 60  # each chunk is 2s

    total_int = len(interventions)
    effective_int = sum(1 for i in interventions if i["effective"] == 1)
    effective_rate = effective_int / total_int if total_int > 0 else 1.0

    score = (
        100
        - 30 * min(1.0, nightmare_events / 3)
        - 20 * (1.0 - effective_rate)
        - 25 * min(1.0, escalations / 2)
        - 25 * min(1.0, awake_minutes / 30)
    )
    return max(0, min(100, round(score)))


def render_score_ring(score: int, label: str = "Recovery") -> None:
    """Render a circular progress ring with the recovery score inside.

    Uses inline SVG — no extra dependencies beyond Streamlit.
    """
    color = recovery_color(score)
    radius = 54
    circumference = 2 * 3.14159 * radius
    filled = circumference * score / 100
    gap = circumference - filled

    # Score band label
    if score >= 67:
        band = "Good"
    elif score >= 34:
        band = "Fair"
    else:
        band = "Low"

    svg = f"""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:12px 0;">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <!-- Track -->
        <circle cx="70" cy="70" r="{radius}"
          fill="none"
          stroke="{PALETTE['surface_alt']}"
          stroke-width="10"/>
        <!-- Progress arc — starts at top (rotate -90deg) -->
        <circle cx="70" cy="70" r="{radius}"
          fill="none"
          stroke="{color}"
          stroke-width="10"
          stroke-linecap="round"
          stroke-dasharray="{filled:.1f} {gap:.1f}"
          transform="rotate(-90 70 70)"/>
        <!-- Score number -->
        <text x="70" y="64"
          text-anchor="middle"
          font-family="Inter, sans-serif"
          font-size="30"
          font-weight="800"
          fill="{PALETTE['text']}">{score}</text>
        <!-- Band label -->
        <text x="70" y="84"
          text-anchor="middle"
          font-family="Inter, sans-serif"
          font-size="12"
          font-weight="600"
          fill="{color}">{band}</text>
      </svg>
      <div style="font-size:0.7rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:{PALETTE['text_dim']};margin-top:-4px;">{label}</div>
    </div>
    """
    st.html(svg)
