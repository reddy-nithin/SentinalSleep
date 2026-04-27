"""Generate synthetic placeholder WAV fixtures for Phase 0.

These files exist so that test infrastructure runs and all fixture paths
resolve. They are NOT suitable for Phase 1+ acceptance tests — real audio
must be sourced and curated before Phase 1 (see data/test_fixtures/SOURCES.md).

Run once:
    uv run python scripts/make_placeholder_fixtures.py

Idempotent — skips files that already exist unless --force is passed.
"""

from __future__ import annotations

import argparse
import struct
import wave
from pathlib import Path

import numpy as np

# Repo root is two levels above this script (scripts/make_placeholder_fixtures.py).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_FIXTURES_DIR = _PROJECT_ROOT / "data" / "test_fixtures"

# All fixtures are mono, 16kHz, 16-bit, 10 seconds.
_SAMPLE_RATE = 16_000
_DURATION_S = 10
_NUM_SAMPLES = _SAMPLE_RATE * _DURATION_S
_RNG_SEED = 42  # deterministic — same output on every run


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int = _SAMPLE_RATE) -> None:
    """Write a mono 16-bit PCM WAV file at the given path.

    Args:
        path: Destination file path.
        samples: Float32 audio in [-1, 1]; will be quantised to int16.
        sample_rate: Samples per second.
    """
    int16 = np.clip(samples, -1.0, 1.0)
    int16 = (int16 * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(int16.tobytes())


def _pink_noise(rng: np.random.Generator, n: int) -> np.ndarray:
    """Generate approximate pink noise via Voss–McCartney algorithm (simplified).

    Args:
        rng: Seeded numpy random generator.
        n: Number of samples.

    Returns:
        Float32 array of pink-ish noise, amplitude ~0.1 to avoid clipping.
    """
    num_rows = 16
    array = rng.standard_normal((num_rows, n))
    # Cumulative sum along each row simulates 1/f spectral rolloff.
    array = np.cumsum(array, axis=1)
    pink = array.sum(axis=0)
    pink -= pink.mean()
    peak = np.abs(pink).max()
    if peak > 0:
        pink = pink / peak * 0.1  # scale to low amplitude
    return pink.astype(np.float32)


def _white_noise(rng: np.random.Generator, n: int, amplitude: float = 0.05) -> np.ndarray:
    """Generate white noise at the given amplitude.

    Args:
        rng: Seeded numpy random generator.
        n: Number of samples.
        amplitude: Peak amplitude in [-1, 1].

    Returns:
        Float32 array of white noise.
    """
    return (rng.standard_normal(n) * amplitude).astype(np.float32)


def _silence(n: int, noise_floor_db: float = -60.0) -> np.ndarray:
    """Generate near-silence (a tiny noise floor to avoid completely blank files).

    Args:
        n: Number of samples.
        noise_floor_db: Noise floor relative to full scale (dBFS).

    Returns:
        Float32 array of near-silence.
    """
    amplitude = 10 ** (noise_floor_db / 20.0)
    rng = np.random.default_rng(_RNG_SEED)
    return (rng.standard_normal(n) * amplitude).astype(np.float32)


def make_fixtures(force: bool = False) -> None:
    """Generate all placeholder fixture WAVs into data/test_fixtures/.

    Args:
        force: If True, overwrite existing files. If False, skip existing.
    """
    _FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(_RNG_SEED)

    fixtures: list[tuple[str, np.ndarray]] = [
        # Phase 1 will replace with real whimpering audio.
        ("nightmare_mild.wav", _pink_noise(rng, _NUM_SAMPLES)),
        # Phase 1 will replace with real crying + heavy breathing.
        ("nightmare_severe.wav", _pink_noise(rng, _NUM_SAMPLES)),
        # Phase 1 will replace with real snoring audio.
        ("false_positive_snore.wav", _white_noise(rng, _NUM_SAMPLES)),
        # Phase 1 will replace with real traffic ambient audio.
        ("false_positive_traffic.wav", _white_noise(rng, _NUM_SAMPLES)),
        # Phase 1 may replace with self-recorded room tone.
        ("calm_sleep.wav", _silence(_NUM_SAMPLES)),
    ]

    for filename, samples in fixtures:
        dest = _FIXTURES_DIR / filename
        if dest.exists() and not force:
            print(f"  skip  {dest.name}  (already exists; use --force to overwrite)")
            continue
        _write_wav(dest, samples)
        print(f"  wrote {dest.name}  ({len(samples) / _SAMPLE_RATE:.0f}s, 16kHz mono)")


def main() -> None:
    """Entry point for the placeholder fixture generator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing fixture files.",
    )
    args = parser.parse_args()

    print(f"Generating placeholder fixtures → {_FIXTURES_DIR}")
    make_fixtures(force=args.force)
    print("Done. These are synthetic placeholders — see SOURCES.md for real sources.")


if __name__ == "__main__":
    main()
