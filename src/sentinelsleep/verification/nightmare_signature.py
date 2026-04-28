"""Nightmare signature verifier for the SentinelSleep verification layer.

Combines DSS history (from Layer 1) with dimensional emotion scores (from Layer 2)
to make a confirmed/unconfirmed determination on whether an audio event is a genuine
PTSD nightmare.

The nightmare signature rule (from SENTINELSLEEP_PLAN.md §7 Phase 2):

    confirmed = (
        mean(dss_window) > DSS_FLAG_THRESHOLD       # acoustic distress present
        and valence < VALENCE_MAX_FOR_NIGHTMARE      # negative emotional state
        and arousal > AROUSAL_MIN_FOR_NIGHTMARE      # high activation
        and dominance < DOMINANCE_MAX_FOR_NIGHTMARE  # low control
        and sustained for >= NIGHTMARE_CONFIRM_DURATION_SECONDS
    )

The verifier maintains a sliding window of per-chunk (dss, valence, arousal, dominance)
readings and checks whether the nightmare signature has been sustained for the required
duration.  It also computes a confidence score indicating the intensity of the signal.

Usage::

    verifier = NightmareVerifier()

    # Called once per 2-second detection chunk:
    sig = verifier.update(dss=0.45, valence=0.25, arousal=0.75, dominance=0.30)
    if sig.confirmed:
        trigger_intervention(sig.confidence)

    # When distress resolves:
    verifier.reset()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from statistics import mean

from sentinelsleep import config


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class NightmareSignature:
    """Result of a single ``NightmareVerifier.update()`` call.

    Attributes:
        confirmed:   True when the nightmare signature has been sustained for
                     ``NIGHTMARE_CONFIRM_DURATION_SECONDS``.
        confidence:  Composite intensity score in ``[0, 1]``.  Reflects how
                     strongly the window's average readings match the nightmare
                     profile.  0.0 when the window is empty or unconfirmed with
                     no signal; higher values indicate a stronger signal.
        dss_mean:    Mean DSS across the current distress window.
        valence:     Most-recent frame valence (lower = more negative).
        arousal:     Most-recent frame arousal (higher = more activated).
        dominance:   Most-recent frame dominance (lower = less control).
        duration_s:  Seconds the distress window has been accumulating.
        frames:      Number of frames in the current distress window.
    """

    confirmed: bool
    confidence: float
    dss_mean: float
    valence: float
    arousal: float
    dominance: float
    duration_s: float
    frames: int


# ---------------------------------------------------------------------------
# Single-frame predicate
# ---------------------------------------------------------------------------


def is_nightmare_frame(
    dss: float,
    valence: float,
    arousal: float,
    dominance: float,
    dss_threshold: float = config.DSS_FLAG_THRESHOLD,
    valence_max: float = config.VALENCE_MAX_FOR_NIGHTMARE,
    arousal_min: float = config.AROUSAL_MIN_FOR_NIGHTMARE,
    dominance_max: float = config.DOMINANCE_MAX_FOR_NIGHTMARE,
) -> bool:
    """Return True if a single frame passes all nightmare thresholds.

    All four conditions must hold simultaneously — this is a strict AND gate.
    None of the thresholds are hit exactly (strict inequalities).

    Args:
        dss:           Distress Signal Score for this chunk (0–1).
        valence:       Emotional valence (0=very negative, 1=very positive).
        arousal:       Emotional arousal (0=calm, 1=very activated).
        dominance:     Emotional dominance (0=powerless, 1=in control).
        dss_threshold: Minimum DSS to classify as distress.
        valence_max:   Maximum valence for a negative emotional state.
        arousal_min:   Minimum arousal for high activation.
        dominance_max: Maximum dominance for low-control state.

    Returns:
        ``True`` if all four threshold conditions are met.
    """
    return (
        dss > dss_threshold
        and valence < valence_max
        and arousal > arousal_min
        and dominance < dominance_max
    )


# ---------------------------------------------------------------------------
# Sliding-window verifier
# ---------------------------------------------------------------------------


@dataclass
class _Frame:
    """Internal per-chunk record stored in the verifier window."""

    timestamp: float  # time.monotonic() at insert
    dss: float
    valence: float
    arousal: float
    dominance: float


class NightmareVerifier:
    """Sliding-window verifier that confirms sustained nightmare signatures.

    The verifier accumulates frames as long as each frame passes
    :func:`is_nightmare_frame`.  Confirmation fires when the window spans
    at least ``confirm_duration_s`` seconds continuously.

    If any frame fails the per-frame predicate, the window is reset — the
    nightmare signature must be *continuously* sustained to confirm.

    Attributes:
        confirm_duration_s: Required continuous distress duration (seconds).
    """

    def __init__(
        self,
        confirm_duration_s: float = float(config.NIGHTMARE_CONFIRM_DURATION_SECONDS),
    ) -> None:
        """Initialise the verifier with an empty window.

        Args:
            confirm_duration_s: Required sustained distress duration in seconds.
                Defaults to ``config.NIGHTMARE_CONFIRM_DURATION_SECONDS`` (15s).
        """
        self.confirm_duration_s = confirm_duration_s
        self._window: list[_Frame] = field(default_factory=list)  # type: ignore[assignment]
        self._window = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        dss: float,
        valence: float,
        arousal: float,
        dominance: float,
    ) -> NightmareSignature:
        """Record a new detection chunk and return the current signature.

        If the frame passes :func:`is_nightmare_frame`, it is appended to the
        distress window.  If not, the window is reset to empty.

        Args:
            dss:       Distress Signal Score from the AST classifier.
            valence:   Valence from the emotion model.
            arousal:   Arousal from the emotion model.
            dominance: Dominance from the emotion model.

        Returns:
            :class:`NightmareSignature` describing the current window state.
        """
        now = time.monotonic()

        if is_nightmare_frame(dss, valence, arousal, dominance):
            self._window.append(
                _Frame(
                    timestamp=now,
                    dss=dss,
                    valence=valence,
                    arousal=arousal,
                    dominance=dominance,
                )
            )
        else:
            # Distress broke — reset the window; must restart the 15s clock.
            self._window = []

        return self._build_signature(
            current_valence=valence,
            current_arousal=arousal,
            current_dominance=dominance,
        )

    def reset(self) -> None:
        """Clear the distress window.

        Call this when the pipeline transitions out of INTERVENING/ESCALATING
        back to LISTENING — ensures the confirmation clock restarts cleanly.
        """
        self._window = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_signature(
        self,
        current_valence: float,
        current_arousal: float,
        current_dominance: float,
    ) -> NightmareSignature:
        """Compute and return the current :class:`NightmareSignature`."""
        if not self._window:
            return NightmareSignature(
                confirmed=False,
                confidence=0.0,
                dss_mean=0.0,
                valence=current_valence,
                arousal=current_arousal,
                dominance=current_dominance,
                duration_s=0.0,
                frames=0,
            )

        oldest = self._window[0].timestamp
        newest = self._window[-1].timestamp
        duration_s = newest - oldest

        dss_vals = [f.dss for f in self._window]
        valence_vals = [f.valence for f in self._window]
        arousal_vals = [f.arousal for f in self._window]
        dominance_vals = [f.dominance for f in self._window]

        dss_mean = mean(dss_vals)
        mean_arousal = mean(arousal_vals)
        mean_valence = mean(valence_vals)
        mean_dominance = mean(dominance_vals)

        confirmed = (
            duration_s >= self.confirm_duration_s
            and len(self._window) >= 2  # need at least 2 frames to span any duration
        )

        # Confidence: composite of how strongly each dimension signals nightmare.
        # All factors are in [0, 1]; product is also in [0, 1].
        # - dss_mean: higher = more acoustic distress
        # - mean_arousal: higher = more activated
        # - (1 - mean_valence): higher = more negative emotional state
        # - (1 - mean_dominance): higher = less control
        confidence = float(
            dss_mean
            * mean_arousal
            * (1.0 - mean_valence)
            * (1.0 - mean_dominance)
        )

        return NightmareSignature(
            confirmed=confirmed,
            confidence=confidence,
            dss_mean=dss_mean,
            valence=current_valence,
            arousal=current_arousal,
            dominance=current_dominance,
            duration_s=duration_s,
            frames=len(self._window),
        )
