"""Sanity tests for the dashboard theme module."""

from __future__ import annotations

import plotly.graph_objects as go

from sentinelsleep.dashboard.theme import (
    PALETTE,
    apply_plotly_defaults,
    plotly_template,
    recovery_color,
)


def test_palette_has_required_keys() -> None:
    required = {"bg", "surface", "accent", "warn", "danger", "text", "text_dim"}
    assert required <= set(PALETTE.keys())


def test_recovery_color_bands() -> None:
    assert recovery_color(100) == PALETTE["accent"]
    assert recovery_color(67) == PALETTE["accent"]
    assert recovery_color(66) == PALETTE["warn"]
    assert recovery_color(34) == PALETTE["warn"]
    assert recovery_color(33) == PALETTE["danger"]
    assert recovery_color(0) == PALETTE["danger"]


def test_plotly_template_returns_template() -> None:
    tpl = plotly_template()
    assert isinstance(tpl, go.layout.Template)


def test_apply_plotly_defaults_sets_height() -> None:
    fig = go.Figure()
    apply_plotly_defaults(fig, height=300)
    assert fig.layout.height == 300
