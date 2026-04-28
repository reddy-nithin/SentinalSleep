"""Unit tests for ``generation.mixer`` (pydub mix + cache validation).

No ML models or large downloads required.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from sentinelsleep import config
from sentinelsleep.generation.mixer import mix_intervention, validate_cache_clip


def _write_mono_wav(
    path: Path,
    *,
    samples: int,
    sample_rate: int,
    subtype: str = "PCM_16",
    stereo: bool = False,
) -> None:
    """Write a simple tone or noise WAV for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.linspace(0, 1, samples, endpoint=False, dtype=np.float32)
    mono = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    if stereo:
        data = np.column_stack([mono, mono])
    else:
        data = mono
    sf.write(str(path), data, sample_rate, subtype=subtype)


class TestValidateCacheClip:
    """Tests for ``validate_cache_clip``."""

    def test_missing_file_invalid(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.wav"
        r = validate_cache_clip(missing)
        assert r["valid"] is False
        assert r["errors"]

    def test_wrong_sample_rate_invalid(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_sr.wav"
        _write_mono_wav(p, samples=16_000 * 2, sample_rate=16_000)
        r = validate_cache_clip(p)
        assert r["valid"] is False
        assert any("44100" in err or "Hz" in err for err in r["errors"])  # type: ignore[operator]

    def test_valid_clip_passes(self, tmp_path: Path) -> None:
        sr = config.INTERVENTION_SAMPLE_RATE
        dur_s = 60
        p = tmp_path / "good.wav"
        _write_mono_wav(p, samples=int(sr * dur_s), sample_rate=sr)
        r = validate_cache_clip(p)
        assert r["valid"] is True, r["errors"]
        assert r["duration_s"] == pytest.approx(60.0, abs=0.5)
        assert r["frame_rate"] == sr
        assert r["sample_width_bits"] == 16
        assert r["channels"] == 1


class TestMixIntervention:
    """Tests for ``mix_intervention``."""

    def test_invalid_profile_raises(self, tmp_path: Path) -> None:
        m = tmp_path / "m.wav"
        s = tmp_path / "s.wav"
        _write_mono_wav(m, samples=44_100 * 2, sample_rate=44_100)
        _write_mono_wav(s, samples=44_100 * 2, sample_rate=44_100)
        out = tmp_path / "mix.wav"
        with pytest.raises(ValueError, match="profile"):
            mix_intervention(m, s, out, profile="invalid")  # type: ignore[arg-type]

    def test_mix_produces_sixty_second_mono_44k_pcm16(self, tmp_path: Path) -> None:
        sr = config.INTERVENTION_SAMPLE_RATE
        # Short sources — mixer loops to 60s
        m = tmp_path / "music.wav"
        s = tmp_path / "scape.wav"
        _write_mono_wav(m, samples=sr * 2, sample_rate=sr)
        _write_mono_wav(s, samples=sr * 2, sample_rate=sr)
        out = tmp_path / "mixed.wav"
        mix_intervention(m, s, out, profile="mild")
        r = validate_cache_clip(out)
        assert r["valid"] is True, r["errors"]
