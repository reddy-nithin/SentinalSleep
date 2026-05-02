"""
Generate demo therapeutic audio clips for the SentinelSleep dashboard.

Outputs:
  web/public/audio/calm_ocean_waves.wav   — pink noise with wave-surge LFO
  web/public/audio/forest_rain_ambient.wav — brown noise with rain tremolo

Run: uv run python scripts/generate_demo_audio.py
"""

import struct
import wave
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

SAMPLE_RATE = 44100
DURATION = 30  # seconds
FADE_DURATION = 2  # seconds fade-out
TARGET_DBFS = -18.0
OUT_DIR = Path(__file__).parent.parent / "web" / "public" / "audio"


def _normalize(sig: np.ndarray, target_dbfs: float) -> np.ndarray:
    peak = np.max(np.abs(sig))
    if peak == 0:
        return sig
    target_amp = 10 ** (target_dbfs / 20)
    return sig * (target_amp / peak)


def _apply_fade_out(sig: np.ndarray, sr: int, fade_sec: float) -> np.ndarray:
    n_fade = int(sr * fade_sec)
    fade = np.linspace(1.0, 0.0, n_fade)
    out = sig.copy()
    out[-n_fade:] *= fade
    return out


def _write_stereo_wav(path: Path, left: np.ndarray, right: np.ndarray, sr: int) -> None:
    pcm_l = np.clip(left, -1.0, 1.0)
    pcm_r = np.clip(right, -1.0, 1.0)
    pcm_l_i16 = (pcm_l * 32767).astype(np.int16)
    pcm_r_i16 = (pcm_r * 32767).astype(np.int16)
    interleaved = np.empty(len(pcm_l_i16) * 2, dtype=np.int16)
    interleaved[0::2] = pcm_l_i16
    interleaved[1::2] = pcm_r_i16
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(interleaved.tobytes())


def _pink_noise(n_samples: int, rng: np.random.Generator) -> np.ndarray:
    """Generate pink (1/f) noise via Voss-McCartney algorithm."""
    white = rng.standard_normal(n_samples)
    # IIR filter approximation of 1/f slope
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1.0, -2.494956002, 2.017265875, -0.522189400]
    pink = lfilter(b, a, white)
    return pink


def _brown_noise(n_samples: int, rng: np.random.Generator) -> np.ndarray:
    """Generate brown (1/f²) noise by cumsum of white noise, then high-pass."""
    white = rng.standard_normal(n_samples)
    brown = np.cumsum(white)
    # Remove DC drift with a simple first-order high-pass
    alpha = 0.995
    hp = lfilter([1.0, -1.0], [1.0, -alpha], brown)
    return hp


def generate_calm_ocean_waves(sr: int, duration: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Pink noise with a slow sinusoidal amplitude LFO (~8 s wave cycle)."""
    n = sr * duration
    t = np.arange(n) / sr

    base = _pink_noise(n, rng)

    # Wave surge: LFO at 0.125 Hz (8-second period), depth 60 %
    lfo_freq = 0.125
    lfo = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * lfo_freq * t))

    sig = base * lfo

    # Slight stereo width via a short delay on the right channel (~8 ms)
    delay_samples = int(0.008 * sr)
    left = sig
    right = np.roll(sig, delay_samples)
    right[:delay_samples] = 0

    left = _apply_fade_out(_normalize(left, TARGET_DBFS), sr, FADE_DURATION)
    right = _apply_fade_out(_normalize(right, TARGET_DBFS), sr, FADE_DURATION)
    return left, right


def generate_forest_rain_ambient(sr: int, duration: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Brown noise base with a 2 Hz tremolo for rain-patter texture."""
    n = sr * duration
    t = np.arange(n) / sr

    base = _brown_noise(n, rng)

    # Rain patter: 2 Hz tremolo, light depth (20 %)
    tremolo = 0.8 + 0.2 * np.sin(2 * np.pi * 2.0 * t)
    # Occasional heavier drops: sparse spikes in white noise convolved with short envelope
    drop_env = np.exp(-np.linspace(0, 10, int(sr * 0.03)))
    drops = np.zeros(n)
    spike_locs = rng.integers(0, n - len(drop_env), size=int(duration * 8))
    for loc in spike_locs:
        drops[loc : loc + len(drop_env)] += rng.uniform(0.05, 0.15) * drop_env

    sig = base * tremolo + drops

    # Stereo: independent instances per channel
    base_r = _brown_noise(n, rng) * tremolo + drops * rng.uniform(0.8, 1.2)
    left = sig
    right = base_r

    left = _apply_fade_out(_normalize(left, TARGET_DBFS), sr, FADE_DURATION)
    right = _apply_fade_out(_normalize(right, TARGET_DBFS), sr, FADE_DURATION)
    return left, right


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    print("Generating calm_ocean_waves.wav …", end=" ", flush=True)
    l, r = generate_calm_ocean_waves(SAMPLE_RATE, DURATION, rng)
    out = OUT_DIR / "calm_ocean_waves.wav"
    _write_stereo_wav(out, l, r, SAMPLE_RATE)
    print(f"saved ({out.stat().st_size // 1024} KB)")

    print("Generating forest_rain_ambient.wav …", end=" ", flush=True)
    l, r = generate_forest_rain_ambient(SAMPLE_RATE, DURATION, rng)
    out = OUT_DIR / "forest_rain_ambient.wav"
    _write_stereo_wav(out, l, r, SAMPLE_RATE)
    print(f"saved ({out.stat().st_size // 1024} KB)")

    print("Done — audio files written to", OUT_DIR)


if __name__ == "__main__":
    main()
