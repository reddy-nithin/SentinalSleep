"""Single source of truth for thresholds, paths, and tunable constants.

All other modules import from this file. Never hardcode a path or magic
number elsewhere in the codebase.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# PROJECT_ROOT resolves to the repo root regardless of CWD.
# config.py lives at <root>/src/sentinelsleep/config.py → 2 parents up.
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
AUDIO_CACHE_DIR: Final[Path] = DATA_DIR / "audio_cache"
MUSIC_CACHE_DIR: Final[Path] = AUDIO_CACHE_DIR / "music"
SOUNDSCAPE_CACHE_DIR: Final[Path] = AUDIO_CACHE_DIR / "soundscape"
MIXED_CACHE_DIR: Final[Path] = AUDIO_CACHE_DIR / "mixed"
TEST_FIXTURES_DIR: Final[Path] = DATA_DIR / "test_fixtures"
EVENTS_DB_PATH: Final[Path] = DATA_DIR / "events.db"

# ---------------------------------------------------------------------------
# Audio I/O
# ---------------------------------------------------------------------------

SAMPLE_RATE: Final[int] = 16_000              # AST + wav2vec2 expect 16 kHz
WINDOW_SECONDS: Final[float] = 2.0            # detection chunk size (seconds)
WINDOW_SAMPLES: Final[int] = int(SAMPLE_RATE * WINDOW_SECONDS)
INTERVENTION_SAMPLE_RATE: Final[int] = 44_100  # cached therapeutic audio
INTERVENTION_BIT_DEPTH: Final[int] = 16

# ---------------------------------------------------------------------------
# Detection — Layer 1 (MIT AST)
# ---------------------------------------------------------------------------

AST_MODEL_ID: Final[str] = "MIT/ast-finetuned-audioset-10-10-0.4593"

# Distress Signal Score thresholds
DSS_FLAG_THRESHOLD: Final[float] = 0.4        # DSS > this → escalate to verification
DSS_FALSE_POSITIVE_CEILING: Final[float] = 0.3  # negative fixtures must stay below this

# Weighted AudioSet distress classes.  Keys must match exact AudioSet label strings.
DISTRESS_CLASS_WEIGHTS: Final[dict[str, float]] = {
    "Crying, sobbing": 1.0,
    "Whimper": 0.9,
    "Screaming": 1.0,
    "Wail, moan": 0.8,
    "Heavy breathing": 0.6,
    "Gasp": 0.7,
    "Groan": 0.5,
    "Rustle": 0.3,
    "Thump, thud": 0.4,
}

# ---------------------------------------------------------------------------
# Verification — Layer 2 (audeering wav2vec2)
# ---------------------------------------------------------------------------

EMOTION_MODEL_ID: Final[str] = (
    "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"
)

# Nightmare signature thresholds (all must hold simultaneously)
VALENCE_MAX_FOR_NIGHTMARE: Final[float] = 0.4    # valence < this = negative state
AROUSAL_MIN_FOR_NIGHTMARE: Final[float] = 0.6    # arousal > this = activated
DOMINANCE_MAX_FOR_NIGHTMARE: Final[float] = 0.4  # dominance < this = low control
NIGHTMARE_CONFIRM_DURATION_SECONDS: Final[int] = 15  # must persist this long

# ---------------------------------------------------------------------------
# Intervention — Layer 3 (pre-generated cache)
# ---------------------------------------------------------------------------

MUSICGEN_MODEL_ID: Final[str] = "facebook/musicgen-small"
AUDIOLDM2_MODEL_ID: Final[str] = "cvssp/audioldm2"

INTERVENTION_DURATION_SECONDS: Final[int] = 60
INTERVENTION_PLAYBACK_DBFS: Final[float] = -20.0   # playback level (ambient)
SOUNDSCAPE_RELATIVE_DBFS: Final[float] = -6.0      # soundscape under music

# ---------------------------------------------------------------------------
# Escalation — Layer 4
# ---------------------------------------------------------------------------

# If distress persists this many seconds after intervention starts, escalate.
ESCALATION_PERSISTENCE_SECONDS: Final[int] = 60

# ---------------------------------------------------------------------------
# Event logging
# ---------------------------------------------------------------------------

EVENT_LOG_FLUSH_EVERY_N: Final[int] = 1  # flush to SQLite on every event

# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------


def select_device() -> str:
    """Return 'mps' on Apple Silicon when available, else 'cpu'.

    Uses a local torch import so importing config never pulls the full ML
    stack into lightweight tooling processes (e.g., dashboard queries).
    """
    import torch  # noqa: PLC0415 — intentional lazy import

    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
