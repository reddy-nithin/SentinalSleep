"""Pre-generation cache builder for the SentinelSleep intervention layer.

This module orchestrates the one-time generation of all therapeutic audio clips
that the live pipeline will play during nightmare interventions.

Execution order (enforced to respect M2 8 GB memory budget — ADR-003):

    1. Load MusicGen → generate ``MUSIC_VARIANTS_COUNT`` music clips → unload
    2. Load AudioGen → generate ``SOUNDSCAPE_VARIANTS_COUNT`` soundscape clips → unload
    3. Mix all combinations into mild + severe intervention clips

Only one large model is resident in memory at a time.

The generated cache structure::

    data/audio_cache/
    ├── music/
    │   ├── ambient_60bpm_low_v1.wav
    │   ├── ambient_60bpm_low_v2.wav
    │   └── ambient_60bpm_low_v3.wav
    ├── soundscape/
    │   ├── ocean_gentle_v1.wav
    │   ├── rain_soft_v1.wav
    │   └── forest_night_v1.wav
    └── mixed/
        ├── intervention_mild_v1.wav   … v5.wav
        └── intervention_severe_v1.wav … v5.wav

Public API::

    from sentinelsleep.generation.pregenerate import build_cache
    build_cache()
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

from sentinelsleep import config
from sentinelsleep.generation.audiogen_wrapper import AudioGenLoadError
from sentinelsleep.generation.manifest import write_manifest as _write_manifest
from sentinelsleep.generation.mixer import create_mild_variant, create_severe_variant, validate_cache_clip

logger = logging.getLogger(__name__)

# When ``skip_mixing`` is True, only validate canonical intervention filenames
# so stray WAVs in ``mixed/`` do not fail the build.
_MIXED_INTERVENTION_RE = re.compile(r"^intervention_(mild|severe)_v[1-5]\.wav$")

# ---------------------------------------------------------------------------
# File naming helpers
# ---------------------------------------------------------------------------

# Short human-readable name tags to embed in soundscape filenames
_SOUNDSCAPE_TAGS = ["ocean_gentle", "rain_soft", "forest_night"]
_MUSIC_TAGS = ["ambient_60bpm_low", "meditative_ambient", "piano_ambient"]


def _music_filename(variant_idx: int) -> str:
    tag = _MUSIC_TAGS[variant_idx] if variant_idx < len(_MUSIC_TAGS) else f"music_v{variant_idx + 1}"
    return f"{tag}_v{variant_idx + 1}.wav"


def _soundscape_filename(variant_idx: int) -> str:
    """Return cache filename for soundscape variant ``variant_idx``.

    Each distinct tag uses ``_v1`` (per SENTINELSLEEP_PLAN.md §7 Phase 3 cache
    layout). Extra variants beyond the tag list use ``soundscape_v{N}.wav``.
    """
    if variant_idx < len(_SOUNDSCAPE_TAGS):
        tag = _SOUNDSCAPE_TAGS[variant_idx]
        return f"{tag}_v1.wav"
    return f"soundscape_v{variant_idx + 1}.wav"


def _mixed_filename(profile: str, variant_num: int) -> str:
    return f"intervention_{profile}_v{variant_num}.wav"


def _synthesize_soundscape_fallback(output_path: Path, prompt_tag: str) -> Path:
    """Write a low-amplitude band-limited pink-noise WAV as a soundscape placeholder.

    Used when AudioGen cannot load (OOM) or when ``use_synthetic_soundscape``
    is requested. Output matches intervention cache format: mono, 44.1 kHz,
    16-bit PCM, ``INTERVENTION_DURATION_SECONDS`` long. Deterministic per
    ``prompt_tag`` seed so re-runs produce identical files.

    Args:
        output_path: Destination WAV path (parent dirs created if needed).
        prompt_tag: Short label for logging / RNG seed derivation.

    Returns:
        Resolved path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sr = config.INTERVENTION_SAMPLE_RATE
    duration_s = float(config.INTERVENTION_DURATION_SECONDS)
    n_samples = int(duration_s * sr)
    seed = (hash(prompt_tag) & 0xFFFF_FFFF) or 42
    rng = np.random.default_rng(seed)

    # Approximate pink noise (Voss–McCartney style, same idea as placeholder fixtures).
    num_rows = 16
    rows = rng.standard_normal((num_rows, n_samples))
    pink = np.cumsum(rows, axis=1).sum(axis=0).astype(np.float32)
    pink -= float(pink.mean())
    peak = float(np.max(np.abs(pink))) or 1.0
    pink = (pink / peak) * 0.08

    sos = signal.butter(4, 2_000.0, btype="low", fs=float(sr), output="sos")
    pink = signal.sosfilt(sos, pink).astype(np.float32)

    sf.write(str(output_path), pink, sr, subtype="PCM_16")
    logger.info(
        "Synthetic soundscape fallback → %s (tag=%r, %.0fs, %d Hz)",
        output_path.name,
        prompt_tag,
        duration_s,
        sr,
    )
    return output_path.resolve()


