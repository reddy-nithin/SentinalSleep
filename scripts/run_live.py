"""Live microphone entry point for SentinelSleep.

Captures audio from the system microphone and runs the full detection-to-
intervention pipeline indefinitely until interrupted with Ctrl-C.

Usage::

    uv run python scripts/run_live.py

    # Specify a sounddevice device index:
    uv run python scripts/run_live.py --device 1

    # List available devices:
    uv run python scripts/run_live.py --list-devices

Results are written to ``data/events.db`` and can be viewed with::

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


def main() -> None:
    """Parse arguments and start the live pipeline."""
    parser = argparse.ArgumentParser(
        description="Run SentinelSleep on live microphone input.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="sounddevice device index or name. Default: system default.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Print available audio devices and exit.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=config.EVENTS_DB_PATH,
        help=f"Path to SQLite event log. Default: {config.EVENTS_DB_PATH}",
    )
    args = parser.parse_args()

    if args.list_devices:
        import sounddevice as sd  # noqa: PLC0415

        print(sd.query_devices())
        sys.exit(0)

    logger.info("SentinelSleep Live Mode")
    logger.info("  device: %s", args.device or "system default")
    logger.info("  db    : %s", args.db)
    logger.info("  Press Ctrl-C to stop.")

    from sentinelsleep.orchestrator.runner import Runner

    runner = Runner(db_path=args.db)
    runner.run_live(device=args.device)

    logger.info("Live session ended.")


if __name__ == "__main__":
    main()
