"""Unit tests for the Phase 4 clip selector."""

from __future__ import annotations

import pytest

from sentinelsleep import config
from sentinelsleep.generation.clip_selector import select_clip


@pytest.fixture
def mock_manifest():
    return {
        "mixed": [
            {"profile": "mild", "path": "mixed/intervention_mild_v1.wav"},
            {"profile": "mild", "path": "mixed/intervention_mild_v2.wav"},
            {"profile": "severe", "path": "mixed/intervention_severe_v1.wav"},
        ]
    }


def test_select_clip_mild(mock_manifest):
    path = select_clip(mock_manifest, profile="mild", rng_seed=42)
    assert path.is_absolute()
    assert str(path).startswith(str(config.AUDIO_CACHE_DIR))
    assert "intervention_mild" in path.name


def test_select_clip_severe(mock_manifest):
    path = select_clip(mock_manifest, profile="severe", rng_seed=42)
    assert path.name == "intervention_severe_v1.wav"


def test_select_clip_invalid_profile(mock_manifest):
    with pytest.raises(ValueError):
        select_clip(mock_manifest, profile="invalid", rng_seed=42) # type: ignore


def test_select_clip_empty_manifest():
    with pytest.raises(RuntimeError, match="No 'mild' clips found"):
        select_clip({}, profile="mild", rng_seed=42)
