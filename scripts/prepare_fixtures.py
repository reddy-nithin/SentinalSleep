"""Prepare real audio fixtures for Phase 1 integration testing.

Converts all raw source audio in data/test_fixtures/ to 16 kHz mono WAV files
that the AST classifier and integration tests expect.

Processing steps:
  1. Resample nightmare_mild.wav (48kHz stereo → 16kHz mono)
  2. Resample false_positive_snore.wav (48kHz stereo → 16kHz mono)
  3. Resample false_positive_traffic.wav (48kHz stereo → 16kHz mono)
  4. Build nightmare_severe.wav by mixing:
       sobbing.mp3  (crying, primary layer)
       panic attack from nightmare.wav  (heavy breathing / panic, secondary layer)
     Output: 16kHz mono, padded/looped to ~30 seconds
  5. Keep calm_sleep.wav as-is (already 16kHz mono from Phase 0)
  6. Remove .synthetic marker so integration tests stop being skipped
  7. Clean up raw source files (sobbing.mp3, panic attack from nightmare.wav)

Run with:
    uv run python scripts/prepare_fixtures.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT_ROOT / "data" / "test_fixtures"
SYNTHETIC_MARKER = FIXTURES / ".synthetic"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("prepare_fixtures")

TARGET_SR = 16_000  # Hz — what MIT AST and audeering wav2vec2 expect
TARGET_DTYPE = "float32"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_any(path: Path, target_sr: int = TARGET_SR) -> np.ndarray:
    """Load an audio file (WAV or MP3), resample to target_sr, return mono float32."""
    log.info("Loading  %s", path.name)
    audio, sr = librosa.load(str(path), sr=target_sr, mono=True, dtype=np.float32)
    log.info("  → %.2f s at %d Hz (original file loaded via librosa)", len(audio) / target_sr, target_sr)
    return audio


def save_wav(audio: np.ndarray, path: Path, sr: int = TARGET_SR) -> None:
    """Write audio array to 16-bit PCM WAV at the given path."""
    sf.write(str(path), audio, sr, subtype="PCM_16")
    duration = len(audio) / sr
    log.info("Wrote    %s  (%.2f s, %d Hz, mono, PCM_16)", path.name, duration, sr)


def pad_or_loop_to(audio: np.ndarray, target_samples: int) -> np.ndarray:
    """Extend audio to target_samples by looping, or trim if already longer."""
    if len(audio) >= target_samples:
        return audio[:target_samples]
    repeats = (target_samples // len(audio)) + 1
    return np.tile(audio, repeats)[:target_samples]


def mix_layers(primary: np.ndarray, secondary: np.ndarray, secondary_gain: float = 0.6) -> np.ndarray:
    """Mix two mono arrays together.

    Both are normalised before mixing so no single source dominates.
    secondary_gain: volume scale for the secondary layer (0–1).
    """
    target_len = max(len(primary), len(secondary))
    primary = pad_or_loop_to(primary, target_len)
    secondary = pad_or_loop_to(secondary, target_len)

    # Normalise each layer to peak ≈ 0.7 before mixing
    def _normalise(a: np.ndarray, peak: float = 0.7) -> np.ndarray:
        m = np.max(np.abs(a))
        return a * (peak / m) if m > 1e-6 else a

    primary = _normalise(primary)
    secondary = _normalise(secondary) * secondary_gain

    mixed = primary + secondary
    # Prevent clipping
    m = np.max(np.abs(mixed))
    if m > 0.95:
        mixed = mixed * (0.95 / m)
    return mixed.astype(np.float32)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== SentinelSleep fixture preparation ===")
    log.info("Fixtures directory: %s", FIXTURES)

    errors: list[str] = []

    # ------------------------------------------------------------------
    # 1. nightmare_mild.wav — resample from 48kHz stereo to 16kHz mono
    # ------------------------------------------------------------------
    src = FIXTURES / "nightmare_mild.wav"
    if src.exists():
        audio = load_any(src)
        save_wav(audio, FIXTURES / "nightmare_mild.wav")
    else:
        errors.append("nightmare_mild.wav not found — skipped")
        log.warning("nightmare_mild.wav not found")

    # ------------------------------------------------------------------
    # 2. false_positive_snore.wav
    # ------------------------------------------------------------------
    src = FIXTURES / "false_positive_snore.wav"
    if src.exists():
        audio = load_any(src)
        save_wav(audio, FIXTURES / "false_positive_snore.wav")
    else:
        errors.append("false_positive_snore.wav not found — skipped")
        log.warning("false_positive_snore.wav not found")

    # ------------------------------------------------------------------
    # 3. false_positive_traffic.wav
    # ------------------------------------------------------------------
    src = FIXTURES / "false_positive_traffic.wav"
    if src.exists():
        audio = load_any(src)
        save_wav(audio, FIXTURES / "false_positive_traffic.wav")
    else:
        errors.append("false_positive_traffic.wav not found — skipped")
        log.warning("false_positive_traffic.wav not found")

    # ------------------------------------------------------------------
    # 4. nightmare_severe.wav — mix sobbing + panic attack
    # ------------------------------------------------------------------
    # Accept sobbing as either .mp3 or .wav (macOS may auto-convert)
    sobbing_path = next(
        (FIXTURES / f for f in ["sobbing.mp3", "sobbing.wav"] if (FIXTURES / f).exists()),
        None,
    )
    panic_path = FIXTURES / "panic attack from nightmare.wav"

    if sobbing_path is not None and panic_path.exists():
        log.info("Building nightmare_severe.wav from two source clips…")
        sobbing = load_any(sobbing_path)
        panic = load_any(panic_path)

        # Target 30 seconds — long enough for the verification layer (needs 15s)
        target_samples = TARGET_SR * 30
        severe = mix_layers(sobbing, panic, secondary_gain=0.65)
        severe = pad_or_loop_to(severe, target_samples)
        save_wav(severe, FIXTURES / "nightmare_severe.wav")
    else:
        missing = []
        if sobbing_path is None:
            missing.append("sobbing.mp3 / sobbing.wav")
        if not panic_path.exists():
            missing.append(panic_path.name)
        msg = f"Cannot build nightmare_severe.wav — missing: {missing}"
        errors.append(msg)
        log.error(msg)

    # ------------------------------------------------------------------
    # 5. calm_sleep.wav — already 16kHz mono, nothing to do
    # ------------------------------------------------------------------
    calm = FIXTURES / "calm_sleep.wav"
    if calm.exists():
        info = sf.info(str(calm))
        log.info("calm_sleep.wav already %d Hz mono (%.2f s) — keeping as-is", info.samplerate, info.duration)
    else:
        errors.append("calm_sleep.wav not found")
        log.error("calm_sleep.wav not found")

    # ------------------------------------------------------------------
    # 6. Remove .synthetic marker
    # ------------------------------------------------------------------
    if SYNTHETIC_MARKER.exists():
        SYNTHETIC_MARKER.unlink()
        log.info("Removed  .synthetic marker — integration tests will now run")
    else:
        log.info(".synthetic marker already absent")

    # ------------------------------------------------------------------
    # 7. Clean up raw source files
    # ------------------------------------------------------------------
    raws_to_clean = [
        FIXTURES / "sobbing.mp3",
        FIXTURES / "sobbing.wav",
        FIXTURES / "panic attack from nightmare.wav",
    ]
    for raw in raws_to_clean:
        if raw.exists():
            raw.unlink()
            log.info("Deleted  %s (raw source, no longer needed)", raw.name)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log.info("")
    log.info("=== Fixture preparation complete ===")

    final_wavs = sorted(FIXTURES.glob("*.wav"))
    log.info("Final fixture files:")
    for wav in final_wavs:
        info = sf.info(str(wav))
        log.info(
            "  %-35s  %5d Hz  %dch  %.1f s",
            wav.name,
            info.samplerate,
            info.channels,
            info.duration,
        )

    if errors:
        log.error("")
        log.error("Errors encountered:")
        for e in errors:
            log.error("  • %s", e)
        sys.exit(1)
    else:
        log.info("")
        log.info("All fixtures ready. Run integration tests with:")
        log.info("  uv run pytest tests/ --integration -v")


if __name__ == "__main__":
    main()
