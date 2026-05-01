"""Integration test for the Phase 4 runner."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from sentinelsleep import config
from sentinelsleep.db.schema import States
from sentinelsleep.orchestrator.runner import Runner


@pytest.fixture
def temp_db(tmp_path: Path):
    return tmp_path / "test_events.db"


@pytest.fixture
def stub_cache(tmp_path: Path):
    """Create a minimal valid stub cache for the runner to load."""
    cache_dir = tmp_path / "audio_cache"
    mixed_dir = cache_dir / "mixed"
    mixed_dir.mkdir(parents=True)

    # Touch a dummy file
    (mixed_dir / "intervention_severe_v1.wav").write_text("dummy")
    (mixed_dir / "intervention_mild_v1.wav").write_text("dummy")

    manifest = {
        "schema_version": 2,
        "mixed": [
            {"profile": "severe", "path": "mixed/intervention_severe_v1.wav", "playback_dbfs": -20.0},
            {"profile": "mild", "path": "mixed/intervention_mild_v1.wav", "playback_dbfs": -20.0},
        ]
    }
    (cache_dir / "manifest.json").write_text(json.dumps(manifest))
    return cache_dir


@pytest.mark.timeout(60)
def test_runner_on_severe_nightmare(temp_db, stub_cache):
    """Run the runner on the nightmare fixture and verify it triggers an intervention.

    All ML inference is mocked so the test validates orchestration logic (state
    transitions, event logging) without depending on what the real models score the
    synthetic fixture.  time.monotonic is also advanced by WINDOW_SECONDS per call
    so the 15s confirmation window resolves in the fast (non-realtime) test run.
    """
    from dataclasses import dataclass

    fixture_path = config.TEST_FIXTURES_DIR / "nightmare_severe.wav"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")

    @dataclass
    class FakeEmotion:
        valence: float = 0.2
        arousal: float = 0.8
        dominance: float = 0.2

    # Fake AST output — shape matches the 527-class softmax but values don't matter
    # because compute_dss is also mocked.
    fake_probs = np.zeros(527, dtype=np.float32)
    fake_probs[0] = 1.0

    call_counts: dict[str, int] = {"dss": 0, "time": 0}

    def _mock_classify(_self: object, _chunk: np.ndarray, _sr: int) -> np.ndarray:
        return fake_probs

    def _mock_predict(_self: object, _chunk: np.ndarray, _sr: int) -> FakeEmotion:
        return FakeEmotion()

    # 3 calm chunks, then high DSS for rest
    def _mock_compute_dss(_probs: np.ndarray) -> float:
        call_counts["dss"] += 1
        return 0.1 if call_counts["dss"] <= 3 else 0.85

    # Advance monotonic clock by WINDOW_SECONDS per chunk so the 15s window fills fast
    def _mock_monotonic() -> float:
        call_counts["time"] += 1
        return call_counts["time"] * config.WINDOW_SECONDS

    with (
        patch("sentinelsleep.orchestrator.runner.compute_dss", side_effect=_mock_compute_dss),
        patch("sentinelsleep.detection.ast_classifier.ASTClassifier.classify", _mock_classify),
        patch("sentinelsleep.verification.emotion_dim.EmotionAnalyzer.predict", _mock_predict),
        patch("sentinelsleep.verification.nightmare_signature.time.monotonic", side_effect=_mock_monotonic),
    ):
        runner = Runner(db_path=temp_db, cache_dir=stub_cache, device="cpu", dry_run=True)
        runner.run_from_file(fixture_path, realtime=False)

    # Verify db contents
    with sqlite3.connect(temp_db) as conn:
        conn.row_factory = sqlite3.Row
        
        sessions = conn.execute("SELECT * FROM sessions").fetchall()
        assert len(sessions) == 1
        session_id = sessions[0]["id"]
        assert sessions[0]["ended_at"] is not None

        events = conn.execute("SELECT state FROM events WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
        states = [e["state"] for e in events]
        
        # We expect at least LISTENING -> FLAGGED -> INTERVENING to have occurred
        assert States.LISTENING in states
        assert States.FLAGGED in states
        assert States.INTERVENING in states

        interventions = conn.execute("SELECT * FROM interventions").fetchall()
        assert len(interventions) >= 1
        assert interventions[0]["ended_at"] is not None
