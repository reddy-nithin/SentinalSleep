"""Unit tests for ``generation.pregenerate`` helpers and ``build_cache`` skips.

No MusicGen / AudioLDM2 loads.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from sentinelsleep import config
from sentinelsleep.generation.mixer import validate_cache_clip
from sentinelsleep.generation.pregenerate import (
    _MILD_PAIRS,
    _SEVERE_PAIRS,
    _mixed_filename,
    _music_filename,
    _synthesize_soundscape_fallback,
    _soundscape_filename,
    build_cache,
)


class TestFilenameHelpers:
    """Expected naming for cache files."""

    def test_music_filenames(self) -> None:
        assert _music_filename(0) == "ambient_60bpm_low_v1.wav"
        assert _music_filename(1) == "meditative_ambient_v2.wav"
        assert _music_filename(2) == "piano_ambient_v3.wav"

    def test_soundscape_filenames(self) -> None:
        assert _soundscape_filename(0) == "ocean_gentle_v1.wav"
        assert _soundscape_filename(1) == "rain_soft_v1.wav"
        assert _soundscape_filename(2) == "forest_night_v1.wav"
        assert _soundscape_filename(3) == "soundscape_v4.wav"

    def test_mixed_filenames(self) -> None:
        assert _mixed_filename("mild", 1) == "intervention_mild_v1.wav"
        assert _mixed_filename("severe", 5) == "intervention_severe_v5.wav"


class TestMixPairs:
    """Deterministic mix pairs must index valid music/soundscape slots."""

    def test_pair_lengths(self) -> None:
        assert len(_MILD_PAIRS) == 5
        assert len(_SEVERE_PAIRS) == 5

    def test_pair_indices_in_range(self) -> None:
        for m_idx, s_idx in _MILD_PAIRS + _SEVERE_PAIRS:
            assert 0 <= m_idx < config.MUSIC_VARIANTS_COUNT
            assert 0 <= s_idx < config.SOUNDSCAPE_VARIANTS_COUNT


class TestBuildCacheSkips:
    """``build_cache`` with all skips should succeed without ML."""

    def test_all_skips_returns_true(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Isolated cache dirs with minimal valid 60s clips (no real ``data/audio_cache``)."""
        import sentinelsleep.generation.pregenerate as pre

        music_dir = tmp_path / "music"
        sc_dir = tmp_path / "soundscape"
        mx_dir = tmp_path / "mixed"
        music_dir.mkdir(parents=True)
        sc_dir.mkdir(parents=True)
        mx_dir.mkdir(parents=True)

        root = tmp_path / "audio_cache"
        monkeypatch.setattr(config, "AUDIO_CACHE_DIR", root)
        monkeypatch.setattr(config, "MUSIC_CACHE_DIR", music_dir)
        monkeypatch.setattr(config, "SOUNDSCAPE_CACHE_DIR", sc_dir)
        monkeypatch.setattr(config, "MIXED_CACHE_DIR", mx_dir)

        sr = config.INTERVENTION_SAMPLE_RATE
        dur = int(sr * float(config.INTERVENTION_DURATION_SECONDS))
        noise = (0.001 * np.random.default_rng(0).standard_normal(dur)).astype(np.float32)

        for i in range(config.MUSIC_VARIANTS_COUNT):
            sf.write(str(music_dir / pre._music_filename(i)), noise, sr, subtype="PCM_16")
        for i in range(config.SOUNDSCAPE_VARIANTS_COUNT):
            sf.write(str(sc_dir / pre._soundscape_filename(i)), noise, sr, subtype="PCM_16")

        ok = build_cache(
            skip_music=True,
            skip_soundscapes=True,
            skip_mixing=True,
            use_synthetic_soundscape=False,
        )
        assert ok is True


class TestSyntheticSoundscapeFallback:
    """Synthetic placeholder meets Phase 3 WAV constraints."""

    def test_synthetic_writes_valid_cache_clip(self, tmp_path: Path) -> None:
        out = tmp_path / "ocean_gentle_v1.wav"
        _synthesize_soundscape_fallback(out, "ocean_gentle")
        r = validate_cache_clip(out)
        assert r["valid"] is True, r["errors"]