# ---------------------------------------------------------------------------
# Step 1: Generate music clips
# ---------------------------------------------------------------------------


def _generate_music() -> list[Path]:
    """Load MusicGen, generate all music variants, unload, return paths.

    Returns:
        List of Paths to generated music WAV files.
    """
    from sentinelsleep.generation.musicgen_wrapper import MusicGenWrapper

    logger.info("=" * 60)
    logger.info("STEP 1 — Generating %d music variants with MusicGen", config.MUSIC_VARIANTS_COUNT)
    logger.info("=" * 60)

    gen = MusicGenWrapper()

    for i, prompt in enumerate(config.MUSIC_PROMPTS[: config.MUSIC_VARIANTS_COUNT]):
        out = config.MUSIC_CACHE_DIR / _music_filename(i)
        if out.exists():
            logger.info("  Skipping %s — already exists", out.name)
            continue
        logger.info("  [%d/%d] Prompt: %s", i + 1, config.MUSIC_VARIANTS_COUNT, prompt[:80])
        gen.generate_to_file(
            output_path=out,
            prompt=prompt,
            duration_s=float(config.INTERVENTION_DURATION_SECONDS),
        )

    gen.unload()
    ordered = [
        config.MUSIC_CACHE_DIR / _music_filename(i) for i in range(config.MUSIC_VARIANTS_COUNT)
    ]
    logger.info("Music generation complete — %d variants at %s", len(ordered), config.MUSIC_CACHE_DIR)
    return ordered


# ---------------------------------------------------------------------------
# Step 2: Generate soundscape clips
# ---------------------------------------------------------------------------


