"""SQLite event logger for Phase 4 orchestration.

This module is the **only place** in the codebase that writes to the
SQLite events database.  Dashboard views and all other consumers are
strictly read-only.

All writes are synchronous and flushed immediately per CLAUDE.md
constraint #3: *"State transitions are logged before audio side
effects."*  The caller must call :func:`log_event` before triggering
any audio playback.

Usage::

    from pathlib import Path
    from sentinelsleep.orchestrator.event_logger import EventLogger
    from sentinelsleep import config

    logger = EventLogger(config.EVENTS_DB_PATH)
    session_id = logger.start_session()
    event_id = logger.log_event(session_id=session_id, state="listening", dss=0.12)
    logger.record_intervention(event_id=event_id, clip_path=Path("..."))
    logger.end_session(session_id)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sentinelsleep.db.schema import get_connection, init_db

logger = logging.getLogger(__name__)


class EventLogger:
    """Write-only interface to the SentinelSleep SQLite event log.

    All methods commit immediately (``EVENT_LOG_FLUSH_EVERY_N = 1``).
    A new connection is opened per write to keep latency predictable
    and avoid long-held locks with WAL mode.

    Args:
        db_path: Path to the SQLite database file.  Parent directory and
                 tables are created via :func:`~sentinelsleep.db.schema.init_db`
                 on first construction.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = Path(db_path)
        init_db(self._path)
        logger.debug("EventLogger initialised — db: %s", self._path)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_session(self, notes: str = "") -> int:
        """Insert a new row in ``sessions`` and return its ``id``.

        Args:
            notes: Optional free-text notes attached to the session.

        Returns:
            The auto-generated ``sessions.id`` for this night's run.
        """
        now = _utcnow()
        with get_connection(self._path) as conn:
            cursor = conn.execute(
                "INSERT INTO sessions (started_at, notes) VALUES (?, ?)",
                (now, notes or None),
            )
            conn.commit()
            session_id = cursor.lastrowid
        logger.info("Session started — id=%d  at=%s", session_id, now)
        assert session_id is not None
        return int(session_id)

    def end_session(self, session_id: int) -> None:
        """Set ``ended_at`` on the given session row.

        Args:
            session_id: The ``sessions.id`` returned by :meth:`start_session`.
        """
        now = _utcnow()
        with get_connection(self._path) as conn:
            conn.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                (now, session_id),
            )
            conn.commit()
        logger.info("Session ended   — id=%d  at=%s", session_id, now)

    # ------------------------------------------------------------------
    # Event logging
    # ------------------------------------------------------------------

    def log_event(
        self,
        *,
        session_id: int,
        state: str,
        dss: Optional[float] = None,
        valence: Optional[float] = None,
        arousal: Optional[float] = None,
        dominance: Optional[float] = None,
        intervention_clip: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Insert a row into ``events`` and return its ``id``.

        This **must** be called before any audio side effect (CLAUDE.md #3).

        Args:
            session_id:        Foreign key into ``sessions``.
            state:             One of :class:`~sentinelsleep.db.schema.States`
                               string constants.
            dss:               Distress Signal Score at this moment (0–1).
            valence:           Emotion valence (0–1, low = negative).
            arousal:           Emotion arousal (0–1, high = activated).
            dominance:         Emotion dominance (0–1, low = low control).
            intervention_clip: Basename of the clip selected for playback
                               (populated only on INTERVENING events).
            notes:             Optional free-text annotation.

        Returns:
            The auto-generated ``events.id``.
        """
        now = _utcnow()
        with get_connection(self._path) as conn:
            cursor = conn.execute(
                """INSERT INTO events
                   (session_id, timestamp, state, dss,
                    valence, arousal, dominance, intervention_clip, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    now,
                    state,
                    dss,
                    valence,
                    arousal,
                    dominance,
                    intervention_clip,
                    notes,
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid
        logger.debug(
            "Event logged — session=%d state=%s dss=%.3f id=%d",
            session_id,
            state,
            dss if dss is not None else 0.0,
            event_id,
        )
        assert event_id is not None
        return int(event_id)

    # ------------------------------------------------------------------
    # Intervention recording
    # ------------------------------------------------------------------

    def record_intervention(
        self,
        *,
        event_id: int,
        clip_path: Path,
        pre_dss: Optional[float] = None,
    ) -> int:
        """Insert a row into ``interventions`` linked to *event_id*.

        Call this immediately before starting audio playback.  Call
        :meth:`close_intervention` when playback ends (or when the
        session ends, whichever comes first).

        Args:
            event_id:  Foreign key into ``events``.
            clip_path: Absolute path of the WAV being played.
            pre_dss:   DSS score captured just before playback starts.

        Returns:
            The auto-generated ``interventions.id``.
        """
        now = _utcnow()
        with get_connection(self._path) as conn:
            cursor = conn.execute(
                """INSERT INTO interventions
                   (event_id, started_at, clip_path, pre_dss)
                   VALUES (?, ?, ?, ?)""",
                (event_id, now, str(clip_path), pre_dss),
            )
            conn.commit()
            intervention_id = cursor.lastrowid
        logger.info(
            "Intervention started — event_id=%d clip=%s id=%d",
            event_id,
            clip_path.name,
            intervention_id,
        )
        assert intervention_id is not None
        return int(intervention_id)

    def close_intervention(
        self,
        intervention_id: int,
        *,
        post_dss: Optional[float] = None,
        effective: Optional[bool] = None,
    ) -> None:
        """Set ``ended_at``, ``post_dss``, and ``effective`` on an intervention row.

        Args:
            intervention_id: The ``interventions.id`` returned by
                :meth:`record_intervention`.
            post_dss:   DSS score measured after playback ends.
            effective:  Whether the intervention reduced distress
                        (``True``/``False``/``None`` = unknown).
        """
        now = _utcnow()
        effective_int = None if effective is None else int(effective)
        with get_connection(self._path) as conn:
            conn.execute(
                """UPDATE interventions
                   SET ended_at = ?, post_dss = ?, effective = ?
                   WHERE id = ?""",
                (now, post_dss, effective_int, intervention_id),
            )
            conn.commit()
        logger.info(
            "Intervention closed — id=%d  post_dss=%.3f  effective=%s",
            intervention_id,
            post_dss if post_dss is not None else 0.0,
            effective,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(tz=timezone.utc)
