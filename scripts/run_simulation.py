"""Simulation / demo entry point for SentinelSleep.

Runs the full pipeline on a WAV file (or the scripted demo track) instead
of a live microphone.  Useful for demos, acceptance testing, and CI smoke
passes that don't require audio hardware.

Usage::

    # Single fixture
    uv run python scripts/run_simulation.py data/test_fixtures/nightmare_severe.wav

    # Demo mode (scripted 2-min track)
    uv run python scripts/run_simulation.py --demo

    # Fast (no real-time sleep between chunks, for quick acceptance tests)
    uv run python scripts/run_simulation.py --fast data/test_fixtures/nightmare_severe.wav

Results are written to ``data/events.db``.  View with::

    uv run streamlit run scripts/run_dashboard.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinelsleep import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_DEMO_TRACK = config.TEST_FIXTURES_DIR / "demo_track_2min.wav"


def main() -> None:
    """Parse arguments and run the simulation."""
    parser = argparse.ArgumentParser(
        description="Run SentinelSleep pipeline on a WAV file (simulation mode).",
    )
    parser.add_argument(
        "wav_file",
        nargs="?",
        type=Path,
        help="Path to the WAV file to process.  Omit when --demo is set.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help=f"Use the scripted demo track ({_DEMO_TRACK.name}).",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip real-time sleep between chunks (fast acceptance test mode).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Suppress audio playback (useful in CI where no audio device exists).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=config.EVENTS_DB_PATH,
        help=f"Path to SQLite event log. Default: {config.EVENTS_DB_PATH}",
    )
    args = parser.parse_args()

    # Resolve the WAV path
    if args.demo:
        wav_path = _DEMO_TRACK
        if not wav_path.exists():
            logger.error(
                "Demo track not found: %s\n"
                "Run: uv run python src/sentinelsleep/demo/simulator.py --build",
                wav_path,
            )
            sys.exit(1)
    elif args.wav_file:
        wav_path = args.wav_file.expanduser().resolve()
        if not wav_path.exists():
            logger.error("WAV file not found: %s", wav_path)
            sys.exit(1)
    else:
        parser.error("Provide a WAV file path or use --demo")
        return  # unreachable, satisfies mypy

    logger.info("SentinelSleep Simulation")
    logger.info("  source  : %s", wav_path)
    logger.info("  db      : %s", args.db)
    logger.info("  realtime: %s", not args.fast)
    logger.info("  dry_run : %s", args.dry_run)

    from sentinelsleep.orchestrator.runner import Runner

    runner = Runner(
        db_path=args.db,
        dry_run=args.dry_run,
    )
    runner.run_from_file(wav_path, realtime=not args.fast)

    logger.info("Simulation complete. Events written to %s", args.db)


if __name__ == "__main__":
    main()