def _generate_soundscapes(*, use_synthetic: bool = False) -> tuple[list[Path], bool]:
    """Load AudioGen, generate all soundscape variants, unload, return paths.

    If ``use_synthetic`` is True, skips AudioGen and writes synthetic placeholders
    for any missing expected files (ADR-010).

    On ``AudioGenLoadError`` (e.g. OOM or audiocraft not installed), fills any missing
    files with the same synthetic fallback so mixing can complete.

    Returns:
        Tuple of (ordered list of Paths, fallback_used flag).  ``fallback_used``
        is ``True`` when synthetic pink-noise placeholders were written instead of
        real AudioGen output.
    """
    from sentinelsleep.generation.audiogen_wrapper import AudioGenWrapper

    all_expected = [
        config.SOUNDSCAPE_CACHE_DIR / _soundscape_filename(i)
        for i in range(config.SOUNDSCAPE_VARIANTS_COUNT)
    ]

    logger.info("=" * 60)
    logger.info(
        "STEP 2 — Generating %d soundscape variants (%s)",
        config.SOUNDSCAPE_VARIANTS_COUNT,
        "synthetic placeholder" if use_synthetic else "AudioGen",
    )
    logger.info("=" * 60)

    if all(p.exists() for p in all_expected):
        logger.info("All soundscape clips already cached — skipping AudioGen load")
        return all_expected, False

    if use_synthetic:
        logger.warning(
            "Using synthetic soundscape fallback (--use-synthetic-soundscape); "
            "see ADR-010."
        )
        for i, out in enumerate(all_expected):
            if out.exists():
                logger.info("  Skipping %s — already exists", out.name)
                continue
            tag = _SOUNDSCAPE_TAGS[i] if i < len(_SOUNDSCAPE_TAGS) else f"soundscape_v{i + 1}"
            _synthesize_soundscape_fallback(out, tag)
        return all_expected, True

    try:
        gen = AudioGenWrapper()
    except AudioGenLoadError as exc:
        logger.error("%s", exc)
        logger.warning(
            "AudioGen unavailable — applying synthetic soundscape fallback for "
            "missing files (ADR-010). Replace with real WAVs in %s if desired.",
            config.SOUNDSCAPE_CACHE_DIR,
        )
        for i, out in enumerate(all_expected):
            if out.exists():
                continue
            tag = _SOUNDSCAPE_TAGS[i] if i < len(_SOUNDSCAPE_TAGS) else f"soundscape_v{i + 1}"
            _synthesize_soundscape_fallback(out, tag)
        return all_expected, True

    for i, prompt in enumerate(config.SOUNDSCAPE_PROMPTS[: config.SOUNDSCAPE_VARIANTS_COUNT]):
        out = config.SOUNDSCAPE_CACHE_DIR / _soundscape_filename(i)
        if out.exists():
            logger.info("  Skipping %s — already exists", out.name)
            continue
        logger.info(
            "  [%d/%d] Prompt: %s", i + 1, config.SOUNDSCAPE_VARIANTS_COUNT, prompt[:80]
        )
        gen.generate_to_file(
            output_path=out,
            prompt=prompt,
            duration_s=float(config.INTERVENTION_DURATION_SECONDS),
        )

    gen.unload()
    logger.info("Soundscape generation complete — %d variants at %s", len(all_expected), config.SOUNDSCAPE_CACHE_DIR)
    return all_expected, False


# ---------------------------------------------------------------------------
# Step 3: Mix into mild + severe intervention clips
# ---------------------------------------------------------------------------

# Mix plan: 5 mild + 5 severe from 3×3 music×soundscape combinations.
# We use a fixed selection so the output is deterministic and human-reviewable.
#
# Pairs are (music_idx, soundscape_idx).  Music has 3 variants (0,1,2);
# soundscape has 3 variants (0,1,2).  We cycle through pairs to fill 5 slots.
_MILD_PAIRS: list[tuple[int, int]] = [(0, 0), (0, 2), (1, 1), (1, 0), (2, 2)]
_SEVERE_PAIRS: list[tuple[int, int]] = [(0, 1), (1, 2), (2, 0), (2, 1), (0, 2)]


