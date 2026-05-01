"""SQLite schema — single source of truth for the events database.

DDL matches SENTINELSLEEP_PLAN.md §7 Phase 4.  Both the event logger
(writer) and the dashboard (reader) import state constants and table
names from here so no string is duplicated.

Usage::

    from sentinelsleep.db.schema import init_db, get_connection, States

    init_db(config.EVENTS_DB_PATH)
    with get_connection(config.EVENTS_DB_PATH) as conn:
        conn.execute("SELECT * FROM events")
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# State name constants  (used by state_machine, event_logger, dashboard)
# ---------------------------------------------------------------------------

class States:
    """Canonical string values for the ``state`` column in ``events``."""
    LISTENING   = "listening"
    FLAGGED     = "flagged"
    INTERVENING = "intervening"
    ESCALATING  = "escalating"
    RESOLVED    = "resolved"
    AWAKE       = "awake"

    ALL: tuple[str, ...] = (
        LISTENING, FLAGGED, INTERVENING, ESCALATING, RESOLVED, AWAKE
    )


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """\
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP NOT NULL,
    ended_at   TIMESTAMP,
    notes      TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL,
    timestamp        TIMESTAMP NOT NULL,
    state            TEXT NOT NULL,
    dss              REAL,
    valence          REAL,
    arousal          REAL,
    dominance        REAL,
    intervention_clip TEXT,
    notes            TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS interventions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER NOT NULL,
    started_at  TIMESTAMP NOT NULL,
    ended_at    TIMESTAMP,
    clip_path   TEXT NOT NULL,
    pre_dss     REAL,
    post_dss    REAL,
    effective   INTEGER,
    FOREIGN KEY (event_id) REFERENCES events(id)
);

CREATE INDEX IF NOT EXISTS idx_events_session
    ON events (session_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_interventions_event
    ON interventions (event_id);
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_db(path: Path) -> None:
    """Create the database and all tables if they do not yet exist.

    Idempotent — safe to call on every startup.

    Args:
        path: Filesystem path for the SQLite database file.
              Parent directory is created if missing.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.executescript(_DDL)
        conn.commit()


def get_connection(path: Path) -> sqlite3.Connection:
    """Return an open SQLite connection with ``row_factory`` set.

    The caller owns the connection and must close it (or use it as a
    context manager).

    Args:
        path: Path to the SQLite database file (must already exist or
              ``init_db`` must have been called first).

    Returns:
        ``sqlite3.Connection`` with ``row_factory = sqlite3.Row`` so
        columns are accessible by name.
    """
    conn = sqlite3.connect(str(path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
