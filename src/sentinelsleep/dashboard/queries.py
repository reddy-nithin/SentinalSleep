"""Read-only SQLite queries for the Phase 5 Morning Dashboard.

This module is the **only place** the dashboard may execute SQL.
It strictly enforces the read-only constraint (CLAUDE.md #4).

Usage::

    from sentinelsleep.dashboard import queries

    sessions = queries.get_sessions()
    events = queries.get_events_for_session(session_id)

All queries use parameterized SQL to prevent injection.
Results are returned as a list of `sqlite3.Row` objects, which behave
like dictionaries.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sentinelsleep import config
from sentinelsleep.db.schema import get_connection


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_sessions(
    db_path: Path | None = None,
    limit: int = 30,
) -> list[sqlite3.Row]:
    """Return the most recent sessions, ordered newest first."""
    db_path = db_path or config.EVENTS_DB_PATH
    with get_connection(db_path) as conn:
        return conn.execute(
            """SELECT id, started_at, ended_at, notes
               FROM sessions
               ORDER BY started_at DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()


def get_events_for_session(
    session_id: int,
    db_path: Path | None = None,
) -> list[sqlite3.Row]:
    """Return all events for a specific session, ordered by timestamp."""
    db_path = db_path or config.EVENTS_DB_PATH
    with get_connection(db_path) as conn:
        return conn.execute(
            """SELECT e.*, i.pre_dss, i.post_dss, i.effective, i.clip_path
               FROM events e
               LEFT JOIN interventions i ON i.event_id = e.id
               WHERE e.session_id = ?
               ORDER BY e.timestamp ASC""",
            (session_id,)
        ).fetchall()


def get_interventions(
    window_days: int = 7,
    db_path: Path | None = None,
) -> list[sqlite3.Row]:
    """Return all interventions from the last ``window_days`` days."""
    db_path = db_path or config.EVENTS_DB_PATH
    cutoff = _utcnow() - timedelta(days=window_days)
    with get_connection(db_path) as conn:
        return conn.execute(
            """SELECT i.*, e.timestamp, e.session_id, e.intervention_clip
               FROM interventions i
               JOIN events e ON i.event_id = e.id
               WHERE e.timestamp >= ?
               ORDER BY e.timestamp DESC""",
            (cutoff,)
        ).fetchall()


def get_dss_timeseries(
    session_id: int,
    db_path: Path | None = None,
) -> list[sqlite3.Row]:
    """Return timeseries data for the waveform view for a single session."""
    db_path = db_path or config.EVENTS_DB_PATH
    with get_connection(db_path) as conn:
        return conn.execute(
            """SELECT timestamp, state, dss, valence, arousal, dominance
               FROM events
               WHERE session_id = ? AND dss IS NOT NULL
               ORDER BY timestamp ASC""",
            (session_id,)
        ).fetchall()


def get_trends(
    window_days: int = 7,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return aggregate metrics over the last ``window_days`` days.

    Returns:
        Dict containing keys like 'total_sessions', 'total_interventions',
        'effective_rate', etc.
    """
    db_path = db_path or config.EVENTS_DB_PATH
    cutoff = _utcnow() - timedelta(days=window_days)
    
    with get_connection(db_path) as conn:
        # Sessions count
        sess_row = conn.execute(
            "SELECT count(*) as count FROM sessions WHERE started_at >= ?",
            (cutoff,)
        ).fetchone()
        
        # Interventions count and effectiveness
        int_rows = conn.execute(
            """SELECT count(*) as total,
                      sum(case when effective = 1 then 1 else 0 end) as effective_count
               FROM interventions i
               JOIN events e ON i.event_id = e.id
               WHERE e.timestamp >= ?""",
            (cutoff,)
        ).fetchone()

    total_int = int_rows["total"] or 0
    eff_count = int_rows["effective_count"] or 0
    eff_rate = (eff_count / total_int * 100.0) if total_int > 0 else 0.0

    return {
        "window_days": window_days,
        "total_sessions": sess_row["count"],
        "total_interventions": total_int,
        "effective_interventions": eff_count,
        "effective_rate_percent": eff_rate,
    }