def _mix_all(music_paths: list[Path], soundscape_paths: list[Path]) -> list[Path]:
    """Mix music and soundscape clips into intervention clips.

    Args:
        music_paths:      Ordered list of music WAV paths (index = variant idx).
        soundscape_paths: Ordered list of soundscape WAV paths.

    Returns:
        List of Paths to all mixed clips that were successfully written.
    """
    logger.info("=" * 60)
    logger.info("STEP 3 — Mixing intervention clips")
    logger.info("=" * 60)

    mixed_paths: list[Path] = []

    def _safe_mix(
        music_idx: int,
        soundscape_idx: int,
        variant_num: int,
        profile: str,
    ) -> None:
        if music_idx >= len(music_paths) or soundscape_idx >= len(soundscape_paths):
            logger.warning(
                "  Skipping %s v%d — source index out of range (music=%d, soundscape=%d)",
                profile,
                variant_num,
                music_idx,
                soundscape_idx,
            )
            return

        out = config.MIXED_CACHE_DIR / _mixed_filename(profile, variant_num)
        if out.exists():
            logger.info("  Skipping %s — already exists", out.name)
            mixed_paths.append(out)
            return

        mixer_fn = create_mild_variant if profile == "mild" else create_severe_variant
        try:
            p = mixer_fn(
                music_path=music_paths[music_idx],
                soundscape_path=soundscape_paths[soundscape_idx],
                output_path=out,
            )
            mixed_paths.append(p)
        except Exception as exc:
            logger.error("  Failed to mix %s: %s", out.name, exc)

    logger.info("  Mild variants (%d):", config.MILD_VARIANTS_COUNT)
    for num, (m_idx, s_idx) in enumerate(_MILD_PAIRS[: config.MILD_VARIANTS_COUNT], start=1):
        _safe_mix(m_idx, s_idx, num, "mild")

    logger.info("  Severe variants (%d):", config.SEVERE_VARIANTS_COUNT)
    for num, (m_idx, s_idx) in enumerate(_SEVERE_PAIRS[: config.SEVERE_VARIANTS_COUNT], start=1):
        _safe_mix(m_idx, s_idx, num, "severe")

    logger.info("Mixing complete — %d clips written", len(mixed_paths))
    return mixed_paths


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_cache(mixed_paths: list[Path]) -> bool:
    """Validate all mixed clips meet Phase 3 acceptance criteria.

    Args:
        mixed_paths: Paths to mixed intervention WAV files.

    Returns:
        ``True`` if all clips pass validation, ``False`` otherwise.
    """
    logger.info("=" * 60)
    logger.info("STEP 4 — Validating cache")
    logger.info("=" * 60)

    all_valid = True
    for path in mixed_paths:
        result = validate_cache_clip(path)
        if result["valid"]:
            logger.info(
                "  ✓ %-40s  %.1f s  %d Hz  %d-bit",
                Path(str(result["path"])).name,
                result["duration_s"],
                result["frame_rate"],
                result["sample_width_bits"],
            )
        else:
            all_valid = False
            logger.error(
                "  ✗ %-40s  INVALID: %s",
                Path(str(result["path"])).name,
                "; ".join(result["errors"]),  # type: ignore[arg-type]
            )
    return all_valid


# ---------------------------------------------------------------------------
# Cache manifest
# ---------------------------------------------------------------------------


