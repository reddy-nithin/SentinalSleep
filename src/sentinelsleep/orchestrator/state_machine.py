"""Pure state machine for the SentinelSleep orchestration loop.

Implements the state transitions defined in SENTINELSLEEP_PLAN.md §3.2.
This module contains **no I/O** — it receives observations and returns
``(new_state, action)`` tuples.  All side effects (logging to SQLite,
playing audio) are the caller's responsibility.

State diagram::

    LISTENING ──dss > DSS_FLAG_THRESHOLD──► FLAGGED
    FLAGGED   ──nightmare confirmed────────► INTERVENING
    FLAGGED   ──nightmare fades─────────── ► LISTENING
    INTERVENING ──distress persists > 60s──► ESCALATING
    INTERVENING ──distress clears──────────► RESOLVED
    ESCALATING ──manual reset────────────── ► AWAKE
    RESOLVED / AWAKE ──────────────────────► LISTENING

Usage::

    from sentinelsleep.orchestrator.state_machine import StateMachine
    from sentinelsleep.db.schema import States

    sm = StateMachine()
    new_state, action = sm.update(observation)

The returned ``action`` is a string token understood by the runner
(``"none"``, ``"intervene"``, ``"escalate"``, ``"reset"``).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Literal

from sentinelsleep import config
from sentinelsleep.db.schema import States

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Observation dataclass
# ---------------------------------------------------------------------------

Action = Literal["none", "intervene", "escalate", "reset"]


@dataclass
class Observation:
    """A single time-step observation fed to :class:`StateMachine.update`.

    Args:
        dss:            Distress Signal Score in ``[0, 1]``.
        nightmare_confirmed: ``True`` when the verification layer has
            confirmed a sustained nightmare signature.
        manual_reset:   ``True`` when an external signal requests a
            forced LISTENING reset (e.g., patient woke voluntarily).
        valence:        Optional emotion valence ``[0, 1]``.
        arousal:        Optional emotion arousal ``[0, 1]``.
        dominance:      Optional emotion dominance ``[0, 1]``.
    """

    dss: float
    nightmare_confirmed: bool = False
    manual_reset: bool = False
    valence: float | None = None
    arousal: float | None = None
    dominance: float | None = None


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


@dataclass
class StateMachine:
    """Deterministic finite state machine for the SentinelSleep loop.

    All thresholds are read from ``config.py`` — no magic numbers here.

    Attributes:
        state:              Current state (one of :class:`~sentinelsleep.db.schema.States`).
        _state_entered_at:  Monotonic timestamp when the current state was entered.
    """

    state: str = field(default=States.LISTENING)
    _state_entered_at: float = field(default_factory=time.monotonic, init=False, repr=False)
    _flagged_at: float | None = field(default=None, init=False, repr=False)

    def update(self, obs: Observation) -> tuple[str, Action]:
        """Compute the next state and action from *obs*.

        The state is updated in-place.  The caller must:
        1. Log the returned state to SQLite **before** executing the action.
        2. Execute the action (e.g., play audio).

        Args:
            obs: Current time-step observation.

        Returns:
            ``(new_state, action)`` tuple where ``action`` is one of
            ``"none"``, ``"intervene"``, ``"escalate"``, ``"reset"``.
        """
        if obs.manual_reset:
            return self._transition(States.LISTENING, "reset")

        if self.state == States.LISTENING:
            return self._handle_listening(obs)
        elif self.state == States.FLAGGED:
            return self._handle_flagged(obs)
        elif self.state == States.INTERVENING:
            return self._handle_intervening(obs)
        elif self.state == States.ESCALATING:
            return self._handle_escalating(obs)
        elif self.state in (States.RESOLVED, States.AWAKE):
            # Auto-return to listening after a brief cool-down
            return self._transition(States.LISTENING, "none")
        else:
            logger.warning("Unknown state %r — resetting to LISTENING", self.state)
            return self._transition(States.LISTENING, "none")

    # ------------------------------------------------------------------
    # Per-state handlers
    # ------------------------------------------------------------------

    def _handle_listening(self, obs: Observation) -> tuple[str, Action]:
        if obs.dss > config.DSS_FLAG_THRESHOLD:
            logger.info(
                "DSS %.3f > %.3f threshold — escalating to FLAGGED",
                obs.dss,
                config.DSS_FLAG_THRESHOLD,
            )
            self._flagged_at = time.monotonic()
            return self._transition(States.FLAGGED, "none")
        return self.state, "none"

    def _handle_flagged(self, obs: Observation) -> tuple[str, Action]:
        if obs.nightmare_confirmed:
            logger.info("Nightmare confirmed — transitioning to INTERVENING")
            return self._transition(States.INTERVENING, "intervene")
        # If DSS drops back below threshold, return to listening
        if obs.dss <= config.DSS_FLAG_THRESHOLD:
            logger.info(
                "DSS %.3f dropped below threshold — returning to LISTENING",
                obs.dss,
            )
            self._flagged_at = None
            return self._transition(States.LISTENING, "none")
        return self.state, "none"

    def _handle_intervening(self, obs: Observation) -> tuple[str, Action]:
        elapsed = time.monotonic() - self._state_entered_at
        if obs.dss <= config.DSS_FLAG_THRESHOLD:
            logger.info("Distress cleared after intervention — RESOLVED")
            return self._transition(States.RESOLVED, "none")
        if elapsed >= config.ESCALATION_PERSISTENCE_SECONDS:
            logger.warning(
                "Distress persisted %.0fs ≥ %ds limit — ESCALATING",
                elapsed,
                config.ESCALATION_PERSISTENCE_SECONDS,
            )
            return self._transition(States.ESCALATING, "escalate")
        return self.state, "none"

    def _handle_escalating(self, obs: Observation) -> tuple[str, Action]:
        # Escalation is a wake protocol — stays here until manual_reset
        return self.state, "none"

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _transition(self, new_state: str, action: Action) -> tuple[str, Action]:
        if new_state != self.state:
            logger.info("State: %s → %s  [action=%s]", self.state, new_state, action)
        self.state = new_state
        self._state_entered_at = time.monotonic()
        return new_state, action
