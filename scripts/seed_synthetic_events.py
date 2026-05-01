"""Synthetic event seeder for dashboard development.

Populates a fresh SQLite database with a fake night's worth of events spanning
every state. This allows developing the dashboard views (Phase 5) without
ever needing to run the live orchestrator or audio pipeline.

Usage::

    uv run python scripts/seed_synthetic_events.py
    uv run streamlit run scripts/run_dashboard.py
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinelsleep import config
from sentinelsleep.db.schema import States, init_db
from sentinelsleep.orchestrator.event_logger import EventLogger

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def generate_synthetic_session(logger_obj: EventLogger, start_time: datetime, is_nightmare: bool) -> None:
    """Generate a realistic sequence of events for a single night."""
    session_id = logger_obj.start_session(notes="Synthetic seeded session")
    current_time = start_time

    def log_point(state: str, dss: float, v: float, a: float, d: float, clip: str | None = None) -> int:
        nonlocal current_time
        # Mock _utcnow for the logger just for this seed script
        import sentinelsleep.orchestrator.event_logger as el
        original_utcnow = el._utcnow
        el._utcnow = lambda: current_time
        try:
            event_id = logger_obj.log_event(
                session_id=session_id,
                state=state,
                dss=dss,
                valence=v,
                arousal=a,
                dominance=d,
                intervention_clip=clip
            )
            return event_id
        finally:
            el._utcnow = original_utcnow

    def advance(seconds: int) -> None:
        nonlocal current_time
        current_time += timedelta(seconds=seconds)

    # 1. Calm sleeping
    for _ in range(10):
        log_point(States.LISTENING, random.uniform(0.0, 0.1), 0.8, 0.2, 0.7)
        advance(30)

    if is_nightmare:
        # 2. Distress onset
        log_point(States.FLAGGED, 0.45, 0.4, 0.5, 0.4)
        advance(2)
        log_point(States.FLAGGED, 0.55, 0.3, 0.7, 0.3)
        advance(2)

        # 3. Nightmare confirmed -> Intervention
        event_id = log_point(States.INTERVENING, 0.65, 0.2, 0.8, 0.2, "intervention_severe_v1.wav")
        
        # Record intervention
        import sentinelsleep.orchestrator.event_logger as el
        original_utcnow = el._utcnow
        el._utcnow = lambda: current_time
        int_id = logger_obj.record_intervention(
            event_id=event_id,
            clip_path=config.AUDIO_CACHE_DIR / "mixed/intervention_severe_v1.wav",
            pre_dss=0.65
        )
        el._utcnow = original_utcnow

        advance(30)
        
        # 4. Distress clears
        log_point(States.RESOLVED, 0.2, 0.6, 0.4, 0.5)
        
        el._utcnow = lambda: current_time
        logger_obj.close_intervention(int_id, post_dss=0.2, effective=True)
        el._utcnow = original_utcnow
        advance(5)

    # 5. Return to calm
    for _ in range(10):
        log_point(States.LISTENING, random.uniform(0.0, 0.1), 0.8, 0.2, 0.7)
        advance(30)

    # End session
    import sentinelsleep.orchestrator.event_logger as el
    original_utcnow = el._utcnow
    el._utcnow = lambda: current_time
    logger_obj.end_session(session_id)
    el._utcnow = original_utcnow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=config.EVENTS_DB_PATH)
    parser.add_argument("--clear", action="store_true", help="Delete existing DB before seeding")
    args = parser.parse_args()

    db_path = args.db
    if args.clear and db_path.exists():
        db_path.unlink()
        logger.info(f"Deleted existing DB: {db_path}")

    init_db(db_path)
    el = EventLogger(db_path)

    now = datetime.now(tz=timezone.utc)
    
    # 3 nights ago - calm
    generate_synthetic_session(el, now - timedelta(days=3, hours=8), is_nightmare=False)
    
    # 2 nights ago - nightmare
    generate_synthetic_session(el, now - timedelta(days=2, hours=8), is_nightmare=True)
    
    # Last night - calm
    generate_synthetic_session(el, now - timedelta(days=1, hours=8), is_nightmare=False)

    logger.info(f"Successfully seeded {db_path} with 3 synthetic sessions.")


if __name__ == "__main__":
    main()
