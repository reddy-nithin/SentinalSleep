"""pydub-based two-layer audio mixer for therapeutic intervention clips.

Combines pre-generated music and soundscape WAV files into mixed intervention
clips at the volume levels specified in ``config.py``.

Two intervention profiles:

- **Mild** — music at ambient level with soundscape slightly prominent.
  Best for early-stage distress where gentle nudging suffices.

- **Severe** — music dominant, soundscape quieter.  The more structured
  musical grounding is intended for deeper nightmare states.

Both profiles are normalised to ``config.INTERVENTION_PLAYBACK_DBFS`` (-20 dBFS)
so they play as ambient background without waking the patient.

Usage::

    from sentinelsleep.generation.mixer import mix_intervention, create_mild_variant

    mix_intervention(
        music_path=Path(\"data/audio_cache/music/ambient_60bpm_low_v1.wav\"),
        soundscape_path=Path(\"data/audio_cache/soundscape/ocean_gentle_v1.wav\"),
        output_path=Path(\"data/audio_cache/mixed/intervention_mild_v1.wav\"),
        profile=\"mild\",
    )
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from pydub import AudioSegment

from sentinelsleep import config

logger = logging.getLogger(__name__)

# Type alias for mix profile selector
MixProfile = Literal["mild", "severe"]


def _load_as_mono_44k(path: Path) -> AudioSegment:
    """Load any WAV file, convert to mono 44.1 kHz 16-bit AudioSegment.

    Args:
        path: Path to source WAV file.

    Returns:
        Mono, 44.1 kHz, 16-bit AudioSegment.
    """
    seg = AudioSegment.from_wav(str(path))
    # Convert to mono if stereo
    if seg.channels > 1:
        seg = seg.set_channels(1)
    # Resample to 44.1 kHz if needed
    if seg.frame_rate != config.INTERVENTION_SAMPLE_RATE:
        seg = seg.set_frame_rate(config.INTERVENTION_SAMPLE_RATE)
    # Ensure 16-bit
    if seg.sample_width != 2:
        seg = seg.set_sample_width(2)
    return seg


def _trim_or_loop_to_duration(seg: AudioSegment, duration_ms: int) -> AudioSegment:
    """Trim or loop an AudioSegment to exactly ``duration_ms`` milliseconds.

    Args:
        seg:         Input AudioSegment.
        duration_ms: Target duration in milliseconds.

    Returns:
        AudioSegment of exactly ``duration_ms`` ms.
    """
    if len(seg) >= duration_ms:
        return seg[:duration_ms]
    # Loop until long enough, then trim.
    repeats = (duration_ms // len(seg)) + 2
    looped = seg * repeats
    return looped[:duration_ms]


def mix_intervention(
    music_path: Path,
    soundscape_path: Path,
    output_path: Path,
    profile: MixProfile = "mild",
    target_duration_s: float = float(config.INTERVENTION_DURATION_SECONDS),
) -> Path:
    """Mix music and soundscape into a single intervention WAV clip.

    Volume rules:

    - **Mild profile:** music at ``INTERVENTION_PLAYBACK_DBFS``,
      soundscape at ``INTERVENTION_PLAYBACK_DBFS + SOUNDSCAPE_RELATIVE_DBFS``
      (i.e. soundscape is louder relative to music — more nature).
    - **Severe profile:** music at ``INTERVENTION_PLAYBACK_DBFS``,
      soundscape at ``INTERVENTION_PLAYBACK_DBFS + SOUNDSCAPE_RELATIVE_DBFS``
      (soundscape is softer — music takes the grounding role).

    Both profiles normalise the final mix to ``INTERVENTION_PLAYBACK_DBFS``
    to ensure ambient-level playback.

    Args:
        music_path:       Path to source music WAV file.
        soundscape_path:  Path to source soundscape WAV file.
        output_path:      Destination WAV file path.  Parent dirs created.
        profile:          ``\"mild\"`` or ``\"severe\"`` mix profile.
        target_duration_s: Clip duration in seconds.

    Returns:
        Resolved path to the written WAV file.

    Raises:
        ValueError: If ``profile`` is not ``\"mild\"`` or ``\"severe\"``.
        FileNotFoundError: If either source path doesn't exist.
    """
    if profile not in ("mild", "severe"):
        raise ValueError(f"profile must be 'mild' or 'severe', got {profile!r}")
    for p in (music_path, soundscape_path):
        if not Path(p).exists():
            raise FileNotFoundError(f"Source audio not found: {p}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    target_ms = int(target_duration_s * 1000)

    logger.info(
        "Mixing %s → %s [profile=%s]",
        music_path.name,
        soundscape_path.name,
        profile,
    )

    music = _load_as_mono_44k(music_path)
    soundscape = _load_as_mono_44k(soundscape_path)

    music = _trim_or_loop_to_duration(music, target_ms)
    soundscape = _trim_or_loop_to_duration(soundscape, target_ms)

    # ----------------------------------------------------------------
    # Volume calibration
    # The plan specifies:
    #   - Overall playback at INTERVENTION_PLAYBACK_DBFS (-20 dBFS)
    #   - Soundscape at SOUNDSCAPE_RELATIVE_DBFS (-6 dB) relative to music
    #
    # Mild profile: nature is slightly prominent (+2 dB boost on soundscape)
    # Severe profile: music is dominant (soundscape at the standard -6 dB)
    # ----------------------------------------------------------------
    if profile == "mild":
        # Music at base level; soundscape slightly louder than standard
        soundscape_offset_db = config.SOUNDSCAPE_RELATIVE_DBFS + 2.0  # -4 dB rel
    else:  # severe
        # Music dominant; soundscape at standard -6 dB relative
        soundscape_offset_db = config.SOUNDSCAPE_RELATIVE_DBFS  # -6 dB rel

    soundscape_adjusted = soundscape.apply_gain(soundscape_offset_db)
    mixed = music.overlay(soundscape_adjusted)

    # Normalise to target playback level (-20 dBFS)
    current_dBFS = mixed.dBFS
    if current_dBFS != float("-inf"):
        gain_needed = config.INTERVENTION_PLAYBACK_DBFS - current_dBFS
        mixed = mixed.apply_gain(gain_needed)

    mixed.export(str(output_path), format="wav")
    logger.info(
        "Wrote mixed clip → %s  (%.1f s, %d Hz, profile=%s, dBFS≈%.1f)",
        output_path.name,
        len(mixed) / 1000,
        config.INTERVENTION_SAMPLE_RATE,
        profile,
        mixed.dBFS,
    )
    return output_path.resolve()


def create_mild_variant(
    music_path: Path,
    soundscape_path: Path,
    output_path: Path,
    target_duration_s: float = float(config.INTERVENTION_DURATION_SECONDS),
) -> Path:
    """Convenience wrapper: mix with the mild profile.

    Args:
        music_path:       Path to music WAV file.
        soundscape_path:  Path to soundscape WAV file.
        output_path:      Destination WAV path.
        target_duration_s: Clip duration in seconds.

    Returns:
        Resolved path to the written WAV file.
    """
    return mix_intervention(
        music_path=music_path,
        soundscape_path=soundscape_path,
        output_path=output_path,
        profile="mild",
        target_duration_s=target_duration_s,
    )


def create_severe_variant(
    music_path: Path,
    soundscape_path: Path,
    output_path: Path,
    target_duration_s: float = float(config.INTERVENTION_DURATION_SECONDS),
) -> Path:
    """Convenience wrapper: mix with the severe profile.

    Args:
        music_path:       Path to music WAV file.
        soundscape_path:  Path to soundscape WAV file.
        output_path:      Destination WAV path.
        target_duration_s: Clip duration in seconds.

    Returns:
        Resolved path to the written WAV file.
    """
    return mix_intervention(
        music_path=music_path,
        soundscape_path=soundscape_path,
        output_path=output_path,
        profile="severe",
        target_duration_s=target_duration_s,
    )


def validate_cache_clip(path: Path) -> dict[str, object]:
    """Validate that a cached clip meets Phase 3 acceptance criteria.

    Acceptance criteria (from SENTINELSLEEP_PLAN.md §7 Phase 3):
    - Duration: 60 s ± 1 s
    - Sample rate: 44 100 Hz
    - Sample width: 16-bit (2 bytes)
    - Channels: 1 (mono)

    Args:
        path: Path to a WAV file in the audio cache.

    Returns:
        Dict with keys ``{\"path\", \"duration_s\", \"frame_rate\",
        \"sample_width_bits\", \"channels\", \"valid\", \"errors\"}``.
    """
    errors: list[str] = []

    try:
        seg = AudioSegment.from_wav(str(path))
    except Exception as exc:
        return {
            "path": str(path),
            "valid": False,
            "errors": [f"Failed to load: {exc}"],
        }

    duration_s = len(seg) / 1000
    sample_width_bits = seg.sample_width * 8

    if not (59.0 <= duration_s <= 61.0):
        errors.append(f"Duration {duration_s:.2f}s not in [59, 61] s")
    if seg.frame_rate != config.INTERVENTION_SAMPLE_RATE:
        errors.append(
            f"Sample rate {seg.frame_rate} Hz ≠ {config.INTERVENTION_SAMPLE_RATE} Hz"
        )
    if seg.sample_width != 2:
        errors.append(f"Sample width {sample_width_bits}-bit, expected 16-bit")
    if seg.channels != 1:
        errors.append(f"Channels={seg.channels}, expected mono (1)")

    return {
        "path": str(path),
        "duration_s": duration_s,
        "frame_rate": seg.frame_rate,
        "sample_width_bits": sample_width_bits,
        "channels": seg.channels,
        "valid": len(errors) == 0,
        "errors": errors,
    }
