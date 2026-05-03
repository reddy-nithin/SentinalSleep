"""
Export SQLite events.db → web/data/*.json for the Vercel dashboard.

Usage:
    uv run python scripts/export_snapshot.py
    uv run python scripts/export_snapshot.py --limit 30 --out web/data

Reuses src.sentinelsleep.db.queries as the single source of truth
for all read shapes. Never writes to the database.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _row_to_dict(row) -> dict:
    return dict(row)


def export(limit: int, out_dir: Path) -> None:
    from sentinelsleep.db import queries
    from sentinelsleep.config import AUDIO_CACHE_DIR

    out_dir.mkdir(parents=True, exist_ok=True)

    # Sessions
    sessions = [_row_to_dict(r) for r in queries.get_sessions(limit=limit)]
    (out_dir / "sessions.json").write_text(json.dumps(sessions, indent=2, default=str))
    print(f"  sessions.json → {len(sessions)} records")

    # Trends (7-day)
    trends_row = queries.get_trends(window_days=7)
    # Convert trends dict to JSON-serialisable form
    trends = {k: (float(v) if isinstance(v, float) else v) for k, v in dict(trends_row).items()} if hasattr(trends_row, "keys") else trends_row
    (out_dir / "trends.json").write_text(json.dumps(trends, indent=2, default=str))
    print("  trends.json written")

    # Recent interventions
    recent_ivs = [_row_to_dict(r) for r in queries.get_interventions(window_days=7)]
    (out_dir / "interventions-recent.json").write_text(
        json.dumps(recent_ivs, indent=2, default=str)
    )
    print(f"  interventions-recent.json → {len(recent_ivs)} records")

    # Per-session data
    session_ids = []
    for session in sessions:
        sid = session["id"]
        session_ids.append(sid)
        sess_dir = out_dir / "sessions" / str(sid)
        sess_dir.mkdir(parents=True, exist_ok=True)

        events = [_row_to_dict(r) for r in queries.get_events_for_session(sid)]
        (sess_dir / "events.json").write_text(json.dumps(events, indent=2, default=str))

        timeseries = [_row_to_dict(r) for r in queries.get_dss_timeseries(sid)]
        (sess_dir / "timeseries.json").write_text(
            json.dumps(timeseries, indent=2, default=str)
        )

        interventions = [_row_to_dict(r) for r in queries.get_interventions_for_session(sid)]
        (sess_dir / "interventions.json").write_text(
            json.dumps(interventions, indent=2, default=str)
        )

        print(f"  sessions/{sid}/ → {len(events)} events, {len(timeseries)} timeseries pts, {len(interventions)} interventions")

    # Manifest
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "session_ids": session_ids,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"  manifest.json → {len(session_ids)} sessions")

    # Copy audio clips referenced by recent interventions
    audio_out = PROJECT_ROOT / "web" / "public" / "audio"
    audio_out.mkdir(parents=True, exist_ok=True)
    clips_copied = 0
    for iv in recent_ivs:
        clip = iv.get("clip_path")
        if not clip:
            continue
        clip_name = Path(clip).name
        src = AUDIO_CACHE_DIR / "mixed" / clip_name
        if src.exists():
            shutil.copy2(src, audio_out / clip_name)
            clips_copied += 1
    print(f"  audio/ → {clips_copied} clip(s) copied to web/public/audio/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export events.db snapshot for Vercel dashboard")
    parser.add_argument("--limit", type=int, default=30, help="Max sessions to export")
    parser.add_argument("--out", type=str, default="web/data", help="Output directory (relative to project root)")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / args.out
    print(f"Exporting snapshot → {out_dir}")

    try:
        export(limit=args.limit, out_dir=out_dir)
        print("Done.")
    except ImportError as e:
        print(f"Error: {e}")
        print("Run from the SentinelSleep project root with: uv run python scripts/export_snapshot.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