def _print_manifest() -> None:
    """Print a summary of everything in the audio cache."""
    logger.info("=" * 60)
    logger.info("CACHE MANIFEST")
    logger.info("=" * 60)

    for label, directory in [
        ("Music", config.MUSIC_CACHE_DIR),
        ("Soundscape", config.SOUNDSCAPE_CACHE_DIR),
        ("Mixed", config.MIXED_CACHE_DIR),
    ]:
        wavs = sorted(directory.glob("*.wav"))
        logger.info("%s/  (%d files):", label.lower(), len(wavs))
        for wav in wavs:
            size_kb = wav.stat().st_size // 1024
            logger.info("    %-42s  %6d KB", wav.name, size_kb)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_cache(
    skip_music: bool = False,
    skip_soundscapes: bool = False,
    skip_mixing: bool = False,
    use_synthetic_soundscape: bool = False,
    write_manifest: bool = True,
) -> bool:
    """Build the complete therapeutic audio cache.

    Runs all three generation steps in sequence with correct memory management:

    1. MusicGen (loaded, generates music, unloaded)
    2. AudioGen (loaded, generates soundscapes, unloaded) — or synthetic fallback
    3. Mixer (CPU-only pydub; no ML model required)

    Steps can be individually skipped when re-running after a partial failure
    (e.g., if soundscapes already exist but mixing failed).

    Args:
        skip_music:       Skip Step 1 (MusicGen).
        skip_soundscapes: Skip Step 2 (AudioGen).
        skip_mixing:      Skip Step 3 (Mixer).
        use_synthetic_soundscape: If True, never load AudioGen; write synthetic
            placeholders for missing soundscapes (ADR-010).
        write_manifest:   If True (default), write ``data/audio_cache/manifest.json``
            after validation passes (ADR-013).

    Returns:
        ``True`` if all generated/cached clips pass validation, ``False`` otherwise.
    """
    # Ensure cache directories exist.
    for d in (config.MUSIC_CACHE_DIR, config.SOUNDSCAPE_CACHE_DIR, config.MIXED_CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)

    logger.info("SentinelSleep — Pre-generation Cache Builder")
    logger.info("Target: %s", config.AUDIO_CACHE_DIR)

    # Step 1 — preserve variant index order (glob order is not guaranteed).
    if skip_music:
        music_paths = [
            config.MUSIC_CACHE_DIR / _music_filename(i)
            for i in range(config.MUSIC_VARIANTS_COUNT)
        ]
        missing_music = [p for p in music_paths if not p.exists()]
        if missing_music:
            logger.error(
                "Skipping music but expected files missing: %s",
                ", ".join(p.name for p in missing_music),
            )
            return False
        logger.info("Skipping music generation — using %d cached files", len(music_paths))
    else:
        music_paths = _generate_music()

    # Step 2 — ordered paths align with ``_MILD_PAIRS`` / ``_SEVERE_PAIRS`` indices.
    soundscape_fallback: bool = False
    if skip_soundscapes:
        soundscape_paths = [
            config.SOUNDSCAPE_CACHE_DIR / _soundscape_filename(i)
            for i in range(config.SOUNDSCAPE_VARIANTS_COUNT)
        ]
        missing_sc = [p for p in soundscape_paths if not p.exists()]
        if missing_sc:
            logger.error(
                "Skipping soundscapes but expected files missing: %s",
                ", ".join(p.name for p in missing_sc),
            )
            return False
        logger.info(
            "Skipping soundscape generation — using %d cached files", len(soundscape_paths)
        )
    else:
        soundscape_paths, soundscape_fallback = _generate_soundscapes(
            use_synthetic=use_synthetic_soundscape
        )

    # Step 3
    if skip_mixing:
        mixed_paths = sorted(
            p
            for p in config.MIXED_CACHE_DIR.glob("*.wav")
            if _MIXED_INTERVENTION_RE.match(p.name)
        )
        logger.info(
            "Skipping mixing — validating %d cached intervention clip(s)",
            len(mixed_paths),
        )
    else:
        if not music_paths or not soundscape_paths:
            logger.error(
                "Cannot mix — no music (%d) or soundscape (%d) files available.",
                len(music_paths),
                len(soundscape_paths),
            )
            return False
        mixed_paths = _mix_all(music_paths, soundscape_paths)

    # Step 4 — validate and optionally write manifest.
    all_valid = _validate_cache(mixed_paths)
    _print_manifest()

    if all_valid and write_manifest:
        manifest_path = _write_manifest(
            music_paths=music_paths,
            soundscape_paths=soundscape_paths,
            mixed_paths=mixed_paths,
            mild_pairs=_MILD_PAIRS[: config.MILD_VARIANTS_COUNT],
            severe_pairs=_SEVERE_PAIRS[: config.SEVERE_VARIANTS_COUNT],
            device=config.select_device(),
            fallback_used={"music": False, "soundscape": soundscape_fallback},
        )
        logger.info("Manifest written → %s", manifest_path)

    if all_valid:
        logger.info("")
        logger.info("✓ Cache build complete — all clips valid.")
        logger.info("  Run the live pipeline: uv run python scripts/run_live.py")
    else:
        logger.error("")
        logger.error("✗ Cache build finished with validation errors.")
        logger.error("  Re-run with --skip-music / --skip-soundscapes to regenerate only failed clips.")

    return all_valid
