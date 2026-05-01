"""Unit tests for the Phase 4 event logger."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sentinelsleep.db.schema import States
from sentinelsleep.orchestrator.event_logger import EventLogger


@pytest.fixture
def logger(tmp_path: Path):
    """Provide an EventLogger connected to a temporary DB."""
    db_path = tmp_path / "test_events.db"
    return EventLogger(db_path)


def test_session_lifecycle(logger: EventLogger):
    session_id = logger.start_session("test notes")
    assert isinstance(session_id, int)

    logger.end_session(session_id)

    # Verify directly via sqlite3
    with sqlite3.connect(logger._path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        assert row is not None
        assert row["notes"] == "test notes"
        assert row["started_at"] is not None
        assert row["ended_at"] is not None


def test_log_event(logger: EventLogger):
    session_id = logger.start_session()

    event_id = logger.log_event(
        session_id=session_id,
        state=States.FLAGGED,
        dss=0.45,
        valence=0.3,
        arousal=0.8,
        dominance=0.2,
        notes="flagged"
    )
    assert isinstance(event_id, int)

    with sqlite3.connect(logger._path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        assert row is not None
        assert row["session_id"] == session_id
        assert row["state"] == States.FLAGGED
        assert row["dss"] == 0.45
        assert row["valence"] == 0.3
        assert row["arousal"] == 0.8
        assert row["dominance"] == 0.2
        assert row["notes"] == "flagged"


def test_intervention_lifecycle(logger: EventLogger):
    session_id = logger.start_session()
    event_id = logger.log_event(session_id=session_id, state=States.INTERVENING)

    clip_path = Path("/mock/clip.wav")
    intervention_id = logger.record_intervention(
        event_id=event_id,
        clip_path=clip_path,
        pre_dss=0.6,
    )
    assert isinstance(intervention_id, int)

    logger.close_intervention(intervention_id, post_dss=0.2, effective=True)

    with sqlite3.connect(logger._path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM interventions WHERE id = ?", (intervention_id,)).fetchone()
        assert row is not None
        assert row["event_id"] == event_id
        assert row["clip_path"] == str(clip_path)
        assert row["pre_dss"] == 0.6
        assert row["post_dss"] == 0.2
        assert row["effective"] == 1
        assert row["started_at"] is not None
        assert row["ended_at"] is not None
