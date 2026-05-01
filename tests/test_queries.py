"""Unit tests for the Phase 5 dashboard read-only queries."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from sentinelsleep.dashboard import queries
from sentinelsleep.db.schema import States, init_db


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    """Provide a temporary database with synthetic events for testing."""
    db_path = tmp_path / "test_dashboard.db"
    init_db(db_path)

    now = datetime.now(tz=timezone.utc)
    yesterday = now - timedelta(days=1)

    with sqlite3.connect(db_path) as conn:
        # Insert Session 1 (yesterday)
        cursor = conn.execute(
            "INSERT INTO sessions (started_at, ended_at, notes) VALUES (?, ?, ?)",
            (yesterday, yesterday + timedelta(hours=8), "Session 1"),
        )
        s1 = cursor.lastrowid

        # Insert Session 2 (today)
        cursor = conn.execute(
            "INSERT INTO sessions (started_at, ended_at, notes) VALUES (?, ?, ?)",
            (now - timedelta(hours=2), now, "Session 2"),
        )
        s2 = cursor.lastrowid

        # Insert Events for Session 1
        e1 = conn.execute(
            """INSERT INTO events (session_id, timestamp, state, dss)
               VALUES (?, ?, ?, ?)""",
            (s1, yesterday + timedelta(minutes=10), States.LISTENING, 0.1),
        ).lastrowid

        # Insert Events & Intervention for Session 2
        e2 = conn.execute(
            """INSERT INTO events (session_id, timestamp, state, dss, intervention_clip)
               VALUES (?, ?, ?, ?, ?)""",
            (s2, now - timedelta(minutes=60), States.INTERVENING, 0.6, "mild_v1.wav"),
        ).lastrowid

        conn.execute(
            """INSERT INTO interventions (event_id, started_at, ended_at, clip_path, pre_dss, post_dss, effective)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (e2, now - timedelta(minutes=60), now - timedelta(minutes=59), "/path/mild_v1.wav", 0.6, 0.2, 1),
        )

        conn.commit()

    return db_path


def test_get_sessions(seeded_db: Path):
    rows = queries.get_sessions(db_path=seeded_db, limit=10)
    assert len(rows) == 2
    # Newest first
    assert rows[0]["notes"] == "Session 2"
    assert rows[1]["notes"] == "Session 1"


def test_get_events_for_session(seeded_db: Path):
    # s1 should have 1 event
    rows_s1 = queries.get_events_for_session(session_id=1, db_path=seeded_db)
    assert len(rows_s1) == 1
    assert rows_s1[0]["state"] == States.LISTENING
    assert rows_s1[0]["clip_path"] is None  # LEFT JOIN null

    # s2 should have 1 event with intervention data joined
    rows_s2 = queries.get_events_for_session(session_id=2, db_path=seeded_db)
    assert len(rows_s2) == 1
    assert rows_s2[0]["state"] == States.INTERVENING
    assert rows_s2[0]["clip_path"] == "/path/mild_v1.wav"
    assert rows_s2[0]["effective"] == 1


def test_get_interventions(seeded_db: Path):
    rows = queries.get_interventions(window_days=7, db_path=seeded_db)
    assert len(rows) == 1
    assert rows[0]["pre_dss"] == 0.6
    assert rows[0]["effective"] == 1


def test_get_dss_timeseries(seeded_db: Path):
    rows = queries.get_dss_timeseries(session_id=2, db_path=seeded_db)
    assert len(rows) == 1
    assert rows[0]["dss"] == 0.6


def test_get_trends(seeded_db: Path):
    trends = queries.get_trends(window_days=7, db_path=seeded_db)
    assert trends["total_sessions"] == 2
    assert trends["total_interventions"] == 1
    assert trends["effective_interventions"] == 1
    assert trends["effective_rate_percent"] == 100.0
