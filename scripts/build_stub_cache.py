"""Build a stub audio cache for local development when Phase 3 Colab job is blocked.

Generates silent (or white-noise) WAVs at the canonical paths defined by
``generation/pregenerate.py`` and writes a valid ``manifest.json`` via
``generation.manifest.write_manifest()``.  The manifest records
``fallback_used.music = True`` and ``fallback_used.soundscape = True`` so it
is honest about being a stub.

Usage::

    # Silent WAVs (default):
    uv run python scripts/build_stub_cache.py

    # White-noise WAVs (useful for visually verifying the dashboard waveform):
    uv run python scripts/build_stub_cache.py --noise

Acceptance test::

    uv run python scripts/build_stub_cache.py
    uv run python scripts/verify_cache.py --no-sha256
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

# Ensure the src package is importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinelsleep import config
from sentinelsleep.generation.manifest import write_manifest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical filename helpers — mirrors pregenerate.py naming conventions
# ---------------------------------------------------------------------------

_MUSIC_TAGS = ["ambient_60bpm_low", "meditative_ambient", "piano_ambient"]
_SOUNDSCAPE_TAGS = ["ocean_gentle", "rain_soft", "forest_night"]

_MILD_PAIRS: list[tuple[int, int]] = [(0, 0), (0, 2), (1, 1), (1, 0), (2, 2)]
_SEVERE_PAIRS: list[tuple[int, int]] = [(0, 1), (1, 2), (2, 0), (2, 1), (0, 2)]


def _music_filename(variant_idx: int) -> str:
    """Return the canonical music WAV filename for *variant_idx*."""
    tag = _MUSIC_TAGS[variant_idx] if variant_idx < len(_MUSIC_TAGS) else f"music_v{variant_idx + 1}"
    return f"{tag}_v{variant_idx + 1}.wav"


def _soundscape_filename(variant_idx: int) -> str:
    """Return the canonical soundscape WAV filename for *variant_idx*."""
    if variant_idx < len(_SOUNDSCAPE_TAGS):
        return f"{_SOUNDSCAPE_TAGS[variant_idx]}_v1.wav"
    return f"soundscape_v{variant_idx + 1}.wav"


def _mixed_filename(profile: str, variant_num: int) -> str:
    """Return the canonical mixed-intervention WAV filename."""
    return f"intervention_{profile}_v{variant_num}.wav"


# ---------------------------------------------------------------------------
# WAV writers
# ---------------------------------------------------------------------------

def _write_wav(path: Path, *, use_noise: bool, seed: int | None = None) -> None:
    """Write a single stub WAV file (silent or white-noise) at *path*.

    The file always matches the intervention cache format:
    - Mono
    - ``config.INTERVENTION_SAMPLE_RATE`` Hz (44 100)
    - 16-bit PCM
    - ``config.INTERVENTION_DURATION_SECONDS`` s (60)

    Args:
        path:      Destination path (parent dirs created if missing).
        use_noise: If True, write low-amplitude white noise; if False, silence.
        seed:      RNG seed for reproducible noise (derived from filename by default).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    sr = config.INTERVENTION_SAMPLE_RATE
    n_samples = sr * config.INTERVENTION_DURATION_SECONDS

    if use_noise:
        rng = np.random.default_rng(seed if seed is not None else hash(path.name) & 0xFFFF_FFFF)
        data = (rng.standard_normal(n_samples) * 0.04).astype(np.float32)
    else:
        data = np.zeros(n_samples, dtype=np.float32)

    sf.write(str(path), data, sr, subtype="PCM_16")
    kind = "noise" if use_noise else "silent"
    logger.info("  wrote %-50s  (%s)", path.name, kind)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_stub_cache(*, use_noise: bool = False) -> None:
    """Build the complete stub audio cache.

    Creates directories, writes WAVs, then calls ``write_manifest`` to produce
    a valid ``manifest.json`` with ``fallback_used = {music: True, soundscape: True}``.

    Args:
        use_noise: Pass through to :func:`_write_wav`.

    Raises:
        RuntimeError: If fewer WAVs than expected are produced.
    """
    logger.info("SentinelSleep — Stub Cache Builder")
    logger.info("  noise: %s", use_noise)
    logger.info("  target: %s", config.AUDIO_CACHE_DIR)

    for d in (config.MUSIC_CACHE_DIR, config.SOUNDSCAPE_CACHE_DIR, config.MIXED_CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # Music variants
    logger.info("Music variants (%d):", config.MUSIC_VARIANTS_COUNT)
    music_paths: list[Path] = []
    for i in range(config.MUSIC_VARIANTS_COUNT):
        p = config.MUSIC_CACHE_DIR / _music_filename(i)
        if not p.exists():
            _write_wav(p, use_noise=use_noise, seed=i)
        else:
            logger.info("  skip %-50s  (exists)", p.name)
        music_paths.append(p)

    # Soundscape variants
    logger.info("Soundscape variants (%d):", config.SOUNDSCAPE_VARIANTS_COUNT)
    soundscape_paths: list[Path] = []
    for i in range(config.SOUNDSCAPE_VARIANTS_COUNT):
        p = config.SOUNDSCAPE_CACHE_DIR / _soundscape_filename(i)
        if not p.exists():
            _write_wav(p, use_noise=use_noise, seed=100 + i)
        else:
            logger.info("  skip %-50s  (exists)", p.name)
        soundscape_paths.append(p)

    # Mixed intervention clips
    mild_clip_count = config.MILD_VARIANTS_COUNT
    severe_clip_count = config.SEVERE_VARIANTS_COUNT
    logger.info("Mixed interventions (mild=%d, severe=%d):", mild_clip_count, severe_clip_count)
    mixed_paths: list[Path] = []
    for num, (m_idx, s_idx) in enumerate(_MILD_PAIRS[:mild_clip_count], start=1):
        p = config.MIXED_CACHE_DIR / _mixed_filename("mild", num)
        if not p.exists():
            _write_wav(p, use_noise=use_noise, seed=200 + num)
        else:
            logger.info("  skip %-50s  (exists)", p.name)
        mixed_paths.append(p)

    for num, (m_idx, s_idx) in enumerate(_SEVERE_PAIRS[:severe_clip_count], start=1):
        p = config.MIXED_CACHE_DIR / _mixed_filename("severe", num)
        if not p.exists():
            _write_wav(p, use_noise=use_noise, seed=300 + num)
        else:
            logger.info("  skip %-50s  (exists)", p.name)
        mixed_paths.append(p)

    total = len(music_paths) + len(soundscape_paths) + len(mixed_paths)
    expected = (
        config.MUSIC_VARIANTS_COUNT
        + config.SOUNDSCAPE_VARIANTS_COUNT
        + config.MILD_VARIANTS_COUNT
        + config.SEVERE_VARIANTS_COUNT
    )
    if total != expected:
        raise RuntimeError(
            f"Expected {expected} WAVs total, produced {total}. Check cache dirs."
        )

    # Write manifest
    manifest_path = write_manifest(
        music_paths=music_paths,
        soundscape_paths=soundscape_paths,
        mixed_paths=mixed_paths,
        mild_pairs=_MILD_PAIRS[:mild_clip_count],
        severe_pairs=_SEVERE_PAIRS[:severe_clip_count],
        device="cpu",
        fallback_used={"music": True, "soundscape": True},
    )

    logger.info("")
    logger.info("✓ Stub cache complete — %d WAVs + manifest", total)
    logger.info("  manifest: %s", manifest_path)
    logger.info("  Verify: uv run python scripts/verify_cache.py --no-sha256")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build a stub audio cache (silent or white-noise WAVs) for local dev."
    )
    parser.add_argument(
        "--noise",
        action="store_true",
        help="Write low-amplitude white-noise WAVs instead of silence.",
    )
    args = parser.parse_args()
    build_stub_cache(use_noise=args.noise)


if __name__ == "__main__":
    main()
